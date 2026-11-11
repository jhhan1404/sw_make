# AI-assisted (Claude) — 정회성 검토 완료
"""서버 시작 시 기본 매장(init_db)과 가상 데이터 적재(seed)가 서로 막지 않는지 확인한다 (PR #23)."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import database, seed
from app.models.models import Reservation, Store


@pytest.fixture
def temp_db(tmp_path, monkeypatch) -> sessionmaker:
    """모듈 전역 engine·SessionLocal을 임시 DB로 바꿔 실제 app.db를 건드리지 않는다."""
    engine = create_engine(f"sqlite:///{tmp_path / 't.db'}")
    session_factory = sessionmaker(bind=engine)
    for module in (database, seed):
        monkeypatch.setattr(module, "engine", engine)
        monkeypatch.setattr(module, "SessionLocal", session_factory)
    return session_factory


def store_names(session_factory: sessionmaker) -> list[str]:
    with session_factory() as session:
        return [s.name for s in session.query(Store).order_by(Store.id)]


def test_init_db_adds_default_store_to_empty_db(temp_db):
    database.init_db()
    database.init_db()  # 재시작해도 중복으로 넣지 않는다
    assert store_names(temp_db) == ["브루밍 카페"]


def test_seed_loads_on_fresh_db(temp_db):
    """빈 DB에서 seed가 기본 매장 때문에 '이미 데이터가 있습니다'로 멈추면 안 된다."""
    seed.seed()
    assert store_names(temp_db) == ["온기 카페", "결 헤어"]
    with temp_db() as session:
        assert session.query(Reservation).count() > 0


def test_init_db_keeps_seed_data(temp_db):
    """seed 후 서버를 시작해도 기본 매장을 덧붙이지 않는다."""
    seed.seed()
    database.init_db()
    assert "브루밍 카페" not in store_names(temp_db)
