# AI-assisted (Claude) — 정회성 검토 완료
"""예약 데이터 조회·저장 (데이터 계층, F-02). 서비스는 SQL을 직접 쓰지 않고 이 클래스를 쓴다."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.models import Customer, Reservation, ReservationHistory, Store

# 정원 계산에 포함하는 상태. 취소·노쇼·방문완료는 자리를 차지하지 않는다.
ACTIVE_STATUSES = ("요청", "확정")


class ReservationRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_stores(self) -> list[Store]:
        return list(self.session.scalars(select(Store).order_by(Store.id)))

    def get_store(self, store_id: int) -> Store | None:
        return self.session.get(Store, store_id)

    def find_customer(self, phone: str) -> Customer | None:
        return self.session.scalar(select(Customer).where(Customer.phone == phone))

    def find_or_create_customer(self, name: str, phone: str) -> Customer:
        """연락처가 같으면 같은 고객으로 본다. (문의 등록과 같은 기준)"""
        customer = self.find_customer(phone)
        if customer is None:
            customer = Customer(name=name, phone=phone)
            self.session.add(customer)
        return customer

    def get(self, reservation_id: int) -> Reservation | None:
        return self.session.get(Reservation, reservation_id)

    def add(self, reservation: Reservation, history: ReservationHistory) -> Reservation:
        self.session.add_all([reservation, history])
        self.session.commit()
        return reservation

    def booked_party_size(
        self, store_id: int, start: datetime, end: datetime, exclude_id: int | None = None
    ) -> int:
        """[start, end) 시간대에 이미 잡힌 인원 합계. 변경할 때는 자기 자신을 뺀다."""
        stmt = select(func.coalesce(func.sum(Reservation.party_size), 0)).where(
            Reservation.store_id == store_id,
            Reservation.status.in_(ACTIVE_STATUSES),
            Reservation.reserved_at >= start,
            Reservation.reserved_at < end,
        )
        if exclude_id is not None:
            stmt = stmt.where(Reservation.id != exclude_id)
        return int(self.session.scalar(stmt))

    def list_by_phone(self, phone: str) -> list[Reservation]:
        """고객 본인 예약 조회 (F-02-3). 최근 일정부터."""
        stmt = (
            select(Reservation)
            .join(Reservation.customer)
            .where(Customer.phone == phone)
            .order_by(Reservation.reserved_at.desc())
        )
        return list(self.session.scalars(stmt))

    def list_by_store(self, store_id: int, status: str | None = None) -> list[Reservation]:
        stmt = select(Reservation).where(Reservation.store_id == store_id)
        if status:
            stmt = stmt.where(Reservation.status == status)
        return list(self.session.scalars(stmt.order_by(Reservation.reserved_at)))

    def save(self) -> None:
        self.session.commit()
