# CLAUDE.md — AI 협업 규칙

> 프로젝트: 소상공인용 AI 마케팅·고객응대 통합 지원 시스템  
> 팀: 신창섭 (한재형·정회성·전지호) | 확정일: 2026-11-03

---

## 1. 프로젝트 개요

소규모 자영업자를 위한 CLI 기반 AI 통합 지원 시스템.  
매장·메뉴·FAQ 관리, 예약·고객 관리, AI 문의 응대, 마케팅 콘텐츠 생성 기능을 제공한다.

- **언어**: Python 3.11+
- **DB**: SQLite (SQLAlchemy ORM)
- **AI**: OpenAI / Claude API (Adapter 패턴으로 교체 가능)
- **진입점**: `main.py`

---

## 2. 디렉터리 구조

```
sw_make/
├── main.py                  # CLI 진입점
├── requirements.txt
├── CLAUDE.md                # 본 파일
├── app/
│   ├── models/              # SQLAlchemy 모델
│   ├── repositories/        # DB CRUD
│   ├── services/            # 비즈니스 로직
│   ├── patterns/
│   │   ├── state/           # 예약 상태 (State 패턴)
│   │   ├── strategy/        # 채널별 홍보 (Strategy 패턴)
│   │   └── adapter/         # AI API (Adapter 패턴)
│   ├── presentation/        # CLI 메뉴
│   └── utils/               # DB 연결, 설정
└── tests/
```

---

## 3. 코딩 규칙

### 3-1. 기본 원칙
- **SOLID 원칙** 준수: 특히 SRP(단일 책임), OCP(개방-폐쇄) 중점
- 한 함수는 하나의 역할만 수행 (20줄 이하 권장)
- 타입 힌트 필수: `def foo(x: int) -> str:`
- Pydantic으로 입력값 검증

### 3-2. 네이밍
- 클래스: `PascalCase` (예: `ReservationService`)
- 함수·변수: `snake_case` (예: `get_menu_list`)
- 상수: `UPPER_SNAKE_CASE` (예: `MAX_PARTY_SIZE`)
- 파일: `snake_case.py`

### 3-3. 디자인 패턴 적용 위치
- **State 패턴** → `app/patterns/state/` (예약 상태 전이)
- **Strategy 패턴** → `app/patterns/strategy/` (채널별 홍보 포맷)
- **Adapter 패턴** → `app/patterns/adapter/` (AI API 연동)

### 3-4. 계층 의존 규칙
```
presentation → service → repository → model
```
- 역방향 의존 금지 (하위 계층이 상위 계층을 import하지 않는다)
- Service 계층에서만 패턴 클래스 사용

---

## 4. Git 브랜치 규칙

| 브랜치 | 용도 |
|--------|------|
| `main` | 최종 안정 버전 (직접 push 금지) |
| `dev` | 통합 브랜치 |
| `feature/기능명` | 기능 개발 (예: `feature/f01-menu`) |
| `fix/버그명` | 버그 수정 |

**PR 규칙**: `feature/*` → `dev` → `main` 순으로 머지  
**커밋 메시지**: `[F-01] 메뉴 추가 기능 구현` 형식

---

## 5. AI 활용 규칙

### AI를 사용해도 되는 작업
- 보일러플레이트 코드 생성
- 테스트 케이스 초안 작성
- 주석·문서 작성 보조
- 디버깅 힌트 요청

### AI 사용 후 반드시 할 일
- 생성된 코드를 직접 읽고 이해한 뒤 커밋
- AI 생성 코드임을 주석에 명시: `# AI-assisted`
- SOLID 원칙 위반 여부 직접 검토
- 단위 테스트 작성 (AI가 만들어도 내용 확인 필수)

### AI에게 요청할 때 포함할 정보
- 현재 계층 (presentation / service / repository)
- 관련 패턴 (State / Strategy / Adapter)
- 입력·출력 타입
- 연관 파일 경로

---

## 6. 기능별 담당자

| 기능 | 담당 | 브랜치 |
|------|------|--------|
| F-01 매장·메뉴·FAQ 관리 | 한재형 | `feature/f01-store` |
| F-02 예약·고객 관리 (State 패턴) | 정회성 | `feature/f02-reservation` |
| F-03 AI 문의 응대 (Adapter 패턴) | 정회성 | `feature/f03-inquiry` |
| F-04 마케팅 콘텐츠 생성 | 전지호 | `feature/f04-marketing` |
| F-05 채널별 홍보·대시보드 (Strategy 패턴) | 전지호 | `feature/f05-channel` |

---

## 7. 팀 회의 규칙

- 매주 1회 이상 진행 상황 공유
- 진행 중 이슈는 GitHub Issue로 등록
- WBS 변경 사항은 `03_WBS_일정표` 문서에 즉시 반영
