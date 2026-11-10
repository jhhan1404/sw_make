# AI-assisted (Claude) — 정회성 검토 완료
"""AI Adapter 테스트 (NF-03, F-03-5). 실제 네트워크 없이 가짜 HTTP 응답으로 확인한다."""

import json

import httpx
import pytest

from app.adapters.ai import AIClientError
from app.adapters.ai.external_adapter import ClaudeAIClient, GeminiAIClient, OpenAIClient
from app.adapters.ai.factory import get_ai_client
from app.adapters.ai.mock_adapter import MockAIClient

SAMPLE_RESPONSES = {
    ClaudeAIClient: {"content": [{"type": "text", "text": "답변입니다."}]},
    GeminiAIClient: {"candidates": [{"content": {"parts": [{"text": "답변입니다."}]}}]},
    OpenAIClient: {"choices": [{"message": {"content": "답변입니다."}}]},
}


def make_client(cls, status=200, body=None, error=None):
    """요청을 기록하고 정해진 응답을 돌려주는 가짜 전송 계층을 붙인다."""
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        if error:
            raise error
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(status, json=SAMPLE_RESPONSES[cls] if body is None else body)

    client = cls(api_key="test-key", model="test-model", transport=httpx.MockTransport(handler))
    return client, seen


@pytest.mark.parametrize("cls", [ClaudeAIClient, GeminiAIClient, OpenAIClient])
def test_generate_returns_text(cls):
    client, seen = make_client(cls)
    assert client.generate("질문", system="규칙") == "답변입니다."
    sent = json.dumps(seen["body"], ensure_ascii=False)
    assert "질문" in sent and "규칙" in sent


def test_claude_request_shape():
    client, seen = make_client(ClaudeAIClient)
    client.generate("질문", system="규칙")
    assert seen["url"].endswith("/v1/messages")
    assert seen["headers"]["x-api-key"] == "test-key"
    assert seen["body"]["system"] == "규칙" and seen["body"]["model"] == "test-model"


def test_gemini_request_shape():
    client, seen = make_client(GeminiAIClient)
    client.generate("질문", system="규칙")
    assert "/models/test-model:generateContent" in seen["url"]
    assert seen["headers"]["x-goog-api-key"] == "test-key"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "규칙"


def test_openai_request_shape():
    client, seen = make_client(OpenAIClient)
    client.generate("질문", system="규칙")
    assert seen["headers"]["authorization"] == "Bearer test-key"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "규칙"}


@pytest.mark.parametrize("cls", [ClaudeAIClient, GeminiAIClient, OpenAIClient])
def test_http_error_becomes_ai_client_error(cls):
    client, _ = make_client(cls, status=500, body={"error": "x"})
    with pytest.raises(AIClientError, match="HTTP 500"):
        client.generate("질문")


@pytest.mark.parametrize("cls", [ClaudeAIClient, GeminiAIClient, OpenAIClient])
def test_malformed_response_becomes_ai_client_error(cls):
    client, _ = make_client(cls, body={"unexpected": True})
    with pytest.raises(AIClientError, match="해석할 수 없습니다"):
        client.generate("질문")


def test_connection_error_becomes_ai_client_error():
    client, _ = make_client(ClaudeAIClient, error=httpx.ConnectError("down"))
    with pytest.raises(AIClientError, match="연결 실패"):
        client.generate("질문")


def test_timeout_becomes_ai_client_error():
    client, _ = make_client(OpenAIClient, error=httpx.ReadTimeout("slow"))
    with pytest.raises(AIClientError, match="시간 초과"):
        client.generate("질문")


def test_missing_key_or_model():
    with pytest.raises(AIClientError, match="AI_API_KEY"):
        ClaudeAIClient(api_key="", model="m").generate("질문")
    with pytest.raises(AIClientError, match="AI_MODEL"):
        ClaudeAIClient(api_key="k", model="").generate("질문")


def test_api_key_never_in_error_message():
    client, _ = make_client(ClaudeAIClient, status=401, body={})
    with pytest.raises(AIClientError) as info:
        client.generate("질문")
    assert "test-key" not in str(info.value)


def test_factory_selects_provider():
    assert isinstance(get_ai_client("mock"), MockAIClient)
    assert isinstance(get_ai_client("claude", "k", "m"), ClaudeAIClient)
    assert isinstance(get_ai_client("gemini", "k", "m"), GeminiAIClient)
    assert isinstance(get_ai_client("openai", "k", "m"), OpenAIClient)
    with pytest.raises(AIClientError, match="알 수 없는"):
        get_ai_client("unknown")
