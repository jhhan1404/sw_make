# AI-assisted (Claude) — 정회성 검토 완료
"""예약 화면 라우터 (F-02). 고객: 신청·조회·변경·취소 / 점주: 예약 처리, 고객 이력.

라우터는 입력을 받아 서비스에 넘기고 화면만 고른다. 로직과 SQL은 쓰지 않는다. (CLAUDE.md 3절)
연락처는 개인정보라 URL에 남지 않도록 조회·변경·취소는 POST로 받는다.
"""

from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.database import get_session
from app.presentation.templating import templates
from app.services.reservation.schemas import (
    MAX_PARTY_SIZE,
    ReservationCreate,
    ReservationSlot,
    korean_errors,
)
from app.services.reservation.service import (
    OWNER_ACTIONS,
    ReservationNotFoundError,
    ReservationRejectedError,
    ReservationService,
    StoreNotFoundError,
)
from app.services.reservation.states import InvalidTransitionError, ReservationStatus, state_of

router = APIRouter(tags=["reservation"])

ACTION_LABELS = {
    "confirm": "확정",
    "visit": "방문완료",
    "no_show": "노쇼",
    "cancel": "취소",
    "change": "변경",
}
STATUS_BADGES = {
    "요청": "text-bg-warning",
    "확정": "text-bg-primary",
    "방문완료": "text-bg-success",
    "취소": "text-bg-secondary",
    "노쇼": "text-bg-danger",
}


def get_service(session: Annotated[Session, Depends(get_session)]) -> ReservationService:
    return ReservationService(session)


ServiceDep = Annotated[ReservationService, Depends(get_service)]
FormStr = Annotated[str, Form()]


def _render(request: Request, name: str, context: dict, status_code: int = 200) -> HTMLResponse:
    base = {"badges": STATUS_BADGES, "labels": ACTION_LABELS, "max_party": MAX_PARTY_SIZE}
    return templates.TemplateResponse(request, name, base | context, status_code=status_code)


def _customer_actions(status: str) -> list[str]:
    """고객 화면에는 변경·취소 버튼만 보여준다. (F-02-3)"""
    return [a for a in state_of(status).allowed_actions() if a in ("change", "cancel")]


# ---------- 고객: 예약 신청 (F-02-1, F-02-2) ----------


@router.get("/reservations/new", response_class=HTMLResponse)
def reservation_form(request: Request, service: ServiceDep) -> HTMLResponse:
    return _render_form(request, service, form={}, errors=[])


@router.post("/reservations", response_class=HTMLResponse)
def submit_reservation(
    request: Request,
    service: ServiceDep,
    store_id: Annotated[int, Form()],
    name: FormStr = "",
    phone: FormStr = "",
    visit_date: FormStr = "",
    visit_time: FormStr = "",
    party_size: FormStr = "",
    request_text: Annotated[str, Form(alias="request")] = "",
) -> HTMLResponse:
    form = {
        "store_id": store_id,
        "name": name,
        "phone": phone,
        "visit_date": visit_date,
        "visit_time": visit_time,
        "party_size": party_size,
        "request": request_text,
    }
    try:
        reservation = service.create(ReservationCreate(**form))
    except ValidationError as e:
        return _render_form(request, service, form, korean_errors(e), 400)
    except StoreNotFoundError:
        return _render_form(request, service, form, ["매장을 다시 선택해 주세요."], 400)
    except ReservationRejectedError as e:
        return _render_form(request, service, form, [str(e)], 400)
    return _render(request, "customer/reservation_done.html", {"reservation": reservation})


def _render_form(
    request: Request,
    service: ReservationService,
    form: dict,
    errors: list[str],
    status_code: int = 200,
) -> HTMLResponse:
    context = {"stores": service.repo.list_stores(), "form": form, "errors": errors}
    return _render(request, "customer/reservation_form.html", context, status_code)


# ---------- 고객: 조회·변경·취소 (F-02-3) ----------


@router.get("/reservations/lookup", response_class=HTMLResponse)
def lookup_form(request: Request) -> HTMLResponse:
    return _render(request, "customer/reservation_lookup.html", {"phone": None})


@router.post("/reservations/lookup", response_class=HTMLResponse)
def lookup(request: Request, service: ServiceDep, phone: FormStr = "") -> HTMLResponse:
    return _render_lookup(request, service, phone.strip())


def _render_lookup(
    request: Request,
    service: ReservationService,
    phone: str,
    message: str | None = None,
    error: str | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    reservations = service.find_by_phone(phone) if phone else []
    context = {
        "phone": phone,
        "reservations": reservations,
        "actions": {r.id: _customer_actions(r.status) for r in reservations},
        "message": message,
        "error": error,
    }
    return _render(request, "customer/reservation_lookup.html", context, status_code)


@router.post("/reservations/{reservation_id}/edit", response_class=HTMLResponse)
def edit_form(
    request: Request, reservation_id: int, service: ServiceDep, phone: FormStr = ""
) -> HTMLResponse:
    try:
        reservation = service.get_owned(reservation_id, phone)
    except ReservationNotFoundError as e:
        return _render_lookup(request, service, phone, error=str(e), status_code=404)
    form = {
        "visit_date": f"{reservation.reserved_at:%Y-%m-%d}",
        "visit_time": f"{reservation.reserved_at:%H:%M}",
        "party_size": reservation.party_size,
    }
    return _render_edit(request, reservation, phone, form, [])


@router.post("/reservations/{reservation_id}/change", response_class=HTMLResponse)
def change_reservation(
    request: Request,
    reservation_id: int,
    service: ServiceDep,
    phone: FormStr = "",
    visit_date: FormStr = "",
    visit_time: FormStr = "",
    party_size: FormStr = "",
) -> HTMLResponse:
    form = {"visit_date": visit_date, "visit_time": visit_time, "party_size": party_size}
    try:
        reservation = service.get_owned(reservation_id, phone)
        service.change(reservation_id, phone, ReservationSlot(**form))
    except ReservationNotFoundError as e:
        return _render_lookup(request, service, phone, error=str(e), status_code=404)
    except ValidationError as e:
        return _render_edit(request, reservation, phone, form, korean_errors(e))
    except (ReservationRejectedError, InvalidTransitionError) as e:
        return _render_edit(request, reservation, phone, form, [str(e)])
    message = "예약을 변경했습니다. 매장에서 다시 확정하면 '확정'으로 바뀝니다."
    return _render_lookup(request, service, phone, message=message)


def _render_edit(
    request: Request, reservation: object, phone: str, form: dict, errors: list[str]
) -> HTMLResponse:
    context = {"reservation": reservation, "phone": phone, "form": form, "errors": errors}
    status_code = 400 if errors else 200
    return _render(request, "customer/reservation_edit.html", context, status_code)


@router.post("/reservations/{reservation_id}/cancel", response_class=HTMLResponse)
def cancel_reservation(
    request: Request, reservation_id: int, service: ServiceDep, phone: FormStr = ""
) -> HTMLResponse:
    try:
        service.cancel_by_customer(reservation_id, phone)
    except ReservationNotFoundError as e:
        return _render_lookup(request, service, phone, error=str(e), status_code=404)
    except InvalidTransitionError as e:
        return _render_lookup(request, service, phone, error=str(e), status_code=400)
    return _render_lookup(request, service, phone, message="예약을 취소했습니다.")


# ---------- 점주: 예약 처리 (F-02-4, F-02-5) ----------


@router.get("/owner/reservations", response_class=HTMLResponse)
def owner_reservation_list(
    request: Request,
    service: ServiceDep,
    store_id: int | None = None,
    status: str | None = None,
) -> HTMLResponse:
    stores = service.repo.list_stores()
    selected = next((s for s in stores if s.id == store_id), stores[0] if stores else None)
    status = status if status in STATUS_BADGES else None
    context = {
        "stores": stores,
        "selected": selected,
        "status": status,
        "statuses": [s.value for s in ReservationStatus],
        "reservations": service.list_for_store(selected.id, status) if selected else [],
    }
    return _render(request, "owner/reservation_list.html", context)


@router.get("/owner/reservations/{reservation_id}", response_class=HTMLResponse)
def owner_reservation_detail(
    request: Request, reservation_id: int, service: ServiceDep, error: str | None = None
) -> HTMLResponse:
    try:
        reservation = service.get(reservation_id)
    except ReservationNotFoundError as e:
        raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다") from e
    owner_actions = [
        a for a in state_of(reservation.status).allowed_actions() if a in OWNER_ACTIONS
    ]
    context = {"reservation": reservation, "owner_actions": owner_actions, "error": error}
    return _render(request, "owner/reservation_detail.html", context)


@router.post("/owner/reservations/{reservation_id}/{action}")
def owner_process(reservation_id: int, action: str, service: ServiceDep) -> RedirectResponse:
    """처리 후 상세 화면으로 돌아간다. 새로고침해도 다시 처리되지 않게 리다이렉트한다."""
    url = f"/owner/reservations/{reservation_id}"
    try:
        service.process(reservation_id, action)
    except ReservationNotFoundError as e:
        raise HTTPException(status_code=404, detail="예약을 찾을 수 없습니다") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="알 수 없는 처리입니다") from e
    except InvalidTransitionError as e:
        url += f"?error={quote(str(e))}"
    return RedirectResponse(url, status_code=303)


# ---------- 점주: 고객 이력 (UC-10) ----------


@router.get("/owner/customers", response_class=HTMLResponse)
def customer_history(request: Request, service: ServiceDep, phone: str = "") -> HTMLResponse:
    phone = phone.strip()
    history = service.customer_history(phone) if phone else None
    context = {"phone": phone, "history": history}
    return _render(request, "owner/customer_history.html", context)
