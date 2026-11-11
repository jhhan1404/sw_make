"""SQLite 연결과 세션을 관리한다."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """모든 모델의 부모 클래스."""


def init_db() -> None:
    """모델 정의를 바탕으로 테이블을 만들고, 기본 매장 데이터를 넣는다."""
    from datetime import time

    from app.models import models  # noqa: F401  (모델 등록용 import)

    Base.metadata.create_all(bind=engine)

    # 배포 직후 store_id=1 이 없으면 매장·메뉴·FAQ 관리 화면이 동작하지 않는다.
    # 아직 없을 때만 기본값으로 만든다 (재시작 때 덮어쓰지 않음).
    with SessionLocal() as session:
        if session.get(models.Store, 1) is None:
            store = models.Store(
                id=1,
                name="브루밍 카페",
                category="카페",
                address="서울시 마포구 연남동 123-45",
                open_time=time(9, 0),
                close_time=time(21, 0),
                closed_days="월",
                phone="02-1234-5678",
                capacity_per_hour=20,
            )
            session.add(store)
            session.flush()  # store.id 확정

            # 메뉴 3개
            session.add_all([
                models.MenuItem(
                    store_id=1,
                    name="아메리카노",
                    price=4500,
                    description="깔끔하고 진한 에스프레소 베이스 아메리카노",
                    on_sale=True,
                ),
                models.MenuItem(
                    store_id=1,
                    name="카페라떼",
                    price=5500,
                    description="부드러운 우유 거품이 올라간 클래식 라떼",
                    on_sale=True,
                ),
                models.MenuItem(
                    store_id=1,
                    name="딸기 스무디",
                    price=6500,
                    description="신선한 딸기로 만든 달콤한 스무디",
                    on_sale=True,
                ),
            ])

            # FAQ 3개
            session.add_all([
                models.FAQ(
                    store_id=1,
                    question="예약은 어떻게 하나요?",
                    answer=(
                        "홈페이지 상단 '예약하기' 메뉴를 통해 "
                        "날짜와 인원을 선택하여 예약하실 수 있습니다."
                    ),
                ),
                models.FAQ(
                    store_id=1,
                    question="주차 가능한가요?",
                    answer=(
                        "매장 근처 공영주차장을 이용하실 수 있습니다. "
                        "도보 3분 거리에 위치해 있습니다."
                    ),
                ),
                models.FAQ(
                    store_id=1,
                    question="단체 예약도 가능한가요?",
                    answer=(
                        "10인 이상 단체 예약은 전화(02-1234-5678)로 "
                        "문의해 주시면 안내해 드립니다."
                    ),
                ),
            ])

            session.commit()


def get_session() -> Iterator[Session]:
    """FastAPI 의존성 주입용 세션."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
