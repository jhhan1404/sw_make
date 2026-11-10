from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.models.models import Store
from app.repositories.marketing_repository import (
    list_marketing_contents,
    save_marketing_content,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db_session:
        yield db_session

    Base.metadata.drop_all(engine)
    engine.dispose()


def create_store(session: Session) -> Store:
    store = Store(
        name="테스트 매장",
        category="카페",
        address="서울시",
        open_time=time(9, 0),
        close_time=time(18, 0),
        closed_days="",
        phone="010-0000-0000",
        capacity_per_hour=10,
    )

    session.add(store)
    session.commit()
    session.refresh(store)
    return store


def test_save_and_list_marketing_content(session: Session):
    store = create_store(session)

    saved = save_marketing_content(
        session=session,
        store_id=store.id,
        channel="instagram",
        target="20대 고객",
        keywords=["커피", "카페"],
        text="새로운 커피를 소개합니다.",
        violations=[],
    )

    assert saved.id is not None
    assert saved.store_id == store.id
    assert saved.channel == "instagram"
    assert saved.keywords == "커피, 카페"

    contents = list_marketing_contents(
        session=session,
        store_id=store.id,
    )

    assert len(contents) == 1
    assert contents[0].text == "새로운 커피를 소개합니다."


def test_list_marketing_contents_limit(session: Session):
    with pytest.raises(ValueError):
        list_marketing_contents(
            session=session,
            store_id=1,
            limit=0,
        )
