"""가상 데이터 적재 스크립트. `app/db/seed_data/*.json`을 읽어 DB에 넣는다.

실행:
    python -m app.db.seed           # 데이터가 없을 때만 적재
    python -m app.db.seed --reset   # 테이블을 비우고 다시 적재

파일 형식은 `app/db/seed_data/README.md` 참고. 없는 파일은 건너뛴다.
"""

import json
import sys
from datetime import datetime, time
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.db.database import Base, SessionLocal, engine, init_db
from app.models.models import (
    FAQ,
    Customer,
    Inquiry,
    MarketingContent,
    MenuItem,
    Reservation,
    Store,
)

DATA_DIR = Path(__file__).parent / "seed_data"


class SeedDataError(Exception):
    """가상 데이터 파일의 형식이나 참조가 잘못되었을 때."""


def read_json(data_dir: Path, name: str) -> list[dict[str, Any]]:
    """`name.json`을 읽는다. 파일이 없으면 빈 리스트."""
    path = data_dir / f"{name}.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


class SeedLoader:
    """JSON 데이터를 모델 객체로 바꿔 세션에 추가한다."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.stores: dict[str, Store] = {}
        self.customers: dict[str, Customer] = {}

    def store(self, key: str) -> Store:
        if key not in self.stores:
            raise SeedDataError(f"stores.json에 없는 매장 키: {key}")
        return self.stores[key]

    def customer(self, info: dict[str, str]) -> Customer:
        """연락처 기준으로 고객을 재사용한다. 처음 보는 연락처면 새로 만든다."""
        phone = info["phone"]
        if phone not in self.customers:
            self.customers[phone] = Customer(name=info["name"], phone=phone)
            self.session.add(self.customers[phone])
        return self.customers[phone]

    def load_stores(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            store = Store(
                name=row["name"],
                category=row["category"],
                address=row["address"],
                open_time=time.fromisoformat(row["open_time"]),
                close_time=time.fromisoformat(row["close_time"]),
                closed_days=row.get("closed_days", ""),
                phone=row["phone"],
                capacity_per_hour=row.get("capacity_per_hour", 10),
            )
            store.menu_items = [MenuItem(**item) for item in row.get("menu", [])]
            self.session.add(store)
            self.stores[row["key"]] = store

    def load_customers(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.customer(row)

    def load_faqs(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.session.add(
                FAQ(store=self.store(row["store"]), question=row["question"], answer=row["answer"])
            )

    def load_inquiries(self, rows: list[dict[str, Any]]) -> None:
        """검증용 필드(category, expected 등)는 DB에 넣지 않고 JSON에만 남긴다."""
        for row in rows:
            self.session.add(
                Inquiry(
                    store=self.store(row["store"]),
                    customer=self.customer(row["customer"]),
                    content=row["content"],
                    received_at=datetime.fromisoformat(row["received_at"]),
                    status=row.get("status", "미응답"),
                )
            )

    def load_reservations(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.session.add(
                Reservation(
                    store=self.store(row["store"]),
                    customer=self.customer(row["customer"]),
                    reserved_at=datetime.fromisoformat(row["reserved_at"]),
                    party_size=row["party_size"],
                    request=row.get("request", ""),
                    status=row.get("status", "요청"),
                )
            )

    def load_contents(self, rows: list[dict[str, Any]]) -> None:
        for row in rows:
            self.session.add(
                MarketingContent(
                    store=self.store(row["store"]),
                    channel=row["channel"],
                    target=row["target"],
                    keywords=", ".join(row.get("keywords", [])),
                    text=row["text"],
                )
            )


def load_all(session: Session, data_dir: Path = DATA_DIR) -> dict[str, int]:
    """모든 JSON을 순서대로 적재하고 파일별 건수를 돌려준다. 커밋은 호출한 쪽에서 한다."""
    loader = SeedLoader(session)
    steps = [
        ("stores", loader.load_stores),
        ("customers", loader.load_customers),
        ("faqs", loader.load_faqs),
        ("inquiries", loader.load_inquiries),
        ("reservations", loader.load_reservations),
        ("contents", loader.load_contents),
    ]
    counts = {}
    for name, load in steps:
        rows = read_json(data_dir, name)
        load(rows)
        counts[name] = len(rows)
    return counts


def seed(reset: bool = False) -> None:
    init_db()
    if reset:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        if not reset and session.query(Store).count() > 0:
            print("이미 데이터가 있습니다. 다시 넣으려면 --reset 을 붙이세요.")
            return
        counts = load_all(session)
        session.commit()
    print("가상 데이터 적재 완료:", ", ".join(f"{k} {v}건" for k, v in counts.items()))


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
