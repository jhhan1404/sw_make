"""앱 진입점. 실행: uvicorn app.main:app --reload"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db.database import init_db
from app.presentation.routers import customer, inquiry, marketing, owner, reservation


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="소상공인 AI 마케팅·고객응대 시스템", lifespan=lifespan)

app.include_router(customer.router)
app.include_router(owner.router)
app.include_router(inquiry.router)
app.include_router(marketing.router)
app.include_router(reservation.router)
