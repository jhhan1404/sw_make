# AI-assisted (Claude) — 정회성 검토 완료
"""예약 비즈니스 로직. (F-02)

예약 가능 여부(휴무일·영업시간·정원)는 AI가 아니라 이 코드가 판단한다. (CLAUDE.md 3-4)
상태 변경은 모두 apply()를 거쳐 State 클래스가 허용 여부를 정하고, 이력이 남는다. (F-02-4, F-02-5)
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.models import Customer, Reservation, ReservationHistory, Store
from app.repositories.reservation_repository import ReservationRepository
from app.services.reservation.schemas import ReservationCreate, ReservationSlot
from app.services.reservation.states import ReservationStatus, state_of

ACTIONS = ("confirm", "visit", "no_show", "cancel", "change")
# 점주가 누를 수 있는 동작. '변경'은 고객만 한다. (F-02-3, F-02-4)
OWNER_ACTIONS = ("confirm", "visit", "no_show", "cancel")
WEEKDAYS = "월화수목금토일"
NEW_MARK = "신규"  # 생성 이력의 '이전 상태' 자리에 쓴다.


class ReservationRejectedError(Exception):
    """휴무일·영업시간 외·정원 초과 등 매장 규칙에 맞지 않는 예약 (F-02-2)."""


class ReservationNotFoundError(Exception):
    """예약이 없거나, 연락처가 달라 본인 예약이 아닐 때."""


class StoreNotFoundError(Exception):
    """존재하지 않는 매장에 예약하려 할 때."""


@dataclass
class CustomerHistory:
    """점주의 고객 이력 조회 결과 (UC-10)."""

    customer: Customer
    reservations: list[Reservation]

    @property
    def visit_count(self) -> int:
        return sum(r.status == ReservationStatus.VISITED for r in self.reservations)

    @property
    def no_show_count(self) -> int:
        return sum(r.status == ReservationStatus.NO_SHOW for r in self.reservations)


class ReservationService:
    def __init__(self, session: Session, now: Callable[[], datetime] = datetime.now) -> None:
        self.session = session
        self.repo = ReservationRepository(session)
        self.now = now  # 테스트에서 '지금'을 고정하려고 주입받는다.

    # ----- 상태 전이 (F-02-4, F-02-5) -----
    def apply(self, reservation: Reservation, action: str) -> Reservation:
        """상태 전이를 적용하고 이력을 남긴다. 허용되지 않으면 InvalidTransitionError."""
        if action not in ACTIONS:
            raise ValueError(f"알 수 없는 동작: {action}")
        current = state_of(reservation.status)
        next_state = getattr(current, action)()
        reservation.histories.append(
            ReservationHistory(from_status=current.status.value, to_status=next_state.status.value)
        )
        reservation.status = next_state.status.value
        self.repo.save()
        return reservation

    def process(self, reservation_id: int, action: str) -> Reservation:
        """점주 처리: 확정·방문완료·노쇼·취소."""
        if action not in OWNER_ACTIONS:
            raise ValueError(f"점주가 할 수 없는 동작: {action}")
        return self.apply(self.get(reservation_id), action)

    # ----- 고객: 신청·조회·변경·취소 (F-02-1, F-02-3) -----
    def create(self, data: ReservationCreate) -> Reservation:
        store = self._store(data.store_id)
        self.check_slot(store, data.reserved_at, data.party_size)
        reservation = Reservation(
            store=store,
            customer=self.repo.find_or_create_customer(data.name, data.phone),
            reserved_at=data.reserved_at,
            party_size=data.party_size,
            request=data.request,
            status=ReservationStatus.REQUESTED.value,
        )
        history = ReservationHistory(
            reservation=reservation, from_status=NEW_MARK, to_status=reservation.status
        )
        return self.repo.add(reservation, history)

    def find_by_phone(self, phone: str) -> list[Reservation]:
        return self.repo.list_by_phone(phone)

    def change(self, reservation_id: int, phone: str, slot: ReservationSlot) -> Reservation:
        """날짜·시간·인원 변경. 확정된 예약도 다시 '요청'이 되어 점주가 재확정한다."""
        reservation = self.get_owned(reservation_id, phone)
        state_of(reservation.status).change()  # 변경 불가 상태면 정원 검사 전에 거부
        self.check_slot(
            reservation.store, slot.reserved_at, slot.party_size, exclude_id=reservation.id
        )
        reservation.reserved_at = slot.reserved_at
        reservation.party_size = slot.party_size
        return self.apply(reservation, "change")

    def cancel_by_customer(self, reservation_id: int, phone: str) -> Reservation:
        return self.apply(self.get_owned(reservation_id, phone), "cancel")

    # ----- 매장 규칙 검사 (F-02-2) -----
    def check_slot(
        self, store: Store, reserved_at: datetime, party_size: int, exclude_id: int | None = None
    ) -> None:
        if reserved_at <= self.now():
            raise ReservationRejectedError("지난 시간은 예약할 수 없습니다.")
        day = WEEKDAYS[reserved_at.weekday()]
        if day in _closed_days(store):
            raise ReservationRejectedError(f"{day}요일은 휴무일입니다.")
        if not store.open_time <= reserved_at.time() < store.close_time:
            raise ReservationRejectedError(
                f"영업시간({store.open_time:%H:%M}~{store.close_time:%H:%M}) 안에서만 "
                "예약할 수 있습니다."
            )
        self._check_capacity(store, reserved_at, party_size, exclude_id)

    def _check_capacity(
        self, store: Store, reserved_at: datetime, party_size: int, exclude_id: int | None
    ) -> None:
        """같은 1시간 대의 '요청'·'확정' 인원 합이 시간당 정원을 넘으면 거부한다."""
        start = reserved_at.replace(minute=0, second=0, microsecond=0)
        booked = self.repo.booked_party_size(
            store.id, start, start + timedelta(hours=1), exclude_id
        )
        left = max(store.capacity_per_hour - booked, 0)
        if party_size > left:
            raise ReservationRejectedError(
                f"{start:%H}시 대에는 {left}명까지만 예약할 수 있습니다. 다른 시간을 골라 주세요."
            )

    # ----- 조회 -----
    def get(self, reservation_id: int) -> Reservation:
        reservation = self.repo.get(reservation_id)
        if reservation is None:
            raise ReservationNotFoundError(f"예약을 찾을 수 없습니다 (id={reservation_id})")
        return reservation

    def get_owned(self, reservation_id: int, phone: str) -> Reservation:
        """연락처가 다르면 '없음'과 똑같이 처리해 다른 사람 예약이 있는지 드러내지 않는다."""
        reservation = self.repo.get(reservation_id)
        if reservation is None or reservation.customer.phone != phone:
            raise ReservationNotFoundError("예약을 찾을 수 없습니다. 연락처를 확인해 주세요.")
        return reservation

    def list_for_store(self, store_id: int, status: str | None = None) -> list[Reservation]:
        return self.repo.list_by_store(store_id, status)

    def customer_history(self, phone: str) -> CustomerHistory | None:
        """전화번호로 고객의 방문 횟수·예약 이력을 본다. (UC-10)"""
        customer = self.repo.find_customer(phone)
        if customer is None:
            return None
        return CustomerHistory(customer, self.repo.list_by_phone(phone))

    def _store(self, store_id: int) -> Store:
        store = self.repo.get_store(store_id)
        if store is None:
            raise StoreNotFoundError(f"매장을 찾을 수 없습니다 (id={store_id})")
        return store


def _closed_days(store: Store) -> set[str]:
    """'월,화' 같은 휴무일 문자열을 요일 집합으로 바꾼다."""
    return {d.strip() for d in store.closed_days.split(",") if d.strip()}
