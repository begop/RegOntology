# Mock Regulation Dataset

이 폴더의 모든 데이터는 **가상 데이터**다. 실제 법령, 감독규정, 금융기관 규정 또는 법률 자문이 아니다.

## 가상 기관

- 기관명: 한빛금융
- 부서: 전자금융운영부, 정보보호부, 개인정보보호부, 업무연속성센터
- 날짜, 기간, 통제, 담당 역할은 모두 테스트를 위해 임의로 정했다.

## 파일

- `regulations/MOCK-EFO-001-v1.0.md`: 전자금융업무 운영규정
- `regulations/MOCK-ISP-001-v1.0.md`: 정보보호 운영규정
- `regulations/MOCK-ISP-001-v1.1.md`: 정보보호 운영규정 개정본
- `regulations/MOCK-PIP-001-v1.0.md`: 개인정보 처리규정(Restricted ACL 테스트)
- `ontology/ontology_seed.json`: 승인된 ontology graph 기대값
- `evaluation/qa_gold.jsonl`: QA/eval seed

## Parser 기대값

| 문서 | 장 | 조 | 최상위 항 |
|---|---:|---:|---:|
| MOCK-EFO-001 v1.0 | 3 | 7 | 17 |
| MOCK-ISP-001 v1.0 | 3 | 7 | 17 |
| MOCK-ISP-001 v1.1 | 3 | 7 | 17 |
| MOCK-PIP-001 v1.0 | 3 | 7 | 18 |

구현 parser의 세부 item count는 nested list 정책을 확정한 뒤 snapshot으로 고정한다.

## 데모 질문

1. “중요정보시스템 접근권한은 얼마나 자주 검토해야 하나요?”
2. “긴급 접근계정을 사용할 수 있는 예외와 사후조치는 무엇인가요?”
3. “중대한 전자금융사고는 언제 누구에게 보고해야 하나요?”
4. “개인정보 보유기간이 끝나면 언제 파기해야 하나요?”(Restricted 권한 test)
5. “해외송금 수수료 한도는 얼마인가요?”(답변 불가 test)

## Version/ACL test

- 모든 v1.0은 2026-01-01부터 유효하다. 2025-12-31 질문에는 검색되면 안 된다.
- MOCK-ISP-001 v1.0은 2026-07-01에 종료되고 v1.1이 그날부터 유효하다. 제5조 제2항의 회수 기한이 `1영업일`에서 `8시간`으로 바뀐다.
- PIP 문서는 `restricted`; 권한이 없는 사용자는 문서명, graph node, citation을 포함해 존재를 추론할 수 없어야 한다.
- `is_mock: true`는 ingestion 후 모든 파생 row/node/answer warning에 전파한다.
