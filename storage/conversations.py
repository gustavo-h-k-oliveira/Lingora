import json
import os
from typing import Any, Dict
from datetime import datetime

__all__ = ["save_conversation_as_array"]


def save_conversation_as_array(path: str, conversation: Dict[str, Any]) -> None:
    """Append a conversation dict to a JSON array in `path`.

    Creates parent directory if needed. If the file exists but is invalid JSON
    it will be overwritten with a new array containing `conversation`.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = []
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if not isinstance(data, list):
                    data = []
        except (json.JSONDecodeError, FileNotFoundError):
            data = []
    data.append(conversation)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
