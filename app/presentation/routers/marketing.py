from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.adapters.ai import get_ai_client
from app.db.database import get_session
from app.models.models import MenuItem, Store
from app.services.marketing.service import MarketingService

router = APIRouter(prefix="/marketing", tags=["marketing"])

SessionDep = Annotated[Session, Depends(get_session)]


class MarketingGenerateRequest(BaseModel):
    store_id: int
    channel: str
    target: str
    keywords: list[str] = Field(default_factory=list)


@router.post("/generate")
def generate_marketing_content(
    body: MarketingGenerateRequest,
    session: SessionDep,
):
    store = session.get(Store, body.store_id)

    if store is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="매장을 찾을 수 없습니다.",
        )

    menus = session.query(MenuItem).filter(
        MenuItem.store_id == body.store_id
    ).all()

    service = MarketingService(get_ai_client())

    result = service.generate(
        channel=body.channel,
        target=body.target,
        keywords=body.keywords,
        store=store,
        menus=menus,
    )

    if result.error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=result.error,
        )

    try:
        saved = service.save(
            session=session,
            store_id=body.store_id,
            channel=body.channel,
            target=body.target,
            keywords=body.keywords,
            result=result,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return {
        "id": saved.id,
        "text": result.text,
        "violations": result.violations,
        "saved_at": saved.saved_at,
    }


@router.get("/stores/{store_id}/contents")
def list_marketing_contents(
    store_id: int,
    session: SessionDep,
    limit: int = 20,
):
    if session.get(Store, store_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="매장을 찾을 수 없습니다.",
        )

    service = MarketingService(get_ai_client())

    contents = service.list_saved(
        session=session,
        store_id=store_id,
        limit=limit,
    )

    return [
        {
            "id": item.id,
            "channel": item.channel,
            "target": item.target,
            "keywords": item.keywords,
            "text": item.text,
            "check_result": item.check_result,
            "saved_at": item.saved_at,
        }
        for item in contents
    ]