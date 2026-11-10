"""매장·메뉴·FAQ 비즈니스 로직. (F-01)"""

from datetime import time

from sqlalchemy.orm import Session

from app.models.models import FAQ, MenuItem, Store
from app.repositories.store_repository import FAQRepository, MenuRepository, StoreRepository


class StoreService:
    """점주가 매장 정보·메뉴·FAQ를 관리하는 유스케이스 모음."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self._store_repo = StoreRepository(session)
        self._menu_repo = MenuRepository(session)
        self._faq_repo = FAQRepository(session)

    # ── 매장 정보 ─────────────────────────────────────────
    def get_store(self, store_id: int) -> Store:
        store = self._store_repo.get(store_id)
        if store is None:
            raise ValueError(f"매장을 찾을 수 없습니다. id={store_id}")
        return store

    def update_store(
        self,
        store_id: int,
        *,
        name: str | None = None,
        category: str | None = None,
        address: str | None = None,
        open_time: time | None = None,
        close_time: time | None = None,
        closed_days: str | None = None,
        phone: str | None = None,
        capacity_per_hour: int | None = None,
    ) -> Store:
        store = self.get_store(store_id)
        fields = {
            k: v
            for k, v in {
                "name": name,
                "category": category,
                "address": address,
                "open_time": open_time,
                "close_time": close_time,
                "closed_days": closed_days,
                "phone": phone,
                "capacity_per_hour": capacity_per_hour,
            }.items()
            if v is not None
        }
        return self._store_repo.update(store, **fields)

    # ── 메뉴 ──────────────────────────────────────────────
    def list_menus(self, store_id: int) -> list[MenuItem]:
        self.get_store(store_id)  # 매장 존재 확인
        return self._menu_repo.list_by_store(store_id)

    def add_menu(
        self,
        store_id: int,
        name: str,
        price: int,
        description: str = "",
        on_sale: bool = True,
    ) -> MenuItem:
        self.get_store(store_id)
        if price < 0:
            raise ValueError("가격은 0원 이상이어야 합니다.")
        return self._menu_repo.add(store_id, name, price, description, on_sale)

    def update_menu(self, store_id: int, menu_id: int, **fields) -> MenuItem:
        self.get_store(store_id)
        item = self._menu_repo.get(menu_id)
        if item is None or item.store_id != store_id:
            raise ValueError(f"메뉴를 찾을 수 없습니다. id={menu_id}")
        if "price" in fields and fields["price"] < 0:
            raise ValueError("가격은 0원 이상이어야 합니다.")
        return self._menu_repo.update(item, **fields)

    def delete_menu(self, store_id: int, menu_id: int) -> None:
        self.get_store(store_id)
        item = self._menu_repo.get(menu_id)
        if item is None or item.store_id != store_id:
            raise ValueError(f"메뉴를 찾을 수 없습니다. id={menu_id}")
        self._menu_repo.delete(item)

    # ── FAQ ───────────────────────────────────────────────
    def list_faqs(self, store_id: int) -> list[FAQ]:
        self.get_store(store_id)
        return self._faq_repo.list_by_store(store_id)

    def add_faq(self, store_id: int, question: str, answer: str) -> FAQ:
        self.get_store(store_id)
        return self._faq_repo.add(store_id, question, answer)

    def update_faq(self, store_id: int, faq_id: int, **fields) -> FAQ:
        self.get_store(store_id)
        faq = self._faq_repo.get(faq_id)
        if faq is None or faq.store_id != store_id:
            raise ValueError(f"FAQ를 찾을 수 없습니다. id={faq_id}")
        return self._faq_repo.update(faq, **fields)

    def delete_faq(self, store_id: int, faq_id: int) -> None:
        self.get_store(store_id)
        faq = self._faq_repo.get(faq_id)
        if faq is None or faq.store_id != store_id:
            raise ValueError(f"FAQ를 찾을 수 없습니다. id={faq_id}")
        self._faq_repo.delete(faq)
