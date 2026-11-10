"""F-01 매장·메뉴·FAQ 관리 API 테스트."""

import pytest
from fastapi.testclient import TestClient
from datetime import time

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_session
from app.main import app
from app.models import models  # noqa: F401 — 모든 모델 테이블 등록
from app.models.models import Store


# ── 테스트용 인메모리 DB 설정 ──────────────────────────────

TEST_ENGINE = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=TEST_ENGINE, autoflush=False, autocommit=False)


def override_get_session():
    session = TestSession()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(TEST_ENGINE)
    app.dependency_overrides[get_session] = override_get_session
    yield
    Base.metadata.drop_all(TEST_ENGINE)
    app.dependency_overrides.clear()


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def store_id(client):
    """테스트용 매장을 DB에 직접 삽입 후 id 반환."""
    session = TestSession()
    store = Store(
        name="테스트 카페",
        category="카페",
        address="서울시 중구 1-1",
        open_time=time(9, 0),
        close_time=time(22, 0),
        closed_days="",
        phone="010-0000-0000",
        capacity_per_hour=5,
    )
    session.add(store)
    session.commit()
    sid = store.id
    session.close()
    return sid


# ── 매장 조회·수정 ────────────────────────────────────────

class TestStoreInfo:
    def test_get_store(self, client, store_id):
        res = client.get(f"/owner/stores/{store_id}")
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "테스트 카페"
        assert data["category"] == "카페"

    def test_get_store_not_found(self, client):
        res = client.get("/owner/stores/9999")
        assert res.status_code == 404

    def test_update_store(self, client, store_id):
        res = client.patch(
            f"/owner/stores/{store_id}",
            json={"name": "수정된 카페", "phone": "010-1234-5678"},
        )
        assert res.status_code == 200
        assert res.json()["name"] == "수정된 카페"


# ── 메뉴 CRUD ─────────────────────────────────────────────

class TestMenu:
    def test_add_and_list(self, client, store_id):
        # 추가
        res = client.post(
            f"/owner/stores/{store_id}/menus",
            json={"name": "아메리카노", "price": 4000},
        )
        assert res.status_code == 201
        menu_id = res.json()["id"]

        # 목록 조회
        res = client.get(f"/owner/stores/{store_id}/menus")
        assert res.status_code == 200
        names = [m["name"] for m in res.json()]
        assert "아메리카노" in names

    def test_update_menu(self, client, store_id):
        # 추가 후 수정
        res = client.post(
            f"/owner/stores/{store_id}/menus",
            json={"name": "라떼", "price": 4500},
        )
        menu_id = res.json()["id"]
        res = client.patch(
            f"/owner/stores/{store_id}/menus/{menu_id}",
            json={"price": 5000, "on_sale": False},
        )
        assert res.status_code == 200
        assert res.json()["price"] == 5000
        assert res.json()["on_sale"] is False

    def test_delete_menu(self, client, store_id):
        res = client.post(
            f"/owner/stores/{store_id}/menus",
            json={"name": "삭제용 음료", "price": 1000},
        )
        menu_id = res.json()["id"]
        res = client.delete(f"/owner/stores/{store_id}/menus/{menu_id}")
        assert res.status_code == 204
        # 삭제 후 조회하면 목록에 없어야 함
        items = client.get(f"/owner/stores/{store_id}/menus").json()
        assert all(m["id"] != menu_id for m in items)

    def test_negative_price_rejected(self, client, store_id):
        res = client.post(
            f"/owner/stores/{store_id}/menus",
            json={"name": "잘못된 메뉴", "price": -1},
        )
        assert res.status_code == 422


# ── FAQ CRUD ──────────────────────────────────────────────

class TestFAQ:
    def test_add_and_list(self, client, store_id):
        res = client.post(
            f"/owner/stores/{store_id}/faqs",
            json={"question": "주차 가능한가요?", "answer": "건물 지하 주차장 이용 가능합니다."},
        )
        assert res.status_code == 201
        faq_id = res.json()["id"]

        faqs = client.get(f"/owner/stores/{store_id}/faqs").json()
        assert any(f["id"] == faq_id for f in faqs)

    def test_update_faq(self, client, store_id):
        res = client.post(
            f"/owner/stores/{store_id}/faqs",
            json={"question": "와이파이 되나요?", "answer": "됩니다."},
        )
        faq_id = res.json()["id"]
        res = client.patch(
            f"/owner/stores/{store_id}/faqs/{faq_id}",
            json={"answer": "무료 와이파이 제공합니다."},
        )
        assert res.status_code == 200
        assert "무료" in res.json()["answer"]

    def test_delete_faq(self, client, store_id):
        res = client.post(
            f"/owner/stores/{store_id}/faqs",
            json={"question": "삭제 테스트", "answer": "삭제됩니다."},
        )
        faq_id = res.json()["id"]
        res = client.delete(f"/owner/stores/{store_id}/faqs/{faq_id}")
        assert res.status_code == 204

    def test_faq_wrong_store(self, client, store_id):
        """다른 매장의 FAQ는 삭제 불가."""
        res = client.post(
            f"/owner/stores/{store_id}/faqs",
            json={"question": "Q", "answer": "A"},
        )
        faq_id = res.json()["id"]
        # 존재하지 않는 매장으로 삭제 시도
        res = client.delete(f"/owner/stores/9999/faqs/{faq_id}")
        assert res.status_code == 404
