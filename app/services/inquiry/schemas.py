# AI-assisted (Claude) — 정회성 검토 완료
"""문의 등록 입력 검증 (F-03-1). CLAUDE.md 5-1: 외부 입력은 Pydantic으로 검증한다."""

from pydantic import BaseModel, ConfigDict, Field, ValidationError

MAX_CONTENT_LENGTH = 1000
PHONE_PATTERN = r"^01[016789]-?\d{3,4}-?\d{4}$"

FIELD_LABELS = {"store_id": "매장", "name": "이름", "phone": "연락처", "content": "문의 내용"}


class InquiryCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    store_id: int
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=PHONE_PATTERN)
    content: str = Field(min_length=1, max_length=MAX_CONTENT_LENGTH)


def korean_errors(error: ValidationError) -> list[str]:
    """Pydantic 오류를 사용자에게 보여줄 한국어 문장으로 바꾼다."""
    messages = []
    for e in error.errors():
        label = FIELD_LABELS.get(str(e["loc"][0]), str(e["loc"][0]))
        if e["type"] == "string_too_short":
            messages.append(f"{label}을(를) 입력해 주세요.")
        elif e["type"] == "string_too_long":
            messages.append(f"{label}은(는) {e['ctx']['max_length']:,}자 이하로 입력해 주세요.")
        elif e["type"] == "string_pattern_mismatch":
            messages.append(f"{label} 형식이 올바르지 않습니다. (예: 010-1234-5678)")
        else:
            messages.append(f"{label}을(를) 확인해 주세요.")
    return messages
