"""고객 화면 라우터."""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.presentation.templating import templates

router = APIRouter(tags=["customer"])


@router.get("/", response_class=HTMLResponse)
def home(request: Request) -> HTMLResponse:
    """고객 첫 화면. 예약(F-02)·문의(F-03) 화면으로 안내한다."""
    return templates.TemplateResponse(request, "customer/index.html", {})
