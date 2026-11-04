# CLAUDE.md — 팀 신창섭 코딩 규칙

이 파일은 팀 코딩 규칙이며, Claude Code 등 AI 도구가 코드를 작성할 때도 이 규칙을 따른다.
(초안: 정회성 · 11주차에 팀 확정)

## 프로젝트 요약

소상공인용 AI 마케팅·고객응대 시스템. Python 3.11+, FastAPI, SQLAlchemy, SQLite, Jinja2.
3계층 구조(presentation → services → repositories/models)이며 패턴은 State, Strategy, Adapter.

## 계층 규칙 (가장 중요)

1. `presentation`은 `services`만 호출한다. 라우터에 비즈니스 로직이나 SQL을 쓰지 않는다.
2. `services`는 `presentation`을 import하지 않는다.
3. AI 호출은 반드시 `app/adapters/ai`의 `AIClient` 인터페이스를 통해서만 한다.
   서비스에서 특정 AI SDK를 직접 import하지 않는다.
4. 가격, 영업시간, 예약 가능 여부 같은 사실 판단은 AI가 아니라 코드가 한다.
   AI 결과는 항상 `FactChecker` 등으로 DB와 대조한다.

## 패턴 규칙

- 예약 상태 변경은 `ReservationService.apply()`로만 한다. `reservation.status = ...` 직접 대입 금지.
- 새 상태는 `states.py`에 상태 클래스를 추가한다. 상태별 if/else 분기를 만들지 않는다.
- 새 홍보 채널은 `strategies.py`에 클래스 하나 + `@register`로 추가한다. 다른 파일은 고치지 않는다.
- 새 AI 제공사는 `AIClient`를 상속한 Adapter 클래스를 추가하고 `factory.py`에만 연결한다.

## 코드 스타일

- `ruff check .`와 `ruff format .`을 통과해야 한다. 한 줄 최대 100자.
- 이름: 변수·함수 `snake_case`, 클래스 `PascalCase`, 상수 `UPPER_SNAKE_CASE`.
- 모든 함수·메서드에 타입 힌트를 단다.
- docstring과 주석은 한국어로, "왜"를 설명한다. 기능 ID(F-03-3 등)를 적어 요구사항과 연결한다.
- 사용자에게 보이는 오류 메시지는 한국어로 쓴다.
- 예외는 구체적인 클래스로 정의한다 (`InvalidTransitionError`, `AIClientError`).

## 테스트

- 기능마다 정상 케이스와 예외 케이스를 `tests/test_<기능>.py`에 작성한다.
- 테스트에서는 실제 AI를 호출하지 않고 `MockAIClient`를 쓴다.
- PR 전 `pytest` 전체 통과.

## Git

- 브랜치: `feature/<기능ID>-<설명>`, 커밋: `feat:`, `fix:`, `test:`, `docs:`, `refactor:`.
- develop·main에는 PR로만 병합한다. 승인은 필요 없지만 `pytest` 통과 후 Merge한다.
- `.env`, `*.db` 파일은 커밋하지 않는다.

## AI 도구 사용

- AI로 코드나 문서를 만들었으면 `docs/ai_usage_log.md`에 기록한다.
- AI가 만든 코드도 직접 읽고 테스트한 뒤 커밋한다.
