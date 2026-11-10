# AI-assisted (Claude) — 정회성 검토 완료
"""문의 접수와 AI 답변 초안 생성. (F-03) AI는 초안만 만들고 확정은 점주가 한다."""

import json
from dataclasses import asdict, dataclass

from app.adapters.ai import AIClient, AIClientError
from app.models.models import FAQ, Inquiry, MenuItem, Store
from app.repositories.inquiry_repository import InquiryRepository
from app.services.inquiry.fact_checker import FactChecker, Mismatch
from app.services.inquiry.schemas import InquiryCreate

SYSTEM_PROMPT = (
    "당신은 소상공인 매장의 고객 문의 답변을 돕는 도우미입니다. "
    "반드시 아래 매장 정보·메뉴·FAQ만 근거로 답하세요. "
    "근거에 없는 내용은 '매장에 직접 문의해 주세요'라고 답하세요."
)


class StoreNotFoundError(Exception):
    """존재하지 않는 매장에 문의하려 할 때."""


class InquiryNotFoundError(Exception):
    """존재하지 않는 문의를 찾을 때."""


@dataclass
class DraftResult:
    draft: str | None
    mismatches: list[Mismatch]
    error: str | None = None  # AI 실패 시 안내 문구 (F-03-5)


class InquiryService:
    def __init__(self, ai_client: AIClient, repository: InquiryRepository | None = None) -> None:
        self.ai = ai_client
        self.repo = repository

    # ----- F-03-1 문의 등록 -----
    def register(self, data: InquiryCreate) -> Inquiry:
        if self.repo.get_store(data.store_id) is None:
            raise StoreNotFoundError(f"매장을 찾을 수 없습니다 (id={data.store_id})")
        customer = self.repo.find_or_create_customer(data.name, data.phone)
        inquiry = Inquiry(store_id=data.store_id, customer=customer, content=data.content)
        return self.repo.add(inquiry)

    # ----- F-03-2, F-03-3 AI 초안 생성과 DB 대조 -----
    def generate_draft(self, inquiry_id: int) -> DraftResult:
        """초안을 만들어 AI 원본(ai_draft)과 대조 결과(check_result)를 저장한다."""
        inquiry = self.get(inquiry_id)
        store = inquiry.store
        result = self.draft_answer(store, store.menu_items, store.faqs, inquiry)
        if result.draft is not None:
            inquiry.ai_draft = result.draft
            inquiry.check_result = json.dumps(
                [asdict(m) for m in result.mismatches], ensure_ascii=False
            )
            self.repo.save()
        return result

    def get(self, inquiry_id: int) -> Inquiry:
        inquiry = self.repo.get(inquiry_id)
        if inquiry is None:
            raise InquiryNotFoundError(f"문의를 찾을 수 없습니다 (id={inquiry_id})")
        return inquiry

    @staticmethod
    def mismatches_of(inquiry: Inquiry) -> list[dict[str, str]]:
        """저장된 대조 결과를 화면용으로 꺼낸다."""
        return json.loads(inquiry.check_result) if inquiry.check_result else []

    # ----- 프롬프트 구성과 초안 생성 (DB 없이도 동작) -----
    def build_prompt(
        self, store: Store, menus: list[MenuItem], faqs: list[FAQ], inquiry: Inquiry
    ) -> str:
        menu_lines = "\n".join(f"- {m.name}: {m.price:,}원" for m in menus if m.on_sale)
        faq_lines = "\n".join(f"- Q: {f.question} / A: {f.answer}" for f in faqs)
        return (
            f"[매장] {store.name}, 영업시간 {store.open_time:%H:%M}~{store.close_time:%H:%M}, "
            f"휴무일 {store.closed_days or '없음'}, 연락처 {store.phone}\n"
            f"[메뉴]\n{menu_lines}\n[FAQ]\n{faq_lines}\n"
            f"[고객 문의]\n{inquiry.content}"
        )

    def draft_answer(
        self, store: Store, menus: list[MenuItem], faqs: list[FAQ], inquiry: Inquiry
    ) -> DraftResult:
        prompt = self.build_prompt(store, menus, faqs, inquiry)
        try:
            draft = self.ai.generate(prompt, system=SYSTEM_PROMPT)
        except AIClientError as e:
            return DraftResult(draft=None, mismatches=[], error=f"AI 초안 생성 실패: {e}")

        checker = FactChecker(
            menu_prices={m.name: m.price for m in menus},
            open_time=store.open_time,
            close_time=store.close_time,
        )
        return DraftResult(draft=draft, mismatches=checker.check(draft))

    # TODO(정회성, 13주차): 점주 수정 → 발송 완료(상태 '답변완료', final_answer 저장) (F-03-4)
