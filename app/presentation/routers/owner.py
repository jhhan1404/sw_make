"""점주 화면 라우터."""

from datetime import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.presentation.templating import templates
from app.services.store.service import StoreService

router = APIRouter(prefix="/owner", tags=["owner"])

# ── 의존성 헬퍼 ───────────────────────────────────────────

SessionDep = Annotated[Session, Depends(get_session)]


def get_store_service(session: SessionDep) -> StoreService:
    return StoreService(session)


StoreSvcDep = Annotated[StoreService, Depends(get_store_service)]


# ── 대시보드 ──────────────────────────────────────────────

@router.get("", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    """점주 대시보드 (F-05). TODO(전지호): 오늘 예약·미응답 문의·최근 콘텐츠 조회."""
    return templates.TemplateResponse(
        request, "owner/dashboard.html", {"reservations": [], "unanswered": 0, "contents": []}
    )


# ── Pydantic 스키마 (F-01) ────────────────────────────────

class StoreUpdate(BaseModel):
    name: str | None = None
    category: str | None = None
    address: str | None = None
    open_time: time | None = None
    close_time: time | None = None
    closed_days: str | None = None
    phone: str | None = None
    capacity_per_hour: int | None = None


class MenuCreate(BaseModel):
    name: str
    price: int
    description: str = ""
    on_sale: bool = True


class MenuUpdate(BaseModel):
    name: str | None = None
    price: int | None = None
    description: str | None = None
    on_sale: bool | None = None


class FAQCreate(BaseModel):
    question: str
    answer: str


class FAQUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None


# ── 매장 정보 엔드포인트 (F-01-1) ─────────────────────────

@router.get("/stores/{store_id}")
def get_store(store_id: int, svc: StoreSvcDep):
    """매장 정보 조회."""
    try:
        store = svc.get_store(store_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {
        "id": store.id,
        "name": store.name,
        "category": store.category,
        "address": store.address,
        "open_time": str(store.open_time),
        "close_time": str(store.close_time),
        "closed_days": store.closed_days,
        "phone": store.phone,
        "capacity_per_hour": store.capacity_per_hour,
    }


@router.patch("/stores/{store_id}")
def update_store(store_id: int, body: StoreUpdate, svc: StoreSvcDep):
    """매장 정보 수정."""
    try:
        store = svc.update_store(store_id, **body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": store.id, "name": store.name}


# ── 메뉴 엔드포인트 (F-01-2) ──────────────────────────────

@router.get("/stores/{store_id}/menus")
def list_menus(store_id: int, svc: StoreSvcDep):
    """메뉴 목록 조회."""
    try:
        items = svc.list_menus(store_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return [
        {"id": m.id, "name": m.name, "price": m.price,
         "description": m.description, "on_sale": m.on_sale}
        for m in items
    ]


@router.post("/stores/{store_id}/menus", status_code=status.HTTP_201_CREATED)
def add_menu(store_id: int, body: MenuCreate, svc: StoreSvcDep):
    """메뉴 추가."""
    try:
        item = svc.add_menu(store_id, body.name, body.price, body.description, body.on_sale)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    return {"id": item.id, "name": item.name, "price": item.price}


@router.patch("/stores/{store_id}/menus/{menu_id}")
def update_menu(store_id: int, menu_id: int, body: MenuUpdate, svc: StoreSvcDep):
    """메뉴 수정."""
    try:
        item = svc.update_menu(store_id, menu_id, **body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": item.id, "name": item.name, "price": item.price, "on_sale": item.on_sale}


@router.delete("/stores/{store_id}/menus/{menu_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_menu(store_id: int, menu_id: int, svc: StoreSvcDep):
    """메뉴 삭제."""
    try:
        svc.delete_menu(store_id, menu_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ── FAQ 엔드포인트 (F-01-3) ───────────────────────────────

@router.get("/stores/{store_id}/faqs")
def list_faqs(store_id: int, svc: StoreSvcDep):
    """FAQ 목록 조회."""
    try:
        faqs = svc.list_faqs(store_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return [{"id": f.id, "question": f.question, "answer": f.answer} for f in faqs]


@router.post("/stores/{store_id}/faqs", status_code=status.HTTP_201_CREATED)
def add_faq(store_id: int, body: FAQCreate, svc: StoreSvcDep):
    """FAQ 추가."""
    try:
        faq = svc.add_faq(store_id, body.question, body.answer)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(e))
    return {"id": faq.id, "question": faq.question}


@router.patch("/stores/{store_id}/faqs/{faq_id}")
def update_faq(store_id: int, faq_id: int, body: FAQUpdate, svc: StoreSvcDep):
    """FAQ 수정."""
    try:
        faq = svc.update_faq(store_id, faq_id, **body.model_dump(exclude_none=True))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return {"id": faq.id, "question": faq.question, "answer": faq.answer}


@router.delete("/stores/{store_id}/faqs/{faq_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faq(store_id: int, faq_id: int, svc: StoreSvcDep):
    """FAQ 삭제."""
    try:
        svc.delete_faq(store_id, faq_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
