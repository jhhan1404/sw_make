# AI-assisted (Claude) — 정회성 검토 완료
"""F-02 예약 신청·조회·변경·취소·상태 처리 테스트 (12주차).

메모리 DB에 가상 데이터를 넣고, '지금'을 2026-11-10(화) 09:00으로 고정해 서비스와 화면을 확인한다.
온기 카페: 09:00~21:00, 월 휴무, 시간당 10명 / 가상 데이터에 11/15 10시 대 10명이 이미 차 있음.
"""

from datetime import date, datetime, time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_session
from app.db.seed import load_all
from app.main import app
from app.models.models import Reservation, Store
from app.presentation.routers.reservation import get_service
from app.services.reservation.schemas import ReservationCreate, ReservationSlot, korean_errors
from app.services.reservation.service import (
    NEW_MARK,
    ReservationNotFoundError,
    ReservationRejectedError,
    ReservationService,
    StoreNotFoundError,
)
from app.services.reservation.states import InvalidTransitionError

NOW = datetime(2026, 11, 10, 9, 0)
PHONE = "010-9999-0000"


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


@pytest.fixture
def service(session) -> ReservationService:
    return ReservationService(session, now=lambda: NOW)


def cafe(session) -> Store:
    return session.query(Store).filter_by(name="온기 카페").one()


def booking(store_id: int, **overrides) -> ReservationCreate:
    data = {
        "store_id": store_id,
        "name": "테스트",
        "phone": PHONE,
        "visit_date": date(2026, 11, 11),  # 수요일
        "visit_time": time(12, 0),
        "party_size": 2,
    }
    return ReservationCreate(**(data | overrides))


def slot(day: int, hour: int, party_size: int = 2) -> ReservationSlot:
    return ReservationSlot(
        visit_date=date(2026, 11, day), visit_time=time(hour, 0), party_size=party_size
    )


# ---------- F-02-1 예약 신청 ----------


def test_create_starts_as_requested_with_history(service, session):
    r = service.create(booking(cafe(session).id, request="창가 자리"))
    assert r.id and r.status == "요청" and r.request == "창가 자리"
    assert r.reserved_at == datetime(2026, 11, 11, 12, 0)
    assert [(h.from_status, h.to_status) for h in r.histories] == [(NEW_MARK, "요청")]


def test_create_reuses_customer_by_phone(service, session):
    a = service.create(booking(cafe(session).id))
    b = service.create(booking(cafe(session).id, visit_time=time(15, 0)))
    assert a.customer_id == b.customer_id


def test_create_unknown_store(service):
    with pytest.raises(StoreNotFoundError):
        service.create(booking(9999))


# ---------- F-02-2 휴무일·영업시간·정원 거부 ----------


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"visit_date": date(2026, 11, 16)}, "월요일은 휴무일입니다."),
        ({"visit_time": time(8, 30)}, "영업시간(09:00~21:00)"),
        ({"visit_time": time(21, 0)}, "영업시간(09:00~21:00)"),  # 마감 시각 정각도 불가
        ({"visit_date": date(2026, 11, 9)}, "지난 시간은 예약할 수 없습니다."),
        ({"party_size": 11}, "12시 대에는 10명까지만"),
        ({"visit_date": date(2026, 11, 15), "visit_time": time(10, 0)}, "10시 대에는 0명까지만"),
    ],
)
def test_create_rejected_by_store_rules(service, session, overrides, message):
    with pytest.raises(ReservationRejectedError) as info:
        service.create(booking(cafe(session).id, **overrides))
    assert message in str(info.value)


def test_capacity_counts_same_hour_only_active(service, session):
    store_id = cafe(session).id
    service.create(booking(store_id, party_size=6))
    service.create(booking(store_id, visit_time=time(12, 30), party_size=4))  # 같은 12시 대, 10명
    with pytest.raises(ReservationRejectedError):
        service.create(booking(store_id, visit_time=time(12, 45), party_size=1))
    assert service.create(booking(store_id, visit_time=time(13, 0), party_size=1))


def test_cancelled_reservation_frees_capacity(service, session):
    store_id = cafe(session).id
    full = service.create(booking(store_id, party_size=10))
    service.cancel_by_customer(full.id, PHONE)
    assert service.create(booking(store_id, party_size=10)).status == "요청"


# ---------- F-02-3 고객 조회·변경·취소 ----------


def test_find_by_phone_returns_only_mine(service, session):
    mine = service.create(booking(cafe(session).id))
    found = service.find_by_phone(PHONE)
    assert [r.id for r in found] == [mine.id]
    assert len(service.find_by_phone("010-0000-0101")) == 3  # 가상 데이터 김하늘 예약


def test_change_confirmed_goes_back_to_requested(service, session):
    r = service.create(booking(cafe(session).id))
    service.process(r.id, "confirm")
    changed = service.change(r.id, PHONE, slot(12, 18, party_size=4))
    assert changed.status == "요청"  # 확정 후 변경하면 점주가 다시 확정
    assert changed.reserved_at == datetime(2026, 11, 12, 18, 0) and changed.party_size == 4


def test_change_excludes_itself_from_capacity(service, session):
    r = service.create(booking(cafe(session).id, party_size=10))
    assert service.change(r.id, PHONE, slot(11, 12, party_size=9)).party_size == 9


def test_change_rejected_slot_keeps_original(service, session):
    r = service.create(booking(cafe(session).id))
    with pytest.raises(ReservationRejectedError):
        service.change(r.id, PHONE, slot(16, 12))  # 월요일
    session.refresh(r)
    assert r.reserved_at == datetime(2026, 11, 11, 12, 0) and r.status == "요청"


def test_change_or_cancel_with_other_phone_is_not_found(service, session):
    r = service.create(booking(cafe(session).id))
    with pytest.raises(ReservationNotFoundError):
        service.change(r.id, "010-1111-2222", slot(12, 12))
    with pytest.raises(ReservationNotFoundError):
        service.cancel_by_customer(r.id, "010-1111-2222")


@pytest.mark.parametrize("final", ["visit", "no_show", "cancel"])
def test_cannot_change_or_cancel_after_final_state(service, session, final):
    r = service.create(booking(cafe(session).id))
    if final != "cancel":
        service.process(r.id, "confirm")
    service.process(r.id, final)
    with pytest.raises(InvalidTransitionError):
        service.change(r.id, PHONE, slot(12, 12))
    with pytest.raises(InvalidTransitionError):
        service.cancel_by_customer(r.id, PHONE)


# ---------- F-02-4 점주 처리, F-02-5 이력 ----------


def test_owner_flow_records_every_change(service, session):
    r = service.create(booking(cafe(session).id))
    service.process(r.id, "confirm")
    service.process(r.id, "visit")
    pairs = [(h.from_status, h.to_status) for h in r.histories]
    assert pairs == [(NEW_MARK, "요청"), ("요청", "확정"), ("확정", "방문완료")]
    assert all(h.changed_at for h in r.histories)


def test_owner_invalid_transition_keeps_state_and_history(service, session):
    r = service.create(booking(cafe(session).id))
    with pytest.raises(InvalidTransitionError):
        service.process(r.id, "visit")  # 확정 전에는 방문 처리 불가
    assert r.status == "요청" and len(r.histories) == 1


def test_owner_cannot_use_change_action(service, session):
    r = service.create(booking(cafe(session).id))
    with pytest.raises(ValueError):
        service.process(r.id, "change")


def test_customer_history_counts_visits(service):
    history = service.customer_history("010-0000-0101")
    assert history.customer.name == "김하늘"
    assert history.visit_count == 1 and len(history.reservations) == 3
    assert service.customer_history("010-1111-2222") is None


# ---------- 입력 검증 (한국어 메시지) ----------


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("name", "", "이름을(를) 입력해 주세요."),
        ("phone", "12345", "연락처 형식이 올바르지 않습니다. (예: 010-1234-5678)"),
        ("party_size", 0, "인원은(는) 1명 이상 20명 이하로 입력해 주세요."),
        ("party_size", 21, "인원은(는) 1명 이상 20명 이하로 입력해 주세요."),
        ("visit_date", "", "방문 날짜을(를) 확인해 주세요."),
    ],
)
def test_invalid_input_has_korean_message(field, value, message):
    data = {"store_id": 1, "name": "a", "phone": PHONE, "visit_date": "2026-11-11"}
    data |= {"visit_time": "12:00", "party_size": 2, field: value}
    with pytest.raises(ValidationError) as info:
        ReservationCreate(**data)
    assert message in korean_errors(info.value)


# ---------- 화면 ----------


@pytest.fixture
def client(session_factory):
    def _session():
        with session_factory() as s:
            yield s

    def _service():
        with session_factory() as s:
            yield ReservationService(s, now=lambda: NOW)

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[get_service] = _service
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def form(store_id: int, **overrides) -> dict:
    data = {"store_id": store_id, "name": "테스트", "phone": PHONE}
    data |= {"visit_date": "2026-11-11", "visit_time": "12:00", "party_size": "2"}
    return data | overrides


def test_pages_open(client):
    for url in ("/", "/reservations/new", "/reservations/lookup", "/owner/reservations"):
        assert client.get(url).status_code == 200, url
    assert "김하늘" in client.get("/owner/customers?phone=010-0000-0101").text


def test_submit_and_lookup(client, session):
    res = client.post("/reservations", data=form(cafe(session).id))
    assert res.status_code == 200 and "예약을 신청했습니다" in res.text
    res = client.post("/reservations/lookup", data={"phone": PHONE})
    assert "온기 카페" in res.text and "2026-11-11 12:00" in res.text


def test_submit_rejected_shows_reason(client, session):
    res = client.post("/reservations", data=form(cafe(session).id, visit_date="2026-11-16"))
    assert res.status_code == 400 and "월요일은 휴무일입니다." in res.text


def test_customer_change_and_cancel(client, session):
    client.post("/reservations", data=form(cafe(session).id))
    rid = session.query(Reservation).filter(Reservation.customer.has(phone=PHONE)).one().id
    change = {"phone": PHONE, "visit_date": "2026-11-12", "visit_time": "18:00", "party_size": "3"}
    res = client.post(f"/reservations/{rid}/change", data=change)
    assert "예약을 변경했습니다" in res.text and "2026-11-12 18:00" in res.text
    res = client.post(f"/reservations/{rid}/cancel", data={"phone": PHONE})
    assert "예약을 취소했습니다" in res.text


def test_customer_other_phone_cannot_edit(client, session):
    rid = session.query(Reservation).first().id
    res = client.post(f"/reservations/{rid}/edit", data={"phone": "010-1111-2222"})
    assert res.status_code == 404 and "연락처를 확인해 주세요" in res.text


def test_owner_process_and_invalid_transition(client, session):
    client.post("/reservations", data=form(cafe(session).id))
    rid = session.query(Reservation).filter(Reservation.customer.has(phone=PHONE)).one().id
    res = client.post(f"/owner/reservations/{rid}/visit")  # 요청 상태에서 방문 처리 → 거부
    assert "할 수 없습니다" in res.text
    res = client.post(f"/owner/reservations/{rid}/confirm")
    assert res.status_code == 200 and "확정" in res.text and "상태 변경 이력" in res.text
    assert client.post(f"/owner/reservations/{rid}/change").status_code == 400
    assert client.get("/owner/reservations/99999").status_code == 404


def test_lookup_unknown_phone_shows_empty_message(client):
    res = client.post("/reservations/lookup", data={"phone": "010-1111-2222"})
    assert res.status_code == 200 and "이 연락처로 된 예약이 없습니다." in res.text
