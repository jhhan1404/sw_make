"""매장·메뉴·FAQ 데이터 접근 레이어. (F-01)"""

from sqlalchemy.orm import Session

from app.models.models import FAQ, MenuItem, Store


class StoreRepository:
    """Store 단일 레코드 조회·수정."""

    def __init__(self, session: Session) -> None:
        self.session = session

    # ── 매장 ──────────────────────────────────────────────
    def get(self, store_id: int) -> Store | None:
        """store_id 로 매장 하나를 반환. 없으면 None."""
        return self.session.get(Store, store_id)

    def update(self, store: Store, **fields) -> Store:
        """허용된 필드만 덮어쓴 뒤 커밋."""
        allowed = {
            "name", "category", "address",
            "open_time", "close_time", "closed_days",
            "phone", "capacity_per_hour",
        }
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"수정 불가 필드: {key}")
            setattr(store, key, value)
        self.session.commit()
        self.session.refresh(store)
        return store


class MenuRepository:
    """MenuItem CRUD."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_store(self, store_id: int) -> list[MenuItem]:
        return (
            self.session.query(MenuItem)
            .filter(MenuItem.store_id == store_id)
            .order_by(MenuItem.id)
            .all()
        )

    def get(self, menu_id: int) -> MenuItem | None:
        return self.session.get(MenuItem, menu_id)

    def add(self, store_id: int, name: str, price: int,
            description: str = "", on_sale: bool = True) -> MenuItem:
        item = MenuItem(
            store_id=store_id,
            name=name,
            price=price,
            description=description,
            on_sale=on_sale,
        )
        self.session.add(item)
        self.session.commit()
        self.session.refresh(item)
        return item

    def update(self, item: MenuItem, **fields) -> MenuItem:
        allowed = {"name", "price", "description", "on_sale"}
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"수정 불가 필드: {key}")
            setattr(item, key, value)
        self.session.commit()
        self.session.refresh(item)
        return item

    def delete(self, item: MenuItem) -> None:
        self.session.delete(item)
        self.session.commit()


class FAQRepository:
    """FAQ CRUD."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_store(self, store_id: int) -> list[FAQ]:
        return (
            self.session.query(FAQ)
            .filter(FAQ.store_id == store_id)
            .order_by(FAQ.id)
            .all()
        )

    def get(self, faq_id: int) -> FAQ | None:
        return self.session.get(FAQ, faq_id)

    def add(self, store_id: int, question: str, answer: str) -> FAQ:
        faq = FAQ(store_id=store_id, question=question, answer=answer)
        self.session.add(faq)
        self.session.commit()
        self.session.refresh(faq)
        return faq

    def update(self, faq: FAQ, **fields) -> FAQ:
        allowed = {"question", "answer"}
        for key, value in fields.items():
            if key not in allowed:
                raise ValueError(f"수정 불가 필드: {key}")
            setattr(faq, key, value)
        self.session.commit()
        self.session.refresh(faq)
        return faq

    def delete(self, faq: FAQ) -> None:
        self.session.delete(faq)
        self.session.commit()
