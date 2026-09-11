import asyncio
import sys
sys.stdout.reconfigure(encoding='utf-8')

from models.database import AsyncSessionLocal
from sqlalchemy import text
from core.llm_client import llm_client, SYSTEM_PROMPT_TAMIL
from services.ai_analyzer import ai_analyzer

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(text("SELECT full_text FROM ocr_results WHERE source_id = 'f35e3985-1c8e-4756-beca-10b22b63162d'"))
        txt = res.scalar()
        doc_context = f"--- பக்கம் 1 (மனு விண்ணப்பம்) ---\n{txt[:1600]}"
        prompt = f"""Analyze this Tamil government grievance petition and extract all structured details into a JSON object:
{{
  "petitioner_name": "Full name of the petitioner (e.g. மரகதம்), or null",
  "father_husband_name": "Father or husband name (e.g. சின்னசாமி), or null",
  "gender": "Male or Female",
  "phone": "Primary 10-digit mobile number, or null",
  "door_no": "Door/House number, or null",
  "street_name": "Street or road name, or null",
  "village": "Village or area, or null",
  "taluk": "Taluk name, or null",
  "district": "District name, or null",
  "full_address": "Complete residential address, or null",
  "grievance_type": "Specific grievance subject (e.g. வாரிசு சான்றிதழ், பட்டா மாறுதல், ஓய்வூதியம்)",
  "grievance_subtype": "Specific sub-category or scheme",
  "department": "Government Department responsible for this grievance",
  "description_summary_tamil": "Formal 2-3 sentence administrative summary in Tamil",
  "description_summary_english": "Accurate professional summary in English"
}}

Respond ONLY with valid JSON.

Document Text:
{doc_context}
"""
        print("Sending to LLM...")
        resp = await llm_client.achat(prompt, system_prompt=SYSTEM_PROMPT_TAMIL, max_tokens=1024, json_mode=True)
        print("LLM RESPONSE:")
        print(resp)

if __name__ == "__main__":
    asyncio.run(main())
