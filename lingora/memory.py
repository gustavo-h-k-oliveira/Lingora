from typing import Any, Dict, List


class MemoryManager:
    def __init__(self, window_size: int = 8):
        self.window_size = window_size

    def short_term(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        # keep last N messages
        return messages[-self.window_size :] if messages else []
