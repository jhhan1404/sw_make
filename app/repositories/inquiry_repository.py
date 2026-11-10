# AI-assisted (Claude) — 정회성 검토 완료
"""문의 데이터 조회·저장 (데이터 계층). 서비스는 SQL을 직접 쓰지 않고 이 클래스를 쓴다."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Customer, Inquiry, Store


class InquiryRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_stores(self) -> list[Store]:
        return list(self.session.scalars(select(Store).order_by(Store.id)))

    def get_store(self, store_id: int) -> Store | None:
        return self.session.get(Store, store_id)

    def find_or_create_customer(self, name: str, phone: str) -> Customer:
        """연락처가 같으면 같은 고객으로 본다. (UC-02와 같은 기준)"""
        customer = self.session.scalar(select(Customer).where(Customer.phone == phone))
        if customer is None:
            customer = Customer(name=name, phone=phone)
            self.session.add(customer)
        return customer

    def add(self, inquiry: Inquiry) -> Inquiry:
        self.session.add(inquiry)
        self.session.commit()
        return inquiry

    def get(self, inquiry_id: int) -> Inquiry | None:
        return self.session.get(Inquiry, inquiry_id)

    def list_by_store(self, store_id: int) -> list[Inquiry]:
        """미응답을 먼저, 그 안에서는 오래된 문의부터 보여준다."""
        stmt = (
            select(Inquiry)
            .where(Inquiry.store_id == store_id)
            .order_by((Inquiry.status != "미응답"), Inquiry.received_at)
        )
        return list(self.session.scalars(stmt))

    def save(self) -> None:
        self.session.commit()
