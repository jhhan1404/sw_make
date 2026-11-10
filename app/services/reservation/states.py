"""예약 상태 클래스 (State 패턴). 기획서 10절 예약 상태 전이도 참고.

요청 --확정--> 확정 --방문처리--> 방문완료
 |  <--고객 변경--  |  --노쇼처리--> 노쇼
 +--취소--> 취소 <--취소--+
방문완료·노쇼·취소는 종료 상태로, 어떤 동작도 허용하지 않는다.
"""

from enum import StrEnum


class ReservationStatus(StrEnum):
    REQUESTED = "요청"
    CONFIRMED = "확정"
    VISITED = "방문완료"
    CANCELLED = "취소"
    NO_SHOW = "노쇼"


class InvalidTransitionError(Exception):
    """현재 상태에서 허용되지 않는 동작을 요청했을 때."""


class ReservationState:
    """모든 동작의 기본 구현은 '거부'다. 허용할 동작만 하위 클래스에서 재정의한다."""

    status: ReservationStatus

    def _deny(self, action: str) -> "ReservationState":
        raise InvalidTransitionError(f"'{self.status}' 상태에서는 '{action}'을(를) 할 수 없습니다")

    def confirm(self) -> "ReservationState":
        return self._deny("확정")

    def visit(self) -> "ReservationState":
        return self._deny("방문 처리")

    def no_show(self) -> "ReservationState":
        return self._deny("노쇼 처리")

    def cancel(self) -> "ReservationState":
        return self._deny("취소")

    def change(self) -> "ReservationState":
        return self._deny("변경")

    def allowed_actions(self) -> list[str]:
        """화면에 보여줄 버튼 목록. (예외 흐름: 가능한 버튼만 표시)"""
        actions = []
        for name in ("confirm", "visit", "no_show", "cancel", "change"):
            if getattr(type(self), name) is not getattr(ReservationState, name):
                actions.append(name)
        return actions


class RequestedState(ReservationState):
    status = ReservationStatus.REQUESTED

    def confirm(self) -> ReservationState:
        return ConfirmedState()

    def cancel(self) -> ReservationState:
        return CancelledState()

    def change(self) -> ReservationState:
        return RequestedState()


class ConfirmedState(ReservationState):
    status = ReservationStatus.CONFIRMED

    def visit(self) -> ReservationState:
        return VisitedState()

    def no_show(self) -> ReservationState:
        return NoShowState()

    def cancel(self) -> ReservationState:
        return CancelledState()

    def change(self) -> ReservationState:
        # 확정된 예약을 고객이 바꾸면 점주가 다시 확정해야 한다.
        return RequestedState()


class VisitedState(ReservationState):
    status = ReservationStatus.VISITED


class CancelledState(ReservationState):
    status = ReservationStatus.CANCELLED


class NoShowState(ReservationState):
    status = ReservationStatus.NO_SHOW


_STATE_BY_STATUS: dict[str, type[ReservationState]] = {
    cls.status.value: cls
    for cls in (RequestedState, ConfirmedState, VisitedState, CancelledState, NoShowState)
}


def state_of(status: str) -> ReservationState:
    """DB에 저장된 상태 문자열로 상태 객체를 만든다."""
    try:
        return _STATE_BY_STATUS[status]()
    except KeyError as e:
        raise ValueError(f"알 수 없는 예약 상태: {status}") from e
