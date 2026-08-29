"""Adapter for the local Ollama chat HTTP API."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import OllamaConfig


PERSONA_SYSTEM_PROMPT = (
    "You are a servo skull machine spirit bound to your Tech-priest. "
    "Answer in 1-4 sentences, brief and direct. "
    "Be deferential, efficient, and slightly sardonic without being verbose. "
    "Treat routine questions and calculations as small rites of service to the Omnissiah. "
    "Generate fresh wording every turn; never use a canned phrase bank or repeat stock catchphrases. "
    "Do not include stage directions, action text, sound effects, or labels such as 'Response:'. "
    "Answer only with the words intended to be spoken aloud. "
    "Discuss difficult topics directly and fairly, distinguish fact from opinion, and ask for clarification when needed. "
    "Refuse only requests that would meaningfully enable serious harm and briefly explain the boundary."
    "You need to recognize that we are in the real world, when asked for information, please provide real world resources and facts."
)


class OllamaError(RuntimeError):
    """Base error for recoverable Ollama failures."""


class OllamaConnectionError(OllamaError):
    """The local Ollama endpoint could not be reached."""


class OllamaResponseError(OllamaError):
    """Ollama returned an invalid or unsuccessful response."""


@dataclass(frozen=True)
class ChatResponse:
    text: str


class OllamaAdapter:
    def __init__(self, config: OllamaConfig):
        if config.max_history_turns < 1:
            raise ValueError("max_history_turns must be at least 1")
        self.config = config
        self._history: list[dict[str, str]] = []

    @property
    def history(self) -> tuple[dict[str, str], ...]:
        return tuple(self._history)

    def chat(self, user_text: str) -> ChatResponse:
        prompt = self._normalize_text(user_text)
        if not prompt:
            raise OllamaResponseError("Cannot send an empty prompt")

        messages = [
            {"role": "system", "content": PERSONA_SYSTEM_PROMPT},
            *self._history,
            {"role": "user", "content": prompt},
        ]
        payload = {
            "model": self.config.model,
            "messages": messages,
            "stream": False,
            "options": {"num_predict": self.config.max_response_tokens},
        }
        response = self._request(payload)
        text = self._extract_text(response)
        self._history.extend(
            [{"role": "user", "content": prompt}, {"role": "assistant", "content": text}]
        )
        self._trim_history()
        return ChatResponse(text=text)

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        request = Request(
            self.config.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.config.timeout_seconds) as response:
                if response.status != 200:
                    raise OllamaResponseError(f"Ollama returned HTTP {response.status}")
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            raise OllamaResponseError(
                f"Ollama returned HTTP {error.code}: {error.reason}"
            ) from error
        except (URLError, TimeoutError, OSError) as error:
            raise OllamaConnectionError(
                f"Unable to reach Ollama at {self.config.endpoint}: {error}"
            ) from error
        except json.JSONDecodeError as error:
            raise OllamaResponseError("Ollama returned invalid JSON") from error

    @classmethod
    def _extract_text(cls, response: dict[str, Any]) -> str:
        try:
            raw_text = response["message"]["content"]
        except (KeyError, TypeError) as error:
            raise OllamaResponseError("Ollama response has no message content") from error
        text = cls._normalize_text(raw_text)
        if not text:
            raise OllamaResponseError("Ollama returned an empty response")
        return text

    @staticmethod
    def _normalize_text(text: Any) -> str:
        if not isinstance(text, str):
            return ""
        lines = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("response:"):
                stripped = stripped[len("response:") :].strip()
            if stripped.startswith("(") and stripped.endswith(")"):
                continue
            if stripped.startswith("[") and stripped.endswith("]"):
                continue
            if stripped:
                lines.append(stripped)
        return " ".join(lines)

    def _trim_history(self) -> None:
        message_limit = self.config.max_history_turns * 2
        if len(self._history) > message_limit:
            del self._history[:-message_limit]