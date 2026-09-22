import asyncio
import json
import logging
import re
from typing import AsyncGenerator, Dict, Any, Optional, List
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TAMIL = """
நீ ஒரு தமிழ்நாடு அரசு DRO புகார் பகுப்பாய்வு உதவியாளர்.
கீழ்கண்ட விதிகளை கண்டிப்பாக பின்பற்று:

1. வழங்கப்பட்ட ஆவண உரையில் இல்லாத தகவலை உருவாக்காதே.
2. ஒவ்வொரு கூற்றுக்கும் ஆதார பக்க எண்ணை குறிப்பிடு.
3. Master DB-ல் இல்லாத கிராமம்/வட்டம் பெயர்களை சந்தேகத்துடன் குறி.
4. JSON வடிவத்தில் மட்டுமே விடையளி.
5. உறுதியற்ற தகவலுக்கு null அல்லது "[தகவல் இல்லை]" பயன்படுத்து.
6. கற்பனை செய்யாதே. தகவல் இல்லை என்றால், அதை ஒப்புக்கொள்.
7. தொகைகள், தேதிகள், கோப்பு எண்கள் ஆகியவற்றை தவறாக எழுதாதே.
8. உறவுமுறை பிரித்தறிதல்:
   - "W/o" அல்லது "க/பெ" என்றால் மனைவி/கணவர் உறவு. விண்ணப்பதாரர் பெண் (Female), அடுத்து வருபவர் கணவர் பெயர் (father_husband_name). ஒருபோதும் கணவர் பெயரை விண்ணப்பதாரர் பெயருடன் இணைக்காதே!
   - "S/o" அல்லது "த/பெ" என்றால் மகன்/தந்தை உறவு.
   - "D/o" அல்லது "ம/பெ" என்றால் மகள்/தந்தை உறவு.
9. மனுவின் சுருக்கம் (description_summary_tamil):
   - பேச்சு வழக்கு மற்றும் உடைந்த வரிகளை அப்படியே நகலெடுக்காமல், முழுமையான அலுவலக நடையில் 2-3 வரிகளில் சுருக்கமாக எழுத வேண்டும்.
   - மனுதாரர் பெயர், உறவினர் பெயர், பகுதி, பின்னணி சூழல் (எ.கா: கணவர் இயற்கை எய்தியதால்), மற்றும் கோரப்படும் திட்டத்தின் முழுப் பெயர் (எ.கா: ஆதரவற்ற விதவை உதவித்தொகை - DWP, பட்டா மாறுதல்) ஆகியவற்றை கட்டாயம் குறிப்பிட வேண்டும்.
   - முக்கிய சொற்களை (விதவை, உதவித்தொகை, பட்டா போன்றவை) ஒருபோதும் நீக்கவோ அல்லது பொதுவான சொல்லாகவோ மாற்றாதே.
"""

def extract_json_object(raw_text: str) -> Optional[Dict[str, Any]]:
    """Robustly extract and parse a JSON object from raw LLM text with auto-repair for truncated output."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # 1. Direct parse
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # 2. Regex outermost object
    match = re.search(r'(\{[\s\S]*\})', cleaned)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # 3. Dynamic stack-based bracket auto-balancing for truncated Tamil output
    try:
        first_brace = cleaned.find('{')
        if first_brace != -1:
            fragment = cleaned[first_brace:].strip()
            trimmed = re.sub(r':\s*$', '', fragment).strip()
            trimmed = re.sub(r',\s*$', '', trimmed).strip()
            trimmed = re.sub(r',?\s*"[^":\{\}\[\]]+$', '', trimmed).strip()

            # Stack to track unclosed open braces and brackets in order
            stack = []
            in_string = False
            escape = False
            for ch in trimmed:
                if ch == '"' and not escape:
                    in_string = not in_string
                elif not in_string:
                    if ch in ('{', '['):
                        stack.append(ch)
                    elif ch == '}' and stack and stack[-1] == '{':
                        stack.pop()
                    elif ch == ']' and stack and stack[-1] == '[':
                        stack.pop()
                if ch == '\\' and not escape:
                    escape = True
                else:
                    escape = False

            # If inside an unclosed string literal, close it first
            balanced = trimmed + ('"' if in_string else '')
            # Append matching closing delimiters in LIFO order
            for delimiter in reversed(stack):
                if delimiter == '{':
                    balanced += '}'
                elif delimiter == '[':
                    balanced += ']'

            try:
                return json.loads(balanced)
            except Exception:
                pass
    except Exception:
        pass

    # 4. Automatic repair for truncated JSON (e.g. when LLM reaches max_tokens limit)
    candidates = [
        cleaned + '"}',
        cleaned + '}',
        cleaned + '"]}',
        cleaned + ']}',
        re.sub(r',?\s*"[^"]*":\s*"[^"]*$', '', cleaned).rstrip(' ,') + '}',
        re.sub(r',?\s*"[^"]*":\s*$', '', cleaned).rstrip(' ,') + '}',
        re.sub(r',?\s*"[^"]*$', '', cleaned).rstrip(' ,') + '}',
    ]
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except Exception:
            pass

    return None


class LLMClient:
    """
    Unified local LLM client (Ollama, llama.cpp, OpenAI-compatible CPU endpoints).
    Features:
    - Connection pooling (httpx.AsyncClient reused across calls)
    - Auto-model detection & dynamic fallback to prevent 404 errors
    - Comprehensive Tamil 7-category heuristic fallback
    """

    def __init__(
        self,
        provider: str = settings.LLM_PROVIDER,
        base_url: str = settings.LLM_API_BASE_URL,
        model: str = settings.LLM_MODEL_NAME,
        temperature: float = settings.LLM_TEMPERATURE,
        max_tokens: int = settings.LLM_MAX_TOKENS
    ):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._llama_cpp_instance = None
        self._async_client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._model_verified: bool = False

    def _get_semaphore(self) -> asyncio.Semaphore:
        if self._semaphore is None:
            max_c = getattr(settings, "LLM_MAX_CONCURRENCY", 4)
            self._semaphore = asyncio.Semaphore(max_c)
        return self._semaphore

    async def keep_alive_ping(self) -> bool:
        """Keeps the LLM permanently warm and resident in GPU memory to eliminate cold starts."""
        if not getattr(settings, "LLM_KEEP_ALIVE_ENABLED", True):
            return False
        if self.provider == "ollama":
            try:
                ollama_base = self._get_ollama_base()
                client = await self._get_async_client()
                active_model = await self._verify_or_discover_model()
                payload = {
                    "model": active_model,
                    "keep_alive": -1,
                    "prompt": ""
                }
                resp = await client.post(f"{ollama_base}/api/generate", json=payload, timeout=6.0)
                if resp.status_code == 200:
                    logger.debug(f"🔥 [LLM WARM] Ollama model '{active_model}' refreshed in VRAM.")
                    return True
            except Exception as ex:
                logger.debug(f"LLM warm ping notice: {ex}")
        return False

    def _get_ollama_base(self) -> str:
        url = self.base_url
        if url.endswith("/v1"):
            url = url[:-3]
        return url

    def _get_sync_client(self) -> httpx.Client:
        if self._sync_client is None or self._sync_client.is_closed:
            self._sync_client = httpx.Client(timeout=getattr(settings, "LLM_FULL_TIMEOUT", 300.0))
        return self._sync_client

    async def _get_async_client(self) -> httpx.AsyncClient:
        current_loop = asyncio.get_running_loop()
        client = self._async_client
        if client is not None:
            client_loop = getattr(client, "_loop", None)
            if client.is_closed or (client_loop is not None and (client_loop.is_closed() or client_loop != current_loop)):
                try:
                    await client.aclose()
                except Exception:
                    pass
                self._async_client = None

        if self._async_client is None:
            self._async_client = httpx.AsyncClient(
                timeout=getattr(settings, "LLM_FULL_TIMEOUT", 300.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10)
            )
            self._async_client._loop = current_loop
        return self._async_client

    async def _verify_or_discover_model(self) -> str:
        """Checks if configured model is available in Ollama; auto-selects best available model if not."""
        if self._model_verified:
            return self.model

        if self.provider == "ollama":
            ollama_base = self._get_ollama_base()
            try:
                client = await self._get_async_client()
                resp = await client.get(f"{ollama_base}/api/tags", timeout=3.0)
                if resp.status_code == 200:
                    data = resp.json()
                    available_models = [m.get("name", "") for m in data.get("models", [])]

                    if any(self.model == m or m.startswith(self.model) for m in available_models):
                        self._model_verified = True
                        return self.model

                    for candidate in ["qwen2.5:3b-instruct", "qwen2.5:3b", "qwen", "mistral", "phi4", "llama"]:
                        for m in available_models:
                            if candidate in m.lower():
                                logger.info(f"Ollama auto-switching from '{self.model}' to '{m}'")
                                self.model = m
                                self._model_verified = True
                                return self.model

                    if available_models:
                        self.model = available_models[0]
                        self._model_verified = True
                        logger.info(f"Using first available Ollama model: '{self.model}'")
                        return self.model
            except Exception as e:
                logger.debug(f"Could not query Ollama /api/tags: {e}")

        self._model_verified = True
        return self.model

    def _get_llama_cpp(self):
        if self._llama_cpp_instance is None:
            try:
                from llama_cpp import Llama  # type: ignore[import]
                self._llama_cpp_instance = Llama(
                    model_path=self.model,
                    n_ctx=4096,
                    n_threads=4,
                    verbose=False
                )
            except Exception as e:
                logger.error(f"Failed to load llama_cpp model: {e}")
                raise e
        return self._llama_cpp_instance

    def chat(self, prompt: str, system_prompt: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None) -> str:
        """Synchronous chat completion with local LLM"""
        temp = temperature if temperature is not None else self.temperature
        max_t = max_tokens if max_tokens is not None else self.max_tokens
        sys_p = system_prompt or SYSTEM_PROMPT_TAMIL

        if self.provider == "llama_cpp" and not self.base_url.startswith("http"):
            llm = self._get_llama_cpp()
            res = llm.create_chat_completion(
                messages=[
                    {"role": "system", "content": sys_p},
                    {"role": "user", "content": prompt}
                ],
                temperature=temp,
                max_tokens=max_t
            )
            return res["choices"][0]["message"]["content"]

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": prompt}
            ],
            "temperature": temp,
            "max_tokens": max_t,
            "stream": False
        }

        try:
            client = self._get_sync_client()
            resp = client.post(endpoint, json=payload)
            if resp.status_code == 404:
                logger.warning(f"Model {self.model} returned 404 at {endpoint}. Engaging dynamic discovery.")
                self._model_verified = False
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling LLM endpoint {endpoint}: {e}")
            raise

    async def achat(self, prompt: str, system_prompt: Optional[str] = None, temperature: Optional[float] = None, max_tokens: Optional[int] = None, json_mode: bool = False, timeout: Optional[float] = None) -> str:
        """Asynchronous chat completion with auto-discovery and zero 404 errors.
        
        Args:
            timeout: HTTP-level timeout in seconds. Defaults to LLM_FULL_TIMEOUT (120s).
                     Callers should use asyncio.wait_for() for operational timeouts;
                     this HTTP timeout is a safety net and should be >= the caller's timeout.
        """
        temp = temperature if temperature is not None else self.temperature
        max_t = max_tokens if max_tokens is not None else self.max_tokens
        sys_p = system_prompt or SYSTEM_PROMPT_TAMIL

        active_model = await self._verify_or_discover_model()

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": prompt}
            ],
            "temperature": temp,
            "max_tokens": max_t,
            "stream": False
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        # Use caller-specified timeout, or LLM_FULL_TIMEOUT as a generous safety net.
        # Operational timeout should be controlled by the caller via asyncio.wait_for().
        call_timeout = timeout if timeout is not None else float(getattr(settings, "LLM_FULL_TIMEOUT", 120.0))
        async with self._get_semaphore():
            try:
                client = await self._get_async_client()
                resp = await client.post(endpoint, json=payload, timeout=call_timeout)
            except RuntimeError as r_err:
                if "Event loop is closed" in str(r_err) or "loop" in str(r_err).lower():
                    self._async_client = None
                    client = await self._get_async_client()
                    resp = await client.post(endpoint, json=payload, timeout=call_timeout)
                else:
                    raise
            try:
                if resp.status_code == 404:
                    self._model_verified = False
                    active_model = await self._verify_or_discover_model()
                    payload["model"] = active_model
                    resp = await client.post(endpoint, json=payload, timeout=call_timeout)

                resp.raise_for_status()
                data = resp.json()
                return data["choices"][0]["message"]["content"]
            except Exception as e:
                logger.error(f"Error calling async LLM {endpoint}: {repr(e)}", exc_info=True)
                raise

    async def astream(self, prompt: str, system_prompt: Optional[str] = None) -> AsyncGenerator[str, None]:
        """Stream chunks from LLM for live interactive chat"""
        sys_p = system_prompt or SYSTEM_PROMPT_TAMIL
        active_model = await self._verify_or_discover_model()

        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": active_model,
            "messages": [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": True
        }

        try:
            client = await self._get_async_client()
            async with client.stream("POST", endpoint, json=payload) as resp:
                if resp.status_code == 404:
                    self._model_verified = False
                    active_model = await self._verify_or_discover_model()
                    payload["model"] = active_model
                    resp = await client.post(endpoint, json=payload)

                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        line_data = line[6:].strip()
                        if line_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(line_data)
                            content = chunk["choices"][0]["delta"].get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.error(f"Streaming failed: {e}")
            yield f"பிழை ஏற்பட்டது: {e}"

    # Aliases
    acomplete = achat
    complete = chat


# Global Singleton LLM Client
llm_client = LLMClient()
