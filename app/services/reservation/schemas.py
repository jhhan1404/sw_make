# AI-assisted (Claude) — 정회성 검토 완료
"""예약 신청·변경 입력 검증 (F-02-1, F-02-3). CLAUDE.md 5-1: 외부 입력은 Pydantic으로 검증한다.

형식 검증만 한다. 휴무일·영업시간·정원 같은 매장 규칙은 DB가 필요하므로 서비스에서 검사한다.
"""

from datetime import date, datetime, time

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.services.inquiry.schemas import PHONE_PATTERN

MAX_PARTY_SIZE = 20
MAX_REQUEST_LENGTH = 300

FIELD_LABELS = {
    "store_id": "매장",
    "name": "이름",
    "phone": "연락처",
    "visit_date": "방문 날짜",
    "visit_time": "방문 시간",
    "party_size": "인원",
    "request": "요청 사항",
}


class ReservationSlot(BaseModel):
    """날짜·시간·인원. 신청과 변경이 같은 규칙을 쓴다."""

    model_config = ConfigDict(str_strip_whitespace=True)

    visit_date: date
    visit_time: time
    party_size: int = Field(ge=1, le=MAX_PARTY_SIZE)

    @property
    def reserved_at(self) -> datetime:
        return datetime.combine(self.visit_date, self.visit_time)


class ReservationCreate(ReservationSlot):
    store_id: int
    name: str = Field(min_length=1, max_length=50)
    phone: str = Field(pattern=PHONE_PATTERN)
    request: str = Field(default="", max_length=MAX_REQUEST_LENGTH)


def korean_errors(error: ValidationError) -> list[str]:
    """Pydantic 오류를 사용자에게 보여줄 한국어 문장으로 바꾼다."""
    messages = []
    for e in error.errors():
        label = FIELD_LABELS.get(str(e["loc"][0]), str(e["loc"][0]))
        kind = e["type"]
        if kind == "string_too_short":
            messages.append(f"{label}을(를) 입력해 주세요.")
        elif kind == "string_too_long":
            messages.append(f"{label}은(는) {e['ctx']['max_length']:,}자 이하로 입력해 주세요.")
        elif kind == "string_pattern_mismatch":
            messages.append(f"{label} 형식이 올바르지 않습니다. (예: 010-1234-5678)")
        elif kind in ("greater_than_equal", "less_than_equal"):
            messages.append(f"{label}은(는) 1명 이상 {MAX_PARTY_SIZE}명 이하로 입력해 주세요.")
        else:
            messages.append(f"{label}을(를) 확인해 주세요.")
    return messages
