"""
DEPRECATED: This module has been consolidated into `backend/scripts/seed_db.py`.
Import directly from `scripts.seed_db` instead.
"""
from scripts.seed_db import (
    seed_official_accounts,
    seed_intake_channels,
    seed_authoritative_hierarchy,
    seed_master_data_if_needed,
    AUTHORITATIVE_HIERARCHY_DATA,
    OFFICIAL_ACCOUNTS,
    CM_INTAKE_CHANNELS,
)

__all__ = [
    "seed_official_accounts",
    "seed_intake_channels",
    "seed_authoritative_hierarchy",
    "seed_master_data_if_needed",
    "AUTHORITATIVE_HIERARCHY_DATA",
    "OFFICIAL_ACCOUNTS",
    "CM_INTAKE_CHANNELS",
]
