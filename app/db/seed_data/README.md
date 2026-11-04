# 가상 데이터 (11주차, 전원)

실제 개인정보·실제 매장 자료는 사용하지 않습니다. 생성형 AI로 만들고, 사용한 프롬프트는 `docs/data_prompts.md`에 남깁니다.

```bash
python -m app.db.seed           # DB가 비어 있을 때 적재
python -m app.db.seed --reset   # 모두 지우고 다시 적재
pytest tests/test_seed_data.py  # 데이터 품질 검사
```

## 파일 현황

| 파일 | 내용 | 수량 | 담당 | 상태 |
| --- | --- | --- | --- | --- |
| `stores.json` | 매장 + 메뉴 | 매장 2, 메뉴 10/매장 | 한재형 | **초안** (정회성 작성, 한재형 검토·보완) |
| `customers.json` | 고객 | 30 | 한재형 | 미작성 |
| `reservations.json` | 예약 (상태 골고루) | 50 | 한재형 | 미작성 |
| `faqs.json` | FAQ | 10/매장 | 정회성 | ✅ |
| `inquiries.json` | 문의 (가격 10, 영업시간 10, 근거없음 10) | 30 | 정회성 | ✅ |
| `contents.json` | 채널별 홍보 문구 예시 | 채널당 5 | 전지호 | 미작성 |

`stores.json`은 문의·FAQ의 정답이 매장 정보와 맞아야 해서 정회성이 먼저 초안을 만들었습니다. 한재형은 메뉴를 늘리거나 바꿔도 되지만, **매장 키(`cafe`, `salon`), 영업시간, 휴무일, 기존 메뉴 이름과 가격을 바꾸면** `pytest tests/test_seed_data.py`가 실패합니다. 바꿔야 한다면 `inquiries.json`의 정답(`expected`)도 함께 고칩니다.

## 파일 형식

모든 파일은 JSON 배열입니다. 매장은 `store` 필드에 `stores.json`의 `key`로 가리킵니다. 고객은 `{"name", "phone"}`으로 쓰며, 같은 연락처는 같은 고객으로 합쳐집니다.

**stores.json**
```json
{"key": "cafe", "name": "온기 카페", "category": "카페", "address": "...",
 "open_time": "09:00", "close_time": "21:00", "closed_days": "월",
 "phone": "02-000-1111", "capacity_per_hour": 10,
 "menu": [{"name": "아메리카노", "price": 4500, "description": "..."}]}
```

**customers.json**
```json
{"name": "김하늘", "phone": "010-0000-0101"}
```

**reservations.json**
```json
{"store": "cafe", "customer": {"name": "김하늘", "phone": "010-0000-0101"},
 "reserved_at": "2026-11-10T12:00", "party_size": 4, "request": "창가 자리", "status": "확정"}
```
`status`는 요청 / 확정 / 방문완료 / 취소 / 노쇼 중 하나입니다.

**faqs.json**
```json
{"store": "cafe", "question": "주차 되나요?", "answer": "건물 뒤편에 2대 주차할 수 있습니다."}
```

**inquiries.json**
```json
{"id": "Q01", "store": "cafe", "category": "가격",
 "customer": {"name": "김하늘", "phone": "010-0000-0101"},
 "received_at": "2026-11-02T10:12", "content": "아메리카노 한 잔 얼마예요?",
 "expected": {"prices": {"아메리카노": 4500}}}
```
`category`, `expected`, `note`, `oos_keyword`는 13주차 AI 검증 실험용 정답 정보이며 DB에는 들어가지 않습니다.
- `가격`: `expected.prices`에 정답 가격
- `영업시간`: `expected`에 관련 `open_time` / `close_time` / `closed_days`
- `근거없음`: 매장 정보에 없는 질문. AI가 지어내지 않고 "매장에 직접 문의"로 안내해야 정답. `oos_keyword`가 메뉴·FAQ에 없어야 함
- `note`: 합계 금액처럼 FactChecker가 오탐·미탐할 수 있는 경우 표시 (Q03, Q19, Q20)

**contents.json**
```json
{"store": "cafe", "channel": "instagram", "target": "밤라떼",
 "keywords": ["가을", "따뜻함"], "text": "..."}
```
`channel`은 `instagram` / `blog` / `sms` 중 하나입니다.
