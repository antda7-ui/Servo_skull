import json

import pytest

from servo_skull.config import OllamaConfig
from servo_skull.ollama import (
    PERSONA_SYSTEM_PROMPT,
    OllamaAdapter,
    OllamaConnectionError,
    OllamaResponseError,
)


class FakeResponse:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


def make_adapter(max_history_turns=2):
    return OllamaAdapter(
        OllamaConfig(
            endpoint="http://127.0.0.1:11434/api/chat",
            model="test-model",
            timeout_seconds=3.0,
            max_history_turns=max_history_turns,
        )
    )


def test_persona_prompt_contains_contract_and_no_phrase_bank():
    assert "1 to 4 sentences" in PERSONA_SYSTEM_PROMPT
    assert "fresh wording" in PERSONA_SYSTEM_PROMPT
    assert "stage directions" in PERSONA_SYSTEM_PROMPT
    assert "canned phrase bank" in PERSONA_SYSTEM_PROMPT


def test_chat_posts_expected_payload_and_keeps_bounded_history(monkeypatch):
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse({"message": {"content": " Acknowledged.\n"}})

    monkeypatch.setattr("servo_skull.ollama.urlopen", fake_urlopen)
    adapter = make_adapter(max_history_turns=1)

    adapter.chat("First request")
    result = adapter.chat("Second request")

    payload = json.loads(requests[1][0].data)
    assert requests[1][1] == 3.0
    assert payload["model"] == "test-model"
    assert payload["stream"] is False
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][0]["content"] == PERSONA_SYSTEM_PROMPT
    assert payload["messages"][-1] == {"role": "user", "content": "Second request"}
    assert result.text == "Acknowledged."
    assert len(adapter.history) == 2


def test_chat_normalizes_spoken_output(monkeypatch):
    monkeypatch.setattr(
        "servo_skull.ollama.urlopen",
        lambda request, timeout: FakeResponse(
            {"message": {"content": "Response: Ready.\n(voice lowers)\nProceed."}}
        ),
    )

    assert make_adapter().chat("Continue").text == "Ready. Proceed."


def test_chat_rejects_empty_prompt():
    with pytest.raises(OllamaResponseError, match="empty prompt"):
        make_adapter().chat("  \n")


def test_chat_rejects_invalid_response(monkeypatch):
    monkeypatch.setattr(
        "servo_skull.ollama.urlopen",
        lambda request, timeout: FakeResponse({"done": True}),
    )

    with pytest.raises(OllamaResponseError, match="no message content"):
        make_adapter().chat("Status")


def test_chat_reports_connection_failure(monkeypatch):
    def fail(request, timeout):
        raise OSError("connection refused")

    monkeypatch.setattr("servo_skull.ollama.urlopen", fail)

    with pytest.raises(OllamaConnectionError, match="connection refused"):
        make_adapter().chat("Status")