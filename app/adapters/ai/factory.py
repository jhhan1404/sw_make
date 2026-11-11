# AI-assisted (Claude) — 정회성 검토 완료
"""설정(AI_PROVIDER)에 따라 사용할 AI 클라이언트를 고른다.

새 AI 제공사는 external_adapter.py에 HttpAIClient 하위 클래스를 만들고
아래 PROVIDERS에 한 줄만 추가한다. 서비스 코드는 바꾸지 않는다. (CLAUDE.md 4절)
"""

from app.adapters.ai.base import AIClient, AIClientError
from app.adapters.ai.external_adapter import (
    ClaudeAIClient,
    GeminiAIClient,
    GroqAIClient,
    HttpAIClient,
    OpenAIClient,
)
from app.adapters.ai.mock_adapter import MockAIClient
from app.config import AI_API_KEY, AI_MAX_RETRIES, AI_MODEL, AI_PROVIDER, AI_TIMEOUT

PROVIDERS: dict[str, type[HttpAIClient]] = {
    "claude": ClaudeAIClient,
    "gemini": GeminiAIClient,
    "openai": OpenAIClient,
    "groq": GroqAIClient,
}


def get_ai_client(
    provider: str = AI_PROVIDER,
    api_key: str = AI_API_KEY,
    model: str = AI_MODEL,
) -> AIClient:
    if provider == "mock":
        return MockAIClient()
    if provider not in PROVIDERS:
        allowed = ", ".join(["mock", *PROVIDERS])
        raise AIClientError(f"알 수 없는 AI_PROVIDER: {provider} (가능: {allowed})")
    return PROVIDERS[provider](
        api_key=api_key, model=model, timeout=AI_TIMEOUT, max_retries=AI_MAX_RETRIES
    )
