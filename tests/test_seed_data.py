"""가상 데이터 품질 검사 (11주차). 13주차 AI 검증 실험의 전제가 깨지지 않았는지 확인한다."""

from collections import Counter
from datetime import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.database import Base
from app.db.seed import DATA_DIR, SeedDataError, load_all, read_json
from app.models.models import FAQ, Customer, Inquiry, MenuItem, Store

stores = {s["key"]: s for s in read_json(DATA_DIR, "stores")}
faqs = read_json(DATA_DIR, "faqs")
inquiries = read_json(DATA_DIR, "inquiries")


def menu_prices(store_key: str) -> dict[str, int]:
    return {m["name"]: m["price"] for m in stores[store_key]["menu"]}


def test_inquiry_count_and_mix():
    """문의 30건, 유형별 10건씩 (README 11주차 기준)."""
    assert len(inquiries) == 30
    assert Counter(q["category"] for q in inquiries) == {"가격": 10, "영업시간": 10, "근거없음": 10}
    assert len({q["id"] for q in inquiries}) == 30


def test_faq_count_per_store():
    assert Counter(f["store"] for f in faqs) == {"cafe": 10, "salon": 10}


def test_price_answers_match_menu():
    """가격 문의의 정답이 stores.json 메뉴 가격과 같아야 한다."""
    for q in inquiries:
        if q["category"] == "가격":
            for name, price in q["expected"]["prices"].items():
                assert menu_prices(q["store"])[name] == price, q["id"]


def test_hour_answers_match_store():
    for q in inquiries:
        if q["category"] != "영업시간":
            continue
        store, exp = stores[q["store"]], q["expected"]
        for field in ("open_time", "close_time", "closed_days"):
            if field in exp:
                assert exp[field] == store[field], q["id"]


def test_out_of_scope_really_has_no_basis():
    """근거없음 문의의 핵심어가 메뉴·FAQ에 나오면 실험이 성립하지 않는다."""
    for q in inquiries:
        if q["category"] != "근거없음":
            continue
        store_faqs = [f["question"] + f["answer"] for f in faqs if f["store"] == q["store"]]
        basis = " ".join([*menu_prices(q["store"]), *store_faqs])
        assert q["oos_keyword"] not in basis, q["id"]


def test_store_hours_are_valid():
    for s in stores.values():
        assert time.fromisoformat(s["open_time"]) < time.fromisoformat(s["close_time"])
        assert all(m["price"] > 0 for m in s["menu"])


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_load_all_into_db(session):
    counts = load_all(session)
    session.commit()
    assert counts["inquiries"] == 30
    assert session.query(Store).count() == len(stores)
    assert session.query(MenuItem).count() == sum(len(s["menu"]) for s in stores.values())
    assert session.query(FAQ).count() == 20
    assert session.query(Inquiry).filter_by(status="미응답").count() == 30
    assert session.query(Customer).count() >= 30


def test_unknown_store_key_is_reported(session, tmp_path):
    (tmp_path / "faqs.json").write_text('[{"store": "bakery", "question": "q", "answer": "a"}]')
    with pytest.raises(SeedDataError):
        load_all(session, tmp_path)
