# CLAUDE.md — 팀 신창섭 코딩·AI 협업 규칙

> 프로젝트: 소상공인용 AI 마케팅·고객응대 통합 지원 시스템
> 팀: 신창섭 (한재형·정회성·전지호)
> 정회성 초안 + 한재형 안(PR #6) 통합 · 2026-11-04 · 금요일 회의에서 최종 확정

이 파일은 팀 코딩 규칙이며, Claude Code 등 AI 도구가 코드를 작성할 때도 이 규칙을 따른다.

---

## 1. 프로젝트 개요

소상공인 점주가 예약·문의·홍보 업무를 한 화면에서 처리하는 **웹 시스템**.
매장·메뉴·FAQ 관리, 예약·고객 관리, AI 문의 응대, 채널별 마케팅 콘텐츠 생성, 점주 대시보드를 제공한다.

- **언어**: Python 3.11+
- **웹**: FastAPI + Jinja2 (점주 화면과 고객 화면 분리)
- **DB**: SQLite (SQLAlchemy ORM)
- **AI**: 생성형 AI API (Adapter 패턴으로 교체 가능, 개발·테스트는 Mock)
- **진입점**: `app/main.py` (`uvicorn app.main:app --reload`)

---

## 2. 디렉터리 구조

```
sw_make/
├── app/
│   ├── main.py              # FastAPI 진입점
│   ├── presentation/        # 프레젠테이션 계층: 라우터, 템플릿
│   ├── services/            # 비즈니스 로직 계층
│   │   ├── reservation/     #   예약 + 상태 클래스 (State 패턴)
│   │   ├── inquiry/         #   문의 + FactChecker (DB 대조)
│   │   └── marketing/       #   홍보 + 채널 전략 (Strategy 패턴)
│   ├── adapters/ai/         # AI API 연동 (Adapter 패턴)
│   ├── repositories/        # DB CRUD
│   ├── models/              # SQLAlchemy 모델
│   └── db/                  # DB 연결, 가상 데이터 적재
├── tests/
├── docs/
├── requirements.txt
└── CLAUDE.md                # 본 파일
```

---

## 3. 계층 규칙 (가장 중요)

```
presentation → services → repositories → models
                  ↓
             adapters/ai
```

1. `presentation`은 `services`만 호출한다. 라우터에 비즈니스 로직이나 SQL을 쓰지 않는다.
2. 역방향 의존 금지: 하위 계층은 상위 계층을 import하지 않는다. (`services`는 `presentation`을 import하지 않는다.)
3. AI 호출은 반드시 `app/adapters/ai`의 `AIClient` 인터페이스를 통해서만 한다.
   서비스에서 특정 AI SDK를 직접 import하지 않는다.
4. 가격, 영업시간, 예약 가능 여부 같은 사실 판단은 AI가 아니라 코드가 한다.
   AI 결과는 항상 `FactChecker` 등으로 DB와 대조한다.
5. 패턴 클래스(State·Strategy·Adapter)는 서비스 계층에서만 사용한다.

---

## 4. 디자인 패턴 규칙

| 패턴 | 위치 | 규칙 |
| --- | --- | --- |
| State | `app/services/reservation/states.py` | 예약 상태 변경은 `ReservationService.apply()`로만 한다. `reservation.status = ...` 직접 대입 금지. 새 상태는 상태 클래스를 추가하고, 상태별 if/else 분기를 만들지 않는다. |
| Strategy | `app/services/marketing/strategies.py` | 새 홍보 채널은 클래스 하나 + `@register`로 추가한다. 다른 파일은 고치지 않는다. |
| Adapter | `app/adapters/ai/` | 새 AI 제공사는 `AIClient`를 상속한 Adapter 클래스를 추가하고 `factory.py`에만 연결한다. |

---

## 5. 코딩 규칙

### 5-1. 기본 원칙
- **SOLID 원칙** 준수: 특히 SRP(단일 책임), OCP(개방-폐쇄) 중점
- 한 함수는 하나의 역할만 수행 (20줄 이하 권장)
- 모든 함수·메서드에 타입 힌트 필수: `def foo(x: int) -> str:`
- 외부 입력(요청 본문, 폼)은 Pydantic 모델로 검증한다.
- `ruff check .`와 `ruff format .`을 통과해야 한다. 한 줄 최대 100자.

### 5-2. 네이밍
- 클래스: `PascalCase` (예: `ReservationService`)
- 함수·변수: `snake_case` (예: `get_menu_list`)
- 상수: `UPPER_SNAKE_CASE` (예: `MAX_PARTY_SIZE`)
- 파일: `snake_case.py`

### 5-3. 주석·오류
- docstring과 주석은 한국어로, "왜"를 설명한다. 기능 ID(F-03-3 등)를 적어 요구사항과 연결한다.
- 사용자에게 보이는 오류 메시지는 한국어로 쓴다.
- 예외는 구체적인 클래스로 정의한다 (`InvalidTransitionError`, `AIClientError`).

---

## 6. 테스트

- 기능마다 정상 케이스와 예외 케이스를 `tests/test_<기능>.py`에 작성한다.
- 테스트에서는 실제 AI를 호출하지 않고 `MockAIClient`를 쓴다.
- PR을 올리면 GitHub Actions가 `ruff`와 `pytest`를 자동 실행하며, 통과해야 Merge할 수 있다.

---

## 7. Git 규칙

| 브랜치 | 용도 |
| --- | --- |
| `main` | 최종 제출·발표 버전 (직접 push 금지) |
| `develop` | 통합 브랜치 (직접 push 금지) |
| `feature/<기능ID>-<설명>` | 기능 개발 (예: `feature/F-01-store`) |
| `fix/<설명>` | 버그 수정 |
| `docs/<설명>` | 문서 작업 |

- **PR 규칙**: `feature/*` → `develop` → `main` 순으로 머지한다. 승인은 필요 없고 CI 통과 후 본인이 Merge한다.
  다른 사람 담당 파일이나 공통 파일(`app/models/`, `app/db/`, `CLAUDE.md`, `requirements.txt`)을 고쳤다면 Merge 전에 단톡방에 알린다.
- **커밋 메시지**: 접두어 + 기능 ID. 예: `feat: F-01 메뉴 추가 기능 구현`, `fix: F-02 휴무일 예약 거부`
  (접두어: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`)
- `.env`, `*.db` 파일은 커밋하지 않는다.

---

## 8. AI 활용 규칙

### AI를 사용해도 되는 작업
- 보일러플레이트 코드 생성
- 테스트 케이스 초안 작성
- 주석·문서 작성 보조
- 디버깅 힌트 요청

### AI 사용 후 반드시 할 일
- 생성된 코드를 직접 읽고 이해한 뒤 커밋한다.
- AI가 생성한 코드 블록 위에 `# AI-assisted` 주석을 단다.
- SOLID 원칙과 위의 계층 규칙 위반 여부를 직접 검토한다.
- 단위 테스트를 작성한다 (AI가 만들어도 내용 확인 필수).
- `docs/ai_usage_log.md`에 기록한다.

### AI에게 요청할 때 포함할 정보
- 현재 계층 (presentation / services / repositories / adapters)
- 관련 패턴 (State / Strategy / Adapter)
- 입력·출력 타입
- 연관 파일 경로

---

## 9. 기능별 담당자

| 기능 | 담당 | 브랜치 예시 |
| --- | --- | --- |
| F-01 매장·메뉴·FAQ 관리 | 한재형 | `feature/F-01-store` |
| F-02 예약·고객 관리 (State 패턴) | 한재형 | `feature/F-02-reservation` |
| F-03 AI 문의 응대 (Adapter 패턴) | 정회성 | `feature/F-03-inquiry` |
| F-04 채널별 마케팅 콘텐츠 생성 (Strategy 패턴) | 전지호 | `feature/F-04-marketing` |
| F-05 점주 대시보드 | 전지호 | `feature/F-05-dashboard` |

---

## 10. 팀 회의 규칙

- 매주 금요일 1회 이상 진행 상황을 공유하고 회의록을 `docs/meetings/`에 남긴다.
- 진행 중 이슈는 GitHub Issue로 등록한다.
- 일정 변경은 README의 "팀원별 할 일"과 WBS 일정표 문서에 즉시 반영한다.
