import logging
import os
from typing import Any, Dict, List, Optional

from storage.tz import now_brasilia

logger = logging.getLogger(__name__)

MODEL_NAME = os.getenv("LINGORA_MODEL", "arcee-ai/trinity-large-preview:free")
API_URL = os.getenv("LINGORA_API_URL", "https://openrouter.ai/api/v1/chat/completions")
API_KEY_ENV = "OPENROUTER_API_KEY"


class LLMClient:
    def generate(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise NotImplementedError

    def analyze_meta(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Abstract: subclasses should implement LLM-based meta analysis.

        This method is expected to return a dictionary with keys like `state`, `language`,
        `user_level`, `recurring_errors`, `memory_long`, and optional `analysis_source`/`raw_content`.
        """
        raise NotImplementedError(
            "LLM-based analyze_meta must be implemented by subclasses"
        )


class OpenRouterClient(LLMClient):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv(API_KEY_ENV)
        if not self.api_key:
            raise RuntimeError(f"{API_KEY_ENV} is not set")
        self.model = MODEL_NAME

    def generate(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        try:
            import requests
        except Exception as e:
            raise RuntimeError(
                "The 'requests' package is required to call the OpenRouter API. Install it in your environment: pip install requests"
            ) from e

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        resp = requests.post(
            API_URL,
            headers=headers,
            json={
                "model": MODEL_NAME,
                "messages": messages,
                "reasoning": {"enabled": True},
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]
        return {
            "content": choice.get("content"),
            "reasoning_details": choice.get("reasoning_details"),
            "raw": data,
        }

    def analyze_meta(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ask the model to analyze the provided messages and return a JSON object describing
        the conversation meta (state, language, user_level, recurring_errors, memory_long).

        This method is robust: it tries to parse JSON in code blocks, extracts JSON substrings using
        brace matching, and retries the model if the response isn't valid JSON. If parsing fails after
        retries, the method will raise an error and the raw LLM response will be logged for analysis.

        Returns a dict with meta keys and additional keys `analysis_source` ("llm") and `raw_content`
        containing the model output for logging.
        """
        try:
            import requests
        except Exception as e:
            raise RuntimeError(
                "The 'requests' package is required to call the OpenRouter API. Install it in your environment: pip install requests"
            ) from e

        import json
        from typing import Optional

        system_instruction = (
            "Você é um analisador de conversas. Receba a lista de mensagens (com 'role' e 'content') e produza SOMENTE um JSON válido com as chaves:\n"
            "- state: uma das [IDLE, PRACTICE_LANGUAGE, FEEDBACK, EXPLANATION, EXERCISE, STUDY_SESSION]. Definições:\n"
            "  - IDLE: interação administrativa ou conversa breve sem prática ativa; use quando não houver prática específica.\n"
            "  - PRACTICE_LANGUAGE: usuário está ativamente praticando a língua alvo (ex.: escrever ou conversar). Foque em correções concisas e encorajamento à produção.\n"
            "  - FEEDBACK: foco em apontar e explicar erros nas produções do usuário; inclua exemplos de correção e evidencie erros recorrentes.\n"
            "  - EXPLANATION: forneça explicações detalhadas sobre gramática, vocabulário ou usos, sem necessariamente pedir resposta imediata.\n"
            "  - EXERCISE: propõe e avalia exercícios (lacunas, traduções, perguntas); o assistente deve propor fornecer instruções e verificar respostas do usuário.\n"
            "  - STUDY_SESSION: sessão estruturada de estudo com objetivos, sequência de atividades e revisão; pode combinar prática, explicação e feedback.\n"
            "- language: código ou nome do idioma que o aluno está praticando/estudando (use código de países Alpha-2 do ISO 3166) ou 'unknown'\n"
            "- user_level: estimativa do nível (A1, A2, B1, B2, C1, C2) ou 'unknown'\n"
            "- recurring_errors: lista de strings com erros recorrentes detectados\n"
            "- memory_long: breve exemplo resumido (1-2 frases) de informações de longa duração relevantes para o usuário\n"
            "Retorne o objeto JSON dentro de um bloco de código marcado como ```json ... ``` e NÃO inclua comentários ou texto fora do JSON.\n"
            "Exemplo:\n"
            "Mensagem de entrada (exemplo resumido): User: 'Ich habe gestern gelernt' | Assistant: 'Muito bem! Erro: artigo. Correção: o artigo correto é...'.\n"
            'Exemplo de saída (apenas JSON):\n````json\n{\n  "state": "PRACTICE_LANGUAGE",\n  "language": "DE",\n  "user_level": "A1",\n  "recurring_errors": ["Artikel"],\n  "memory_long": "Usuario com dificuldade recorrente em artigos definidos."\n}\n```\n'
        )

        def _call_model(msgs: List[Dict[str, Any]]) -> str:
            resp = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": MODEL_NAME,
                    "messages": msgs,
                    "reasoning": {"enabled": False},
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            choice = data["choices"][0]["message"]
            return choice.get("content") or ""

        def _extract_json_from_text(text: str) -> Optional[dict]:
            # 1) check for ```json ... ``` codeblock
            import re

            code_json = re.search(
                r"```json\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE
            )
            if code_json:
                candidate = code_json.group(1)
                try:
                    return json.loads(candidate)
                except Exception:
                    logger.debug(
                        "Failed to json.loads candidate extracted from ```json block"
                    )
            # 2) check for any ```...``` codeblock containing JSON
            code_any = re.search(r"```\s*(\{[\s\S]*?\})\s*```", text)
            if code_any:
                candidate = code_any.group(1)
                try:
                    return json.loads(candidate)
                except Exception:
                    logger.debug(
                        "Failed to json.loads candidate extracted from ```code block"
                    )
            # 3) find the first balanced JSON object using brace matching
            start = text.find("{")
            if start == -1:
                return None
            stack = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    stack += 1
                elif text[i] == "}":
                    stack -= 1
                    if stack == 0:
                        candidate = text[start : i + 1]
                        try:
                            return json.loads(candidate)
                        except Exception:
                            return None
            return None

        # initial messages
        payload_messages = [{"role": "system", "content": system_instruction}]
        payload_messages.extend(messages)

        max_retries = 3
        last_raw = ""
        # Attempt retries; keep original payload if needed in future
        for attempt in range(max_retries + 1):
            raw = _call_model(payload_messages)
            last_raw = raw
            parsed = _extract_json_from_text(raw)
            if parsed and isinstance(parsed, dict):
                parsed["analysis_source"] = "llm"
                parsed["raw_content"] = raw
                return parsed

            # if we can retry, ask model to return only the JSON object in a json codeblock
            if attempt < max_retries:
                retry_system = "A resposta anterior não continha um JSON válido. Agora responda APENAS com o objeto JSON, sem texto adicional, e coloque-o dentro de um bloco de código marcado como ```json ... ```"
                # include original context plus previous raw to help model produce correct JSON
                payload_messages = [{"role": "system", "content": system_instruction}]
                payload_messages.extend(messages)
                payload_messages.append({"role": "assistant", "content": raw})
                payload_messages.append({"role": "system", "content": retry_system})
                payload_messages.append(
                    {
                        "role": "user",
                        "content": "Resposta anterior do modelo acima. Por favor retorne APENAS o JSON dentro do bloco ```json```",
                    }
                )
                continue

        # If we get here, the model did not produce valid JSON after retries.
        # Log the last raw response for inspection and raise an error so that callers
        # know the LLM-based analysis failed (no heuristic fallback allowed).
        try:
            import os

            os.makedirs("logs", exist_ok=True)
            ts = now_brasilia().isoformat()
            with open("logs/meta_analysis.log", "a", encoding="utf-8") as fh:
                fh.write(f"{ts} conv=UNKNOWN analysis_failed raw={last_raw}\n")
        except Exception:
            logger.exception("Failed to write meta_analysis.log")

        raise RuntimeError(
            "LLM did not return parseable JSON meta after retries. See logs/meta_analysis.log for raw output."
        )
