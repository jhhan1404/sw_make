# AI-assisted (Claude) — 정회성 검토 완료
"""실제 AI API 연결 확인. `.env`에 키를 넣은 뒤 한 번 실행한다.

실행: python -m app.adapters.ai.check
"""

from app.adapters.ai import AIClientError, get_ai_client
from app.config import AI_MODEL, AI_PROVIDER


def main() -> int:
    print(f"AI_PROVIDER={AI_PROVIDER}, AI_MODEL={AI_MODEL or '(미설정)'}")
    try:
        client = get_ai_client()
        text = client.generate(
            "손님에게 한 문장으로 인사해 주세요.", system="당신은 친절한 카페 직원입니다."
        )
    except AIClientError as e:
        print(f"실패: {e}")
        return 1
    print(f"성공: {text}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
