import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import MarketingContent


def save_marketing_content(
    session: Session,
    store_id: int,
    channel: str,
    target: str,
    keywords: list[str],
    text: str,
    violations: list[str],
) -> MarketingContent:
    content = MarketingContent(
        store_id=store_id,
        channel=channel,
        target=target,
        keywords=", ".join(keywords),
        text=text,
        check_result=json.dumps(
            {"violations": violations},
            ensure_ascii=False,
        ),
    )

    try:
        session.add(content)
        session.commit()
        session.refresh(content)
        return content
    except Exception:
        session.rollback()
        raise


def list_marketing_contents(
    session: Session,
    store_id: int,
    limit: int = 20,
) -> list[MarketingContent]:
    if limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")

    statement = (
        select(MarketingContent)
        .where(MarketingContent.store_id == store_id)
        .order_by(
            MarketingContent.saved_at.desc(),
            MarketingContent.id.desc(),
        )
        .limit(limit)
    )

    return list(session.scalars(statement).all())