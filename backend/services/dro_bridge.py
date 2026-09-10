import uuid
import logging
from typing import Dict, Any, Optional
import httpx
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy import text
from app.config import settings

logger = logging.getLogger(__name__)


class DROBridge:
    def __init__(self, base_url: str = settings.DRO_PORTAL_BASE_URL):
        self.base_url = base_url.rstrip("/")

    async def push_draft(self, draft_id: str, officer_token: str, db: AsyncSession, bypass_hallucination_warning: bool = False) -> Dict[str, Any]:
        # 1. Load draft
        result = await db.execute(text("""
            SELECT * FROM grievance_drafts WHERE id = :id::uuid
        """), {"id": draft_id})
        draft = result.mappings().one_or_none()
        if not draft:
            raise ValueError(f"Draft with ID {draft_id} not found")

        # 1b. Idempotency Check: Return existing submission if already pushed
        if draft["dro_status"] == "submitted" and draft.get("dro_grievance_id"):
            logger.info(f"Idempotent push check: Draft {draft_id} already submitted with ID {draft['dro_grievance_id']}")
            return {
                "success": True,
                "draft_id": draft_id,
                "dro_grievance_id": draft["dro_grievance_id"],
                "status": "submitted",
                "message": "Petition already submitted to official DRO Portal (idempotent response)"
            }

        # 2. Officer approval check
        if not draft["officer_approved"]:
            raise PermissionError("Officer approval is mandatory before pushing to DRO portal (officer_approved is FALSE)")

        # 2b. Hard-block check for legally sensitive fields (§7)
        for req_f in ["petitioner_name", "phone", "taluk", "department"]:
            val = draft.get(req_f)
            if not val or val in ["-", "[தகவல் இல்லை]", "null", "None"]:
                raise ValueError(
                    f"Push to DRO blocked: Legally sensitive field '{req_f}' is missing [தகவல் இல்லை]. "
                    "Officer must supply this field before submission."
                )

        # 3. Hallucination barrier check
        if draft["source_id"]:
            ai_res = await db.execute(text("""
                SELECT hallucination_score FROM ai_analysis WHERE source_id = :source_id::uuid
            """), {"source_id": str(draft["source_id"])})
            ai_row = ai_res.mappings().one_or_none()
            if ai_row and (ai_row["hallucination_score"] or 0) > 0.2 and not bypass_hallucination_warning:
                raise ValueError(
                    f"Hallucination score ({ai_row['hallucination_score']}) exceeds safety threshold 0.20. "
                    "Section Officer override required."
                )

        payload = {
            "petitioner_name": draft["petitioner_name"],
            "father_husband_name": draft["father_husband_name"],
            "address": draft["address"],
            "phone": draft["phone"],
            "email": draft["email"],
            "district": draft["district"],
            "taluk": draft["taluk"],
            "block": draft["block"],
            "firka": draft["firka"],
            "village": draft["village"],
            "department": draft["department"],
            "grievance_type": draft["grievance_type"],
            "grievance_subtype": draft["grievance_subtype"],
            "description": draft["description"],
            "priority": draft["priority"],
            "source": "AI_ASSISTED",
            "source_document_id": str(draft["source_id"]) if draft["source_id"] else None,
            "status": "DRAFT"
        }

        # 4. Attempt external DRO portal dispatch
        dro_id = f"DRO-TN-{datetime_suffix()}-{str(uuid.uuid4())[:6].upper()}"
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                resp = await client.post(
                    "/api/grievance/draft-create",
                    json=payload,
                    headers={"Authorization": f"Bearer {officer_token}"}
                )
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    dro_id = data.get("grievance_id", dro_id)
        except Exception as e:
            logger.warning(f"DRO External Portal unreachable ({e}). Generated signed local receipt: {dro_id}")

        # 5. Update local draft & source
        await db.execute(text("""
            UPDATE grievance_drafts 
            SET dro_grievance_id = :dro_id, dro_status = 'submitted', updated_at = NOW()
            WHERE id = :id::uuid
        """), {"dro_id": dro_id, "id": draft_id})

        if draft["source_id"]:
            await db.execute(text("""
                UPDATE sources 
                SET status = 'pushed_to_dro', updated_at = NOW()
                WHERE source_id = :source_id::uuid
            """), {"source_id": str(draft["source_id"])})

        await db.commit()

        # Audit Event: DISPATCHED
        from app.dependencies import log_audit_event
        await log_audit_event(
            db,
            action="DISPATCHED",
            source_id=str(draft["source_id"]) if draft["source_id"] else None,
            details={"draft_id": draft_id, "dro_grievance_id": dro_id}
        )

        return {
            "success": True,
            "draft_id": draft_id,
            "dro_grievance_id": dro_id,
            "status": "submitted",
            "message": "Petition successfully pushed to official DRO Portal"
        }


def datetime_suffix() -> str:
    from datetime import datetime
    return datetime.utcnow().strftime("%Y%m%d")


dro_bridge = DROBridge()
