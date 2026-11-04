# 팀 Git 사용 가이드

작성: 정회성 · 처음 한 번은 순서대로 따라 하고, 이후에는 "매일 작업 순서"만 보면 된다.

## 1. 처음 한 번: 내 PC에 받기

레포 초대 메일(또는 GitHub 알림)에서 **Accept invitation**을 먼저 누른다.

```bash
git clone https://github.com/sakakinji-maker/sw_make.git
cd sw_make
git config user.name "본인 이름"
git config user.email "GitHub에 등록한 이메일"

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # Windows: copy .env.example .env
pytest                           # "29 passed" 가 나오면 성공
```

`pytest`가 통과하면 README의 10주차 "각자 PC에서 실행 확인"을 체크한다.

## 2. 브랜치 구조

```
main      ← 제출·발표용. 직접 push 금지
develop   ← 통합 브랜치. 직접 push 금지, PR로 병합 (승인 없이 본인 Merge 가능)
feature/… ← 각자 작업 브랜치
```

| 담당 | 브랜치 이름 예시 |
| --- | --- |
| 한재형 | `feature/F-01-store`, `feature/F-02-reservation` |
| 정회성 | `feature/F-03-inquiry`, `feature/ai-adapter` |
| 전지호 | `feature/F-04-marketing`, `feature/F-05-dashboard` |
| 문서 | `docs/architecture`, `docs/requirements` |

## 3. 매일 작업 순서

```bash
# ① 최신 develop 받기
git checkout develop
git pull

# ② 작업 브랜치 만들기 (처음 한 번) 또는 이동
git checkout -b feature/F-02-reservation
#   이미 있으면: git checkout feature/F-02-reservation
#   그리고 최신 develop 반영: git merge develop

# ③ 작업 → 확인
pytest
ruff check .
ruff format .

# ④ 커밋 (작게, 자주)
git add .
git commit -m "feat: F-02 예약 취소 기능"

# ⑤ GitHub에 올리기
git push -u origin feature/F-02-reservation
```

## 4. Pull Request(PR) 올리기

1. GitHub 레포 화면에 뜨는 **Compare & pull request**를 누른다.
2. **base: `develop`** ← compare: 내 브랜치. (base가 `main`이 아닌지 꼭 확인)
3. 제목: `F-02 예약 취소 기능`, 본문: 무엇을 했는지, 테스트 결과, 관련 기능 ID.
4. (선택) 리뷰를 받고 싶으면 Reviewers에 팀원을 지정한다. 승인은 필수가 아니다.
5. **Merge pull request** → **Confirm merge**를 눌러 본인이 병합한다.
6. 다른 사람 담당 파일이나 공통 파일(`app/models/`, `app/db/`, `CLAUDE.md`, `requirements.txt`)을 고쳤다면, Merge 전에 단톡방에 알리고 담당자 확인을 받는다.
7. Merge 후 GitHub에 뜨는 **Delete branch**를 눌러 다 쓴 브랜치를 정리한다.

## 5. 커밋 메시지 규칙

| 접두어 | 용도 | 예시 |
| --- | --- | --- |
| `feat:` | 새 기능 | `feat: F-03 AI 답변 초안 생성` |
| `fix:` | 버그 수정 | `fix: 휴무일 예약이 접수되는 문제` |
| `test:` | 테스트 추가·수정 | `test: 예약 상태 전이 예외 케이스` |
| `docs:` | 문서 | `docs: 클래스 다이어그램 추가` |
| `refactor:` | 동작 변화 없는 구조 개선 | `refactor: 예약 검사 로직 분리` |
| `chore:` | 설정·패키지 등 | `chore: requirements 업데이트` |

## 6. 자주 생기는 문제

**push가 거부될 때 (rejected)**: 원격에 새 커밋이 있다는 뜻이다. `git pull` 후 다시 push.

**충돌(conflict)이 났을 때**: 파일에 `<<<<<<<`, `=======`, `>>>>>>>` 표시가 생긴다. 남길 코드만 남기고 표시를 지운 뒤 `git add .` → `git commit`. 모르겠으면 혼자 해결하지 말고 단톡방에 올린다.

**실수로 develop에서 작업했을 때**: 커밋하기 전이라면 `git checkout -b feature/새이름` 하면 변경 내용을 그대로 가지고 새 브랜치로 옮겨진다.

**`.env`를 커밋할 뻔했을 때**: `.gitignore`에 들어 있어서 기본적으로 올라가지 않는다. `git status`에 `.env`가 보이면 커밋하지 말고 정회성에게 알린다.
