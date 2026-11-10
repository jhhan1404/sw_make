# AI-assisted (Claude) — 정회성 검토 완료
"""실제 생성형 AI API Adapter (Adapter 패턴의 Adapter).

세 API는 요청·응답 JSON 모양만 다르고 "보내고 → 받고 → 텍스트 꺼내기" 흐름은 같다.
공통 흐름은 HttpAIClient.generate()에 두고, API별 차이(주소·헤더·본문·응답 해석)만
하위 클래스가 구현한다. 서비스 계층은 AIClient.generate()만 알면 된다. (NF-03)

어떤 실패든 AIClientError로 바꿔서 던진다. API 키는 오류 메시지에 절대 넣지 않는다.
"""

import time
from abc import abstractmethod
from collections.abc import Callable
from typing import Any

import httpx

from app.adapters.ai.base import AIClient, AIClientError

MAX_OUTPUT_TOKENS = 1024
# 429(호출 한도 초과), 503(일시 과부하)은 잠깐 기다리면 풀리는 경우가 많아 다시 시도한다.
# 무료 등급(Gemini)에서 검증 실험 30건을 연달아 돌릴 때를 대비한 설정.
RETRY_STATUS = {429, 503}


class HttpAIClient(AIClient):
    """HTTP로 호출하는 AI API의 공통 흐름."""

    provider_name: str = ""

    def __init__(
        self,
        api_key: str,
        model: str,
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 2,
        retry_wait: float = 5.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.transport = transport  # 테스트에서 가짜 응답을 넣을 때만 사용
        self.max_retries = max_retries
        self.retry_wait = retry_wait
        self.sleep = sleep  # 테스트에서는 실제로 기다리지 않도록 바꿔 끼운다

    def generate(self, prompt: str, system: str | None = None) -> str:
        self._check_config()
        body = self.payload(prompt, system)
        response = self._post(body)
        for attempt in range(1, self.max_retries + 1):
            if response.status_code not in RETRY_STATUS:
                break
            self.sleep(self.retry_wait * attempt)
            response = self._post(body)
        return self._extract_text(response)

    def _check_config(self) -> None:
        if not self.api_key:
            raise AIClientError("AI_API_KEY가 설정되지 않았습니다 (.env 확인)")
        if not self.model:
            raise AIClientError("AI_MODEL이 설정되지 않았습니다 (.env 확인)")

    def _post(self, body: dict[str, Any]) -> httpx.Response:
        try:
            with httpx.Client(timeout=self.timeout, transport=self.transport) as client:
                return client.post(self.endpoint(), headers=self.headers(), json=body)
        except httpx.TimeoutException as e:
            raise AIClientError(f"{self.provider_name} 응답 시간 초과") from e
        except httpx.HTTPError as e:
            raise AIClientError(f"{self.provider_name} 연결 실패: {type(e).__name__}") from e

    def _extract_text(self, response: httpx.Response) -> str:
        if response.status_code == 429:
            raise AIClientError(
                f"{self.provider_name} 호출 한도 초과 (HTTP 429). 잠시 후 다시 시도"
            )
        if response.status_code != 200:
            raise AIClientError(f"{self.provider_name} 오류 (HTTP {response.status_code})")
        try:
            text = self.parse(response.json())
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise AIClientError(f"{self.provider_name} 응답 형식을 해석할 수 없습니다") from e
        if not text or not text.strip():
            raise AIClientError(f"{self.provider_name} 응답이 비어 있습니다")
        return text.strip()

    @abstractmethod
    def endpoint(self) -> str: ...

    @abstractmethod
    def headers(self) -> dict[str, str]: ...

    @abstractmethod
    def payload(self, prompt: str, system: str | None) -> dict[str, Any]: ...

    @abstractmethod
    def parse(self, data: dict[str, Any]) -> str: ...


class ClaudeAIClient(HttpAIClient):
    """Anthropic Messages API."""

    provider_name = "Claude"

    def endpoint(self) -> str:
        return "https://api.anthropic.com/v1/messages"

    def headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    def payload(self, prompt: str, system: str | None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": MAX_OUTPUT_TOKENS,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            body["system"] = system
        return body

    def parse(self, data: dict[str, Any]) -> str:
        return "".join(b["text"] for b in data["content"] if b.get("type") == "text")


class GeminiAIClient(HttpAIClient):
    """Google Gemini API (generateContent)."""

    provider_name = "Gemini"
    # Gemini 3 계열은 답하기 전에 '생각(thinking)'을 하고, 그 분량도 출력 한도에 포함된다.
    # 한도가 작으면 생각만 하다 답이 비어서 오므로 넉넉하게 둔다. (무료 등급은 토큰 요금 없음)
    max_output_tokens = 8192

    def endpoint(self) -> str:
        base = "https://generativelanguage.googleapis.com/v1beta/models"
        return f"{base}/{self._model_id()}:generateContent?key={self.api_key}"

    def _model_id(self) -> str:
        """AI Studio 예제 코드의 'models/gemini-...' 형식도 그대로 받는다."""
        return self.model.removeprefix("models/")

    def headers(self) -> dict[str, str]:
        return {}

    def payload(self, prompt: str, system: str | None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": self.max_output_tokens},
        }
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        return body

    def parse(self, data: dict[str, Any]) -> str:
        candidate = data["candidates"][0]
        parts = candidate.get("content", {}).get("parts", [])
        # 생각 요약(thought)이 섞여 오면 빼고 실제 답변만 쓴다.
        text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
        if not text.strip() and "finishReason" in candidate:
            reason = candidate["finishReason"]
            raise AIClientError(f"Gemini 응답이 비어 있습니다 (finishReason={reason})")
        return text


class OpenAIClient(HttpAIClient):
    """OpenAI Chat Completions API."""

    provider_name = "OpenAI"

    def endpoint(self) -> str:
        return "https://api.openai.com/v1/chat/completions"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def payload(self, prompt: str, system: str | None) -> dict[str, Any]:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        return {"model": self.model, "messages": messages}

    def parse(self, data: dict[str, Any]) -> str:
        return data["choices"][0]["message"]["content"]


class GroqAIClient(HttpAIClient):
    """Groq Cloud API (OpenAI-compatible)."""

    provider_name = "Groq"

    def endpoint(self) -> str:
        return "https://api.groq.com/openai/v1/chat/completions"

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def payload(self, prompt: str, system: str | None) -> dict[str, Any]:
        messages = [{"role": "system", "content": system}] if system else []
        messages.append({"role": "user", "content": prompt})
        return {"model": self.model, "messages": messages}

    def parse(self, data: dict[str, Any]) -> str:
        return data["choices"][0]["message"]["content"]
