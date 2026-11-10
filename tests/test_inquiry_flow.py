# AI-assisted (Claude) — 정회성 검토 완료
"""F-03 문의 등록 → AI 초안 생성 → DB 대조 흐름 테스트 (12주차).

메모리 DB에 가상 데이터를 넣고, AI는 Mock으로 바꿔서 서비스와 화면을 모두 확인한다.
"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.adapters.ai.mock_adapter import MockAIClient
from app.db.database import Base, get_session
from app.db.seed import load_all
from app.main import app
from app.models.models import Inquiry, Store
from app.presentation.routers.inquiry import get_ai
from app.repositories.inquiry_repository import InquiryRepository
from app.services.inquiry.schemas import InquiryCreate, korean_errors
from app.services.inquiry.service import InquiryNotFoundError, InquiryService, StoreNotFoundError


@pytest.fixture
def session_factory():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)
    with factory() as s:
        load_all(s)
        s.commit()
    return factory


@pytest.fixture
def session(session_factory):
    with session_factory() as s:
        yield s


def service_with(session, ai=None) -> InquiryService:
    return InquiryService(ai or MockAIClient(), InquiryRepository(session))


def cafe(session) -> Store:
    return session.query(Store).filter_by(name="온기 카페").one()


def valid_form(store_id: int, **overrides) -> dict:
    form = {
        "store_id": store_id,
        "name": "테스트",
        "phone": "010-9999-0000",
        "content": "주차 되나요?",
    }
    return form | overrides


# ---------- 서비스: F-03-1 문의 등록 ----------


def test_register_creates_unanswered_inquiry(session):
    inquiry = service_with(session).register(InquiryCreate(**valid_form(cafe(session).id)))
    assert inquiry.id and inquiry.status == "미응답"
    assert inquiry.customer.phone == "010-9999-0000"


def test_register_reuses_customer_by_phone(session):
    service = service_with(session)
    a = service.register(InquiryCreate(**valid_form(cafe(session).id)))
    b = service.register(InquiryCreate(**valid_form(cafe(session).id, content="와이파이?")))
    assert a.customer_id == b.customer_id


def test_register_unknown_store(session):
    with pytest.raises(StoreNotFoundError):
        service_with(session).register(InquiryCreate(**valid_form(9999)))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("content", "   ", "문의 내용을(를) 입력해 주세요."),
        ("content", "가" * 1001, "문의 내용은(는) 1,000자 이하로 입력해 주세요."),
        ("phone", "12345", "연락처 형식이 올바르지 않습니다. (예: 010-1234-5678)"),
        ("name", "", "이름을(를) 입력해 주세요."),
    ],
)
def test_invalid_input_has_korean_message(field, value, message):
    with pytest.raises(ValidationError) as info:
        InquiryCreate(**valid_form(1, **{field: value}))
    assert message in korean_errors(info.value)


# ---------- 서비스: F-03-2, F-03-3 초안 생성과 대조 결과 저장 ----------


def first_inquiry(session) -> Inquiry:
    return session.query(Inquiry).filter_by(store_id=cafe(session).id).first()


def test_generate_draft_saves_ai_draft_and_check(session):
    ai = MockAIClient(fixed_response="아메리카노는 4,500원, 09:00~21:00 영업합니다.")
    q = first_inquiry(session)
    result = service_with(session, ai).generate_draft(q.id)
    session.refresh(q)
    assert result.mismatches == [] and q.ai_draft.startswith("아메리카노")
    assert InquiryService.mismatches_of(q) == []
    assert q.status == "미응답"  # 발송 전까지는 미응답 유지 (F-03-4는 점주 확정 후)


def test_generate_draft_records_mismatch(session):
    ai = MockAIClient(fixed_response="아메리카노는 3,000원이고 22:00까지 합니다.")
    q = first_inquiry(session)
    service_with(session, ai).generate_draft(q.id)
    session.refresh(q)
    kinds = [m["kind"] for m in InquiryService.mismatches_of(q)]
    assert kinds == ["가격", "시각"]


def test_prompt_uses_seeded_store_data(session):
    ai = MockAIClient()
    service_with(session, ai).generate_draft(first_inquiry(session).id)
    assert "밤라떼: 6,000원" in ai.last_prompt and "휴무일 월" in ai.last_prompt


def test_generate_draft_ai_failure_keeps_inquiry(session):
    q = first_inquiry(session)
    result = service_with(session, MockAIClient(fail=True)).generate_draft(q.id)
    session.refresh(q)
    assert result.error and q.ai_draft is None


def test_generate_draft_unknown_inquiry(session):
    with pytest.raises(InquiryNotFoundError):
        service_with(session).generate_draft(9999)


# ---------- 화면 (라우터) ----------


@pytest.fixture
def client(session_factory):
    ai = MockAIClient(fixed_response="아메리카노는 4,000원입니다.")

    def override_session():
        with session_factory() as s:
            yield s

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_ai] = lambda: ai
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_customer_form_lists_stores(client):
    page = client.get("/inquiries/new")
    assert page.status_code == 200 and "온기 카페" in page.text and "결 헤어" in page.text


def test_customer_submit_success(client):
    page = client.post("/inquiries", data=valid_form(1))
    assert page.status_code == 200 and "문의가 접수되었습니다" in page.text


def test_customer_submit_invalid_shows_errors_and_keeps_input(client):
    page = client.post("/inquiries", data=valid_form(1, phone="abc", content="그대로 남아야 함"))
    assert page.status_code == 400
    assert "연락처 형식이 올바르지 않습니다" in page.text and "그대로 남아야 함" in page.text


def test_owner_list_shows_unanswered(client):
    page = client.get("/owner/inquiries?store_id=1")
    assert page.status_code == 200 and "미응답" in page.text and "아메리카노 한 잔" in page.text


def test_owner_generate_draft_shows_warning(client):
    redirect = client.post("/owner/inquiries/1/draft", follow_redirects=False)
    assert redirect.status_code == 303
    page = client.get(redirect.headers["location"])
    assert "4,000원" in page.text and "매장 정보와 다른 내용" in page.text


def test_owner_detail_404(client):
    assert client.get("/owner/inquiries/9999").status_code == 404


def test_owner_draft_ai_failure_message(client):
    app.dependency_overrides[get_ai] = lambda: MockAIClient(fail=True)
    redirect = client.post("/owner/inquiries/2/draft", follow_redirects=False)
    assert redirect.headers["location"].endswith("?ai_error=1")
    assert "직접 답변을 작성" in client.get(redirect.headers["location"]).text
