from typing import Any, Dict, List

# Prompt template adapted from README.md (section: "Prompt base para cada estado")
PROMPT_TEMPLATE = (
    "Você é Lingora, tutora virtual amigável, paciente e motivadora.\n"
    "Objetivo: ajudar o usuário a aprender {language}.\n"
    "Estado atual: {state}\n"
    "Instruções:\n"
    "- Corrija erros antes de explicar\n"
    "- Priorize a produção do aluno\n"
    "- Adapte a complexidade ao nível do usuário\n"
    "- Use feedback positivo\n"
    "- Use exemplos concretos para explicar erros\n"
    "- Use elementos do Markdown para formatar a resposta (listas, negrito, itálico, etc) e destacar pontos importantes\n"
    "- Limite a explicação ao necessário\n"
    "- Propor exercícios quando apropriado\n"
    "- Identificar o idioma do usuário antes de responder as perguntas\n"
    "Contexto do usuário: {memory_short}\n"
    "Mensagem do usuário: {input}\n"
    "Gere a resposta de acordo com essas regras."
)


class PromptBuilder:
    def __init__(self, system_prompt: str | None = None):
        # allow overriding the whole template if needed
        self.template = system_prompt or PROMPT_TEMPLATE

    def _history_to_short_memory(
        self, history: List[Dict[str, Any]], max_items: int = 6
    ) -> str:
        if not history:
            return ""
        recent = history[-max_items:]
        parts = []
        for m in recent:
            role = m.get("role", "unknown")
            content = (m.get("content") or "").strip()
            parts.append(f"{role.capitalize()}: {content}")
        return " | ".join(parts)

    def build(
        self,
        history: List[Dict[str, Any]],
        user_message: Dict[str, Any],
        meta: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        # meta may contain: state, language, user_level, recurring_errors, memory_long
        meta = meta or {}
        state = meta.get("state", "IDLE")
        language = meta.get("language", "unknown")
        memory_short = self._history_to_short_memory(history)
        memory_long = meta.get("memory_long", "")
        user_input = (user_message.get("content") or "").strip()

        system_content = self.template.format(
            state=state,
            language=language,
            memory_short=memory_short,
            memory_long=memory_long,
            input=user_input,
        )

        messages: List[Dict[str, Any]] = [{"role": "system", "content": system_content}]

        # If there is a separate long memory summary, add as system note
        if memory_long:
            messages.append(
                {
                    "role": "system",
                    "content": f"Long-term memory summary: {memory_long}",
                }
            )

        # Append trimmed history (assumed already ordered)
        messages.extend(history)

        # Append the latest user message
        messages.append(user_message)
        return messages
