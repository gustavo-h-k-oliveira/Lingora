import logging
from typing import Any, Dict, List, Optional

from storage.conversations import (
    append_messages,
    get_conversation,
    save_conversation,
    update_conversation_meta,
)
from storage.tz import now_brasilia

from .llm_client import LLMClient, OpenRouterClient
from .memory import MemoryManager
from .prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class LingoraEngine:
    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        prompt_builder: Optional[PromptBuilder] = None,
        memory_manager: Optional[MemoryManager] = None,
    ):
        self.llm = llm_client or OpenRouterClient()
        self.builder = prompt_builder or PromptBuilder()
        self.memory = memory_manager or MemoryManager()

    def run_turn(
        self,
        question: Optional[str] = None,
        messages: Optional[List[Dict[str, Any]]] = None,
        conversation_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        # Determine messages to use
        if messages is None:
            if question is None:
                question = "Bring me three sentences in German."
            messages = [{"role": "user", "content": question}]

        # If conversation_id provided, fetch stored conversation to build context
        history = []
        if conversation_id:
            conv = get_conversation(conversation_id)
            if conv and conv.get("messages"):
                history = conv["messages"]
        else:
            history = messages[
                :-1
            ]  # if provided inline full messages, treat all but last as history

        # short-term memory
        context = self.memory.short_term(history)

        # Build prompt
        user_msg = messages[-1]

        # Determine meta: prefer stored conversation meta when available
        meta: Dict[str, Any] = {}
        if conversation_id:
            stored = get_conversation(conversation_id)
            if stored:
                meta = stored.get("meta", {}) or {}
        # ensure some sensible defaults
        meta.setdefault("state", "IDLE")
        meta.setdefault("language", "unknown")

        prompt_messages = self.builder.build(context, user_msg, meta=meta)

        # Call LLM
        resp = self.llm.generate(prompt_messages)
        assistant_content = resp.get("content")
        reasoning = resp.get("reasoning_details")

        # Persist
        if conversation_id:
            append_messages(
                conversation_id,
                [
                    user_msg,
                    {
                        "role": "assistant",
                        "content": assistant_content,
                        "reasoning_details": reasoning,
                    },
                ],
            )
            conv_id = conversation_id
        else:
            convo_to_save = {
                "model": getattr(self.llm, "model", "unknown"),
                "meta": meta,
                "messages": (context or [])
                + [
                    user_msg,
                    {
                        "role": "assistant",
                        "content": assistant_content,
                        "reasoning_details": reasoning,
                    },
                ],
            }
            conv_id = save_conversation(convo_to_save)

        # Always mark last activity timestamp on the conversation meta
        try:
            activity_ts = now_brasilia().isoformat()
            update_conversation_meta(conv_id, {"last_activity_at": activity_ts})
        except Exception:
            logger.exception(
                f"Failed to write last_activity_at for conversation {conv_id}"
            )

        # LLM-based meta analysis: ask the model to summarize/update conversation meta
        try:
            # include assistant reasoning_details when available to help analysis
            assistant_msg_for_analysis = {
                "role": "assistant",
                "content": assistant_content,
            }
            if reasoning:
                assistant_msg_for_analysis["reasoning_details"] = reasoning

            analysis_messages = (context or []) + [user_msg, assistant_msg_for_analysis]

            suggested_meta = None
            try:
                suggested_meta = self.llm.analyze_meta(analysis_messages)
            except Exception as e:
                # log LLM failure and persist an analysis error marker
                try:
                    import json
                    import os

                    os.makedirs("logs", exist_ok=True)
                    ts = now_brasilia().isoformat()
                    with open(
                        "logs/meta_analysis_errors.log", "a", encoding="utf-8"
                    ) as fh:
                        fh.write(
                            json.dumps(
                                {"ts": ts, "conv": conv_id, "error": str(e)},
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    # record the failed attempt in meta
                    update_conversation_meta(
                        conv_id,
                        {
                            "last_meta_analysis_error": str(e),
                            "last_meta_analysis_at": ts,
                        },
                    )
                except Exception:
                    logger.exception(
                        "Failed to write meta_analysis_errors.log or record analysis failure in meta"
                    )

            if suggested_meta:
                new_meta = update_conversation_meta(conv_id, suggested_meta)

                # log raw content for debugging/troubleshooting and record the applied meta
                try:
                    import json
                    import os

                    os.makedirs("logs", exist_ok=True)
                    ts = now_brasilia().isoformat()
                    raw = suggested_meta.get("raw_content", "")
                    src = suggested_meta.get("analysis_source", "")
                    with open("logs/meta_analysis.log", "a", encoding="utf-8") as fh:
                        fh.write(f"{ts} conv={conv_id} source={src} raw={raw}\n")
                    # record the applied meta separately for easy inspection
                    with open("logs/meta_updates.log", "a", encoding="utf-8") as fh:
                        fh.write(
                            json.dumps(
                                {"ts": ts, "conv": conv_id, "applied_meta": new_meta},
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                    logger.info(f"Meta applied to conversation {conv_id}: {new_meta}")
                except Exception:
                    logger.exception(
                        "Failed to write meta_analysis.log or meta_updates.log"
                    )
        except Exception:
            # keep going if meta update fails
            logger.exception(
                f"Failed to analyze/update meta for conversation {conv_id}"
            )

        return {
            "conversation": {"id": conv_id},
            "final_message": assistant_content,
            "conversation_id": conv_id,
        }
