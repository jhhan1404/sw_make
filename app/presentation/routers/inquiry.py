# AI-assisted (Claude) — 정회성 검토 완료
"""문의 화면 라우터 (F-03). 고객: 문의 등록 / 점주: 문의함, AI 초안 생성.

라우터는 입력을 받아 서비스에 넘기고 화면만 고른다. 로직과 SQL은 쓰지 않는다. (CLAUDE.md 3절)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.adapters.ai import AIClient, AIClientError, get_ai_client
from app.adapters.ai.mock_adapter import MockAIClient
from app.db.database import get_session
from app.presentation.templating import templates
from app.repositories.inquiry_repository import InquiryRepository
from app.services.inquiry.schemas import MAX_CONTENT_LENGTH, InquiryCreate, korean_errors
from app.services.inquiry.service import (
    InquiryNotFoundError,
    InquiryService,
    StoreNotFoundError,
)

router = APIRouter(tags=["inquiry"])


class _MisconfiguredAI(MockAIClient):
    """설정 오류(.env)를 F-03-5의 'AI 실패' 흐름으로 보여주기 위한 대체 클라이언트."""

    def __init__(self, reason: str) -> None:
        super().__init__(fail=True)
        self.reason = reason

    def generate(self, prompt: str, system: str | None = None) -> str:
        raise AIClientError(self.reason)


def get_ai() -> AIClient:
    try:
        return get_ai_client()
    except AIClientError as e:
        return _MisconfiguredAI(str(e))


def get_service(
    session: Annotated[Session, Depends(get_session)],
    ai: Annotated[AIClient, Depends(get_ai)],
) -> InquiryService:
    return InquiryService(ai, InquiryRepository(session))


ServiceDep = Annotated[InquiryService, Depends(get_service)]


# ---------- 고객 화면 (F-03-1) ----------


@router.get("/inquiries/new", response_class=HTMLResponse)
def inquiry_form(request: Request, service: ServiceDep) -> HTMLResponse:
    return _render_form(request, service, form={}, errors=[])


@router.post("/inquiries", response_class=HTMLResponse)
def submit_inquiry(
    request: Request,
    store_id: Annotated[int, Form()],
    service: ServiceDep,
    name: Annotated[str, Form()] = "",
    phone: Annotated[str, Form()] = "",
    content: Annotated[str, Form()] = "",
) -> HTMLResponse:
    form = {"store_id": store_id, "name": name, "phone": phone, "content": content}
    try:
        inquiry = service.register(InquiryCreate(**form))
    except ValidationError as e:
        return _render_form(request, service, form, korean_errors(e), status_code=400)
    except StoreNotFoundError:
        return _render_form(request, service, form, ["매장을 다시 선택해 주세요."], 400)
    return templates.TemplateResponse(request, "customer/inquiry_done.html", {"inquiry": inquiry})


def _render_form(
    request: Request,
    service: InquiryService,
    form: dict,
    errors: list[str],
    status_code: int = 200,
) -> HTMLResponse:
    context = {
        "stores": service.repo.list_stores(),
        "form": form,
        "errors": errors,
        "max_length": MAX_CONTENT_LENGTH,
    }
    return templates.TemplateResponse(
        request, "customer/inquiry_form.html", context, status_code=status_code
    )


# ---------- 점주 화면 (F-03-2, F-03-3) ----------


@router.get("/owner/inquiries", response_class=HTMLResponse)
def inquiry_list(
    request: Request,
    service: ServiceDep,
    store_id: int | None = None,
) -> HTMLResponse:
    stores = service.repo.list_stores()
    selected = next((s for s in stores if s.id == store_id), stores[0] if stores else None)
    inquiries = service.repo.list_by_store(selected.id) if selected else []
    context = {"stores": stores, "selected": selected, "inquiries": inquiries}
    return templates.TemplateResponse(request, "owner/inquiry_list.html", context)


@router.get("/owner/inquiries/{inquiry_id}", response_class=HTMLResponse)
def inquiry_detail(
    request: Request,
    inquiry_id: int,
    service: ServiceDep,
    ai_error: str | None = None,
) -> HTMLResponse:
    try:
        inquiry = service.get(inquiry_id)
    except InquiryNotFoundError as e:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다") from e
    context = {
        "inquiry": inquiry,
        "mismatches": service.mismatches_of(inquiry),
        "ai_error": ai_error,
    }
    return templates.TemplateResponse(request, "owner/inquiry_detail.html", context)


@router.post("/owner/inquiries/{inquiry_id}/draft")
def create_draft(inquiry_id: int, service: ServiceDep) -> RedirectResponse:
    """초안 생성 후 상세 화면으로 돌아간다. 새로고침해도 다시 생성되지 않게 리다이렉트한다."""
    try:
        result = service.generate_draft(inquiry_id)
    except InquiryNotFoundError as e:
        raise HTTPException(status_code=404, detail="문의를 찾을 수 없습니다") from e
    url = f"/owner/inquiries/{inquiry_id}"
    if result.error:
        url += "?ai_error=1"
    return RedirectResponse(url, status_code=303)
