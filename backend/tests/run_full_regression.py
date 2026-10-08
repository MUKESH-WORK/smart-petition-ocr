import asyncio
import json
from typing import List, NotRequired, Optional, TypedDict
from models.database import AsyncSessionLocal
from sqlalchemy import text
from services.ai_analyzer import ai_analyzer
from services.semantic_classifier import semantic_classifier

class TestCase(TypedDict):
    test_name: str
    source_id: str
    forbidden_terms: list[str]
    expected_tax_id: NotRequired[int]
    expected_subtype: NotRequired[str]
    expected_dept: NotRequired[str]
    expected_concept: NotRequired[str]

test_cases: list[TestCase] = [
    {
        "test_name": "Test 1: Community Hall (K. Senthilkumar)",
        "source_id": "c8ae935c-6a7c-4e21-bc4e-8f2a3dd6e646",
        "expected_tax_id": 14,
        "expected_subtype": "Community Hall - ADW",
        "forbidden_terms": ["ST Community Genuiness", "DTW", "Old Age Pension", "முதியோர் உதவித்தொகை", "குடிநீர்", "Drinking Water"]
    },
    {
        "test_name": "Test 2: Veterinary Hospital repair (P. Lokesh)",
        "source_id": "6c0f806a-01cb-4e9d-90a2-4bfb1ec30543",
        "expected_dept": "Animal Husbandry",
        "forbidden_terms": ["குடிநீர்", "Drinking Water", "Old Age Pension", "முதியோர் உதவித்தொகை", "Community Hall", "ST Community"]
    },
    {
        "test_name": "Test 3: Burial Ground pathway (P. Muthulakshmi)",
        "source_id": "1d31dadc-b9c6-4356-a7be-eb1c029d8eb1",
        "expected_tax_id": 24,
        "expected_subtype": "Pathway To Burial Ground",
        "forbidden_terms": ["Old Age Pension", "முதியோர் உதவித்தொகை", "IGNOAPS", "குடிநீர்", "ST Community"]
    },
    {
        "test_name": "Test 4: Water channel encroachment (M. Aravind)",
        "source_id": "2dc8ba7b-d860-443e-b6bd-3dfaab1df1d2",
        "expected_concept": "encroachment",
        "forbidden_terms": ["Community Hall", "Old Age Pension", "முதியோர் உதவித்தொகை", "கால்நடை", "Veterinary"]
    },
    {
        "test_name": "Test 5: Scholarship (M. Karthik)",
        "source_id": "4ef8f49e-46f9-4d18-8bad-01757bb0e637",
        "expected_dept": "Higher Education",
        "forbidden_terms": ["Community Hall", "Old Age Pension", "முதியோர் உதவித்தொகை", "Burial Ground", "சுடுகாடு"]
    }
]

async def run_regression():
    print("=" * 80)
    print("RUNNING 5-POINT REGRESSION TEST SUITE")
    print("=" * 80)
    all_passed = True

    async with AsyncSessionLocal() as db:
        for tc in test_cases:
            sid: str = tc["source_id"]
            name: str = tc["test_name"]
            print(f"\n>>> EXECUTING: {name} (source_id: {sid})")

            # Fetch OCR & Entities
            ocr_row = (await db.execute(text("SELECT full_text FROM ocr_results WHERE source_id = :sid"), {"sid": sid})).mappings().one_or_none()
            ent_rows = (await db.execute(text("SELECT entity_type, entity_value FROM extracted_entities WHERE source_id = :sid"), {"sid": sid})).mappings().all()

            if not ocr_row:
                print(f"FAILED: No OCR results found for {sid}")
                all_passed = False
                continue

            doc_text = str(ocr_row["full_text"] or "")
            entities = [{"entity_type": r["entity_type"], "entity_value": r["entity_value"]} for r in ent_rows]

            # 1. Run Semantic Classifier Directly
            sem_res = semantic_classifier.classify(full_doc_text=doc_text, top_k=5)
            print(f"  [Semantic Classifier]")
            print(f"    Top Tax ID: {sem_res.get('taxonomy_id')} | Subtype: {sem_res.get('grievance_subtype')} | Score: {sem_res.get('confidence_score')}")
            for c in sem_res.get("candidates", [])[:3]:
                print(f"      - ID {c['taxonomy_id']}: {c['grievance_sub_type']} (score: {c['final_score']:.4f})")

            # 2. Run Full AI Analyzer Pipeline
            result = await ai_analyzer.analyze(
                db=db,
                source_id=sid
            )

            final_tax_id = result.get("taxonomy_id")
            final_dept = result.get("department")
            final_type = result.get("grievance_type")
            final_subtype = result.get("grievance_subtype")
            final_desc = result.get("description_summary_tamil") or result.get("summary_tamil") or ""

            print(f"  [AI Analyzer Final Result]")
            print(f"    Final Tax ID: {final_tax_id}")
            print(f"    Final Dept  : {final_dept}")
            print(f"    Final Type  : {final_type}")
            print(f"    Final Subtype: {final_subtype}")
            print(f"    Final Desc  : {final_desc}")

            # Verification Checks
            test_ok = True

            # Check Taxonomy
            exp_tax_id: Optional[int] = tc.get("expected_tax_id")
            exp_subtype: Optional[str] = tc.get("expected_subtype")
            exp_dept: Optional[str] = tc.get("expected_dept")
            forbidden_terms: list[str] = tc.get("forbidden_terms", [])

            if exp_tax_id is not None and final_tax_id != exp_tax_id:
                print(f"  [FAIL] Expected taxonomy_id {exp_tax_id}, got {final_tax_id}")
                test_ok = False
            elif exp_subtype and exp_subtype.lower() not in (final_subtype or "").lower():
                print(f"  [FAIL] Expected subtype '{exp_subtype}', got '{final_subtype}'")
                test_ok = False
            elif exp_dept and exp_dept.lower() not in (final_dept or "").lower():
                print(f"  [FAIL] Expected dept '{exp_dept}', got '{final_dept}'")
                test_ok = False
            else:
                print(f"  [PASS] Taxonomy verified successfully.")

            # Check Description Contaminants
            found_contaminants = [term for term in forbidden_terms if term.lower() in final_desc.lower()]
            if found_contaminants:
                print(f"  [FAIL] Description contaminated with forbidden terms: {found_contaminants}")
                test_ok = False
            else:
                print(f"  [PASS] Description free of contaminating/preliminary terms.")

            if test_ok:
                print(f"  ===> {name}: PASSED BOTH TAXONOMY AND DESCRIPTION")
            else:
                print(f"  ===> {name}: FAILED")
                all_passed = False

    print("\n" + "=" * 80)
    if all_passed:
        print("ALL 5 REGRESSION TESTS PASSED!")
    else:
        print("SOME TESTS FAILED - SEE DETAILS ABOVE")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(run_regression())
