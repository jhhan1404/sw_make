from datetime import time

from app.adapters.ai.mock_adapter import MockAIClient
from app.models.models import MenuItem, Store
from app.services.marketing.service import MarketingService


def create_store() -> Store:
    return Store(
        name="테스트 카페",
        category="카페",
        address="서울시",
        open_time=time(9, 0),
        close_time=time(18, 0),
        closed_days="",
        phone="010-0000-0000",
        capacity_per_hour=10,
    )


def create_menu() -> MenuItem:
    return MenuItem(
        name="아메리카노",
        price=4500,
        on_sale=True,
    )


def test_marketing_service_checks_price_and_time():
    response = "아메리카노는 5000원입니다. 영업시간은 09:00부터 21:00까지입니다."

    service = MarketingService(MockAIClient(fixed_response=response))

    result = service.generate(
        channel="sms",
        target="일반 고객",
        keywords=["아메리카노"],
        store=create_store(),
        menus=[create_menu()],
    )

    assert result.text == response
    assert any("가격" in violation for violation in result.violations)
    assert any("시각" in violation for violation in result.violations)


def test_marketing_service_accepts_registered_price_and_time():
    response = "아메리카노는 4500원입니다. 영업시간은 09:00부터 18:00까지입니다."

    service = MarketingService(MockAIClient(fixed_response=response))

    result = service.generate(
        channel="sms",
        target="일반 고객",
        keywords=["아메리카노"],
        store=create_store(),
        menus=[create_menu()],
    )

    assert result.text == response
    assert result.violations == []


def test_marketing_service_detects_unregistered_menu():
    response = "바닐라라떼는 5000원입니다."

    service = MarketingService(MockAIClient(fixed_response=response))

    result = service.generate(
        channel="sms",
        target="일반 고객",
        keywords=["신메뉴"],
        store=create_store(),
        menus=[create_menu()],
    )

    assert any("Unregistered menu name" in violation for violation in result.violations)
