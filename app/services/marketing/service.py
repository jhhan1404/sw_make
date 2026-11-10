import re
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.adapters.ai import AIClient, AIClientError
from app.models.models import MarketingContent, MenuItem, Store
from app.repositories.marketing_repository import (
    list_marketing_contents,
    save_marketing_content,
)
from app.services.inquiry.fact_checker import FactChecker
from app.services.marketing.strategies import get_strategy


@dataclass
class ContentResult:
    text: str | None
    violations: list[str]
    error: str | None = None


MENU_PRICE_PATTERN = re.compile(
    r"([가-힣A-Za-z0-9][가-힣A-Za-z0-9\s·()_-]{0,30}?)"
    r"(?:은|는|이|가)\s*(?:가격은\s*)?[\d,]+\s*원"
)


class MarketingService:
    def __init__(self, ai_client: AIClient) -> None:
        self.ai = ai_client

    def generate(
        self,
        channel: str,
        target: str,
        keywords: list[str],
        store: Store | None = None,
        menus: list[MenuItem] | None = None,
    ) -> ContentResult:
        strategy = get_strategy(channel)

        try:
            text = self.ai.generate(strategy.build_prompt(target, keywords))
        except AIClientError as e:
            return ContentResult(
                text=None,
                violations=[],
                error=f"문구 생성 실패: {e}",
            )

        violations = strategy.check(text)

        # 매장 및 메뉴 정보가 전달되면 가격과 영업시간 검증
        if store is not None and menus is not None:
            menu_prices = {menu.name: menu.price for menu in menus if menu.on_sale}

            fact_checker = FactChecker(
                menu_prices=menu_prices,
                open_time=store.open_time,
                close_time=store.close_time,
            )

            mismatches = fact_checker.check(text)

            for mismatch in mismatches:
                violations.append(f"{mismatch.kind}: {mismatch.found} - {mismatch.message}")
            registered_names = {menu.name.strip() for menu in menus if menu.on_sale}

            candidates = MENU_PRICE_PATTERN.findall(text)

            for candidate in candidates:
                menu_name = candidate.strip()

                if menu_name not in registered_names:
                    violations.append(f"Unregistered menu name: {menu_name}")

        return ContentResult(
            text=text,
            violations=violations,
        )

    def save(
        self,
        session: Session,
        store_id: int,
        channel: str,
        target: str,
        keywords: list[str],
        result: ContentResult,
    ) -> MarketingContent:
        if result.text is None:
            raise ValueError("생성에 실패한 문구는 저장할 수 없습니다.")

        return save_marketing_content(
            session=session,
            store_id=store_id,
            channel=channel,
            target=target,
            keywords=keywords,
            text=result.text,
            violations=result.violations,
        )

    def list_saved(
        self,
        session: Session,
        store_id: int,
        limit: int = 20,
    ) -> list[MarketingContent]:
        return list_marketing_contents(
            session=session,
            store_id=store_id,
            limit=limit,
        )
