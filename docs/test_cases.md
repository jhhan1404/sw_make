# 테스트 케이스 (담당: 정회성 취합)

필수 기능별 **정상·예외 테스트 케이스** 목록입니다. 과목 공통 요건 "필수 기능별 정상·예외 테스트 케이스"의 제출본이 됩니다.

## 작성 규칙

- 기능을 구현한 사람이 자기 기능의 행을 추가합니다. 정회성은 13주차에 빠진 기능이 없는지 확인합니다.
- **기능 ID마다 정상 1개 이상, 예외 1개 이상.**
- 자동화한 테스트는 `파일::함수` 를 적습니다. 화면으로만 확인한 경우 "수동"이라고 적고 확인 날짜를 남깁니다.
- 결과: ✅ 통과 / ❌ 실패 / ⬜ 미작성

| 열 | 쓰는 법 |
| --- | --- |
| TC ID | `TC-<기능번호>-<순번>` 예: `TC-02-03` |
| 기능 ID | 기획서 6절의 세부 ID (예: F-02-4) |
| 구분 | 정상 / 예외 |
| 입력·조건 | 무엇을 넣었는지, 어떤 상태에서 했는지 |
| 기대 결과 | 시스템이 어떻게 반응해야 하는지 |
| 자동화 | `tests/파일.py::함수` 또는 "수동(11/12)" |

---

## F-01 매장·메뉴·FAQ 관리 (한재형)

| TC ID | 기능 ID | 구분 | 입력·조건 | 기대 결과 | 자동화 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-01-01 | F-01-1 | 정상 | 매장명·영업시간·휴무일 입력 후 저장 | 저장되고 조회 화면에 반영 | | ⬜ |
| TC-01-02 | F-01-1 | 예외 | 종료 시각이 시작 시각보다 이름 (21:00~09:00) | 저장 거부, 오류 메시지 | | ⬜ |
| TC-01-03 | F-01-2 | 정상 | 메뉴 등록 (이름, 가격 4500) | 메뉴 목록에 추가 | | ⬜ |
| TC-01-04 | F-01-2 | 예외 | 가격 -1000 또는 문자 입력 | 저장 거부, 오류 메시지 | | ⬜ |
| TC-01-05 | F-01-3 | 정상 | FAQ 질문·답변 등록 | FAQ 목록에 추가 | | ⬜ |

## F-02 예약 관리 (한재형)

| TC ID | 기능 ID | 구분 | 입력·조건 | 기대 결과 | 자동화 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-02-01 | F-02-4 | 정상 | "요청" 상태에서 확정·취소·변경 | 각각 확정 / 취소 / 요청 | `tests/test_reservation_states.py::test_allowed_transitions` | ✅ |
| TC-02-02 | F-02-4 | 정상 | "확정" 상태에서 방문·노쇼·취소·변경 | 방문완료 / 노쇼 / 취소 / 요청(재확정 필요) | `tests/test_reservation_states.py::test_allowed_transitions` | ✅ |
| TC-02-03 | F-02-4 | 예외 | "요청"에서 방문 처리, "취소"에서 확정 등 | `InvalidTransitionError` | `tests/test_reservation_states.py::test_denied_transitions` | ✅ |
| TC-02-04 | F-02-4 | 예외 | 종료 상태(방문완료·취소·노쇼)의 버튼 목록 | 빈 목록 (버튼 없음) | `tests/test_reservation_states.py::test_terminal_states_have_no_actions` | ✅ |
| TC-02-05 | F-02-4 | 예외 | DB에 없는 상태 문자열 "보류" | `ValueError` | `tests/test_reservation_states.py::test_unknown_status` | ✅ |
| TC-02-06 | F-02-1 | 정상 | 영업일 영업시간 안, 정원 이내로 예약 신청 | "요청" 상태로 저장, 예약 번호 표시 | | ⬜ |
| TC-02-07 | F-02-2 | 예외 | 휴무일(월) 예약 신청 | 거부, 사유 표시 | | ⬜ |
| TC-02-08 | F-02-2 | 예외 | 영업시간 밖(22:00) 예약 신청 | 거부, 사유 표시 | | ⬜ |
| TC-02-09 | F-02-2 | 예외 | 시간당 정원 초과 | 거부, 다른 시간대 안내 | | ⬜ |
| TC-02-10 | F-02-3 | 예외 | 없는 연락처로 조회 | "예약을 찾을 수 없습니다" | | ⬜ |
| TC-02-11 | F-02-5 | 정상 | 상태 변경 | 이전·이후 상태가 이력에 기록 | | ⬜ |

## F-03 문의 접수·AI 답변 초안 (정회성)

| TC ID | 기능 ID | 구분 | 입력·조건 | 기대 결과 | 자동화 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-03-01 | F-03-2 | 정상 | 문의 + 매장 정보로 초안 생성 | 프롬프트에 메뉴 가격·영업시간 포함 | `tests/test_inquiry_service.py::test_prompt_contains_store_info` | ✅ |
| TC-03-02 | F-03-3 | 정상 | 초안 속 가격·시각이 모두 DB와 같음 | 불일치 0건 | `tests/test_fact_checker.py::test_correct_draft_passes` | ✅ |
| TC-03-03 | F-03-3 | 예외 | 초안에 틀린 가격(4,000원) | 가격 불일치 1건 | `tests/test_fact_checker.py::test_wrong_price_detected` | ✅ |
| TC-03-04 | F-03-3 | 예외 | 초안에 틀린 시각(22:00) | 시각 불일치 1건 | `tests/test_fact_checker.py::test_wrong_time_detected` | ✅ |
| TC-03-05 | F-03-3 | 정상 | 한 자리 시각 표기(9:00) | 09:00으로 인식해 통과 | `tests/test_fact_checker.py::test_single_digit_hour_normalized` | ✅ |
| TC-03-06 | F-03-3 | 예외 | AI가 틀린 가격(3,000원)으로 답함 | 초안과 함께 경고 반환 | `tests/test_inquiry_service.py::test_draft_with_wrong_price_warns` | ✅ |
| TC-03-07 | F-03-5 | 예외 | AI 호출 실패 | 초안 없음 + 오류 안내 | `tests/test_inquiry_service.py::test_ai_failure_returns_error` | ✅ |
| TC-03-08 | F-03-1 | 정상 | 고객이 이름·연락처·내용으로 문의 등록 | "미응답"으로 저장 | | ⬜ |
| TC-03-09 | F-03-1 | 예외 | 내용이 비었거나 1,000자 초과 | 등록 거부 | | ⬜ |
| TC-03-10 | F-03-4 | 정상 | 초안 수정 후 발송 완료 | 상태 "답변완료", AI 원본과 최종 답변 모두 저장 | | ⬜ |

## F-04 채널별 AI 홍보 문구 (전지호)

| TC ID | 기능 ID | 구분 | 입력·조건 | 기대 결과 | 자동화 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-04-01 | F-04-1 | 정상 | 등록된 채널 목록 | instagram, blog, sms 포함 | `tests/test_marketing_strategies.py::test_channels_registered` | ✅ |
| TC-04-02 | F-04-2 | 정상 | 규칙을 지킨 인스타그램 문구 | 위반 0건 | `tests/test_marketing_strategies.py::test_instagram_valid_text` | ✅ |
| TC-04-03 | F-04-2 | 예외 | 문자(SMS)에 해시태그 포함 | 해시태그 위반 표시 | `tests/test_marketing_strategies.py::test_sms_rejects_hashtags` | ✅ |
| TC-04-04 | F-04-1 | 예외 | 없는 채널 "tiktok" | `ValueError` | `tests/test_marketing_strategies.py::test_unknown_channel` | ✅ |
| TC-04-05 | F-04-1 | 예외 | AI 호출 실패 | 문구 없음 + 오류 안내 | `tests/test_marketing_strategies.py::test_service_handles_ai_failure` | ✅ |
| TC-04-06 | F-04-3 | 정상 | 생성 문구 저장 후 채널별 목록 조회 | 저장한 문구가 목록에 표시 | | ⬜ |

## F-05 대시보드 (전지호)

| TC ID | 기능 ID | 구분 | 입력·조건 | 기대 결과 | 자동화 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-05-01 | F-05-1 | 정상 | 점주 화면 접속 | 200 응답 | `tests/test_app.py::test_pages_open` | ✅ |
| TC-05-02 | F-05-1 | 정상 | 오늘 예약 3건, 미응답 문의 2건 | 숫자와 목록이 그대로 표시 | | ⬜ |
| TC-05-03 | F-05-1 | 예외 | 오늘 예약 0건 | "오늘 예약이 없습니다" 안내 | | ⬜ |

## 공통: 가상 데이터 (정회성)

| TC ID | 대상 | 구분 | 입력·조건 | 기대 결과 | 자동화 | 결과 |
| --- | --- | --- | --- | --- | --- | --- |
| TC-D-01 | 문의 데이터 | 정상 | `inquiries.json` | 30건, 가격·영업시간·근거없음 각 10건 | `tests/test_seed_data.py::test_inquiry_count_and_mix` | ✅ |
| TC-D-02 | 문의 데이터 | 정상 | 가격·영업시간 문의의 정답 | `stores.json`과 일치 | `tests/test_seed_data.py::test_price_answers_match_menu`, `::test_hour_answers_match_store` | ✅ |
| TC-D-03 | 문의 데이터 | 정상 | 근거없음 문의의 핵심어 | 메뉴·FAQ 어디에도 없음 | `tests/test_seed_data.py::test_out_of_scope_really_has_no_basis` | ✅ |
| TC-D-04 | 적재 | 정상 | `load_all()` 실행 | 매장·메뉴·FAQ·문의가 DB에 들어감 | `tests/test_seed_data.py::test_load_all_into_db` | ✅ |
| TC-D-05 | 적재 | 예외 | 없는 매장 키를 참조하는 FAQ | `SeedDataError` | `tests/test_seed_data.py::test_unknown_store_key_is_reported` | ✅ |

---

**현황 (11/04)**: 자동화 ✅ 23건 / 미작성 ⬜ 17건. 미작성 행은 12~13주차에 각 담당자가 구현하면서 채웁니다.
