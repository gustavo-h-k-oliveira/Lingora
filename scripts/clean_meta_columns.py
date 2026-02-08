"""Cleanup script: keep only allowed meta keys in conversations.meta

Run this when you want to prune existing conversation meta entries so that only
`state`, `language`, and `recurring_errors` remain.
"""

import json
import os
import logging

from sqlalchemy import text

from storage.conversations import ALLOWED_META_KEYS
from storage.db import engine

logger = logging.getLogger(__name__)

os.makedirs("logs", exist_ok=True)

with engine.connect() as conn:
    rows = conn.execute(text("SELECT id, meta FROM conversations")).fetchall()
    for row in rows:
        conv_id = row[0]
        raw = row[1]
        try:
            meta = json.loads(raw) if isinstance(raw, str) else (raw or {})
        except Exception:
            meta = {}
        new_meta = {k: meta.get(k) for k in ALLOWED_META_KEYS if k in meta}
        if new_meta != (meta or {}):
            conn.execute(
                text("UPDATE conversations SET meta = :meta WHERE id = :id"),
                {"meta": json.dumps(new_meta), "id": conv_id},
            )
            conn.commit()
            with open("logs/meta_clean.log", "a", encoding="utf-8") as fh:
                fh.write(
                    json.dumps(
                        {"id": conv_id, "old": meta, "new": new_meta},
                        ensure_ascii=False,
                    )
                    + "\n"
                )

logger.info("Done. See logs/meta_clean.log for changed rows.")
