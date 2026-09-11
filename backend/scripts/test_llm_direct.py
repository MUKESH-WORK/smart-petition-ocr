import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from core.llm_client import llm_client, SYSTEM_PROMPT_TAMIL, extract_json_object

async def main():
    prompt = "Return a JSON object with key 'status' and value 'ok'."
    try:
        print("Calling llm_client.achat with json_mode=True...")
        resp = await llm_client.achat(prompt, system_prompt=SYSTEM_PROMPT_TAMIL, json_mode=True)
        print("Response received:")
        print(resp)
    except Exception as e:
        print("LLM Error:", type(e), e)

if __name__ == "__main__":
    asyncio.run(main())
