from storage.conversations import (
    get_conversation,
    save_conversation,
    update_conversation_meta,
)

import importlib
import logging
logging.basicConfig(level=logging.INFO)

# Create conv with extra keys
conv_id = save_conversation(
    {
        "model": "meta-test",
        "messages": [],
        "meta": {
            "state": "PRACTICE_LANGUAGE",
            "language": "DE",
            "memory_long": "should be removed",
            "recurring_errors": ["Artikel"],
        },
    }
)
logging.info("created id %s", conv_id)
conv = get_conversation(conv_id)
logging.info("meta after create: %s", conv.get("meta"))
# Attempt to update with disallowed keys
update_conversation_meta(
    conv_id,
    {
        "last_activity_at": "2026-02-08T00:00:00",
        "recurring_errors": ["Plural"],
        "language": "DE",
    },
)
conv2 = get_conversation(conv_id)
logging.info("meta after update: %s", conv2.get("meta"))
# Clean all rows (idempotent)
importlib.import_module("scripts.clean_meta_columns")

logging.info("cleanup done; requery:")
logging.info("%s", get_conversation(conv_id))
