# Product Backlog

상태: Baseline

`IMPLEMENTATION_PLAN.md`의 MVP task가 우선한다. 아래는 MVP 이후 후보이며 증거 없이 MVP로 당기지 않는다.

## Near-term

| ID | 항목 | 진입 조건 |
|---|---|---|
| BL-001 | 스캔 PDF OCR 및 표 구조 복원 | 실제 source inventory에서 OCR 비율 확인 |
| BL-002 | OpenSearch/Nori 한국어 lexical lane | PostgreSQL lexical 중요 slice Recall 미달 |
| BL-003 | 규정 변경 영향 분석 workflow | version diff UAT와 ontology 품질 확보 |
| BL-004 | 외부 법령/감독규정 connector | 라이선스·출처·갱신 책임 승인 |
| BL-005 | 2-person publication approval | production IAM/workflow 결정 |
| BL-006 | 질문에서 담당 부서 ticket 초안 | 기관 업무시스템과 권한/개인정보 승인 |
| BL-007 | ontology SHACL/RDF export | 외부 interoperability use case 확정 |

## Later

| ID | 항목 | 비고 |
|---|---|---|
| BL-101 | 다중 기관/tenant 격리 | 첫 버전은 기관별 독립 배포 권장 |
| BL-102 | self-hosted Korean LLM/embedding profile | 기관 policy와 benchmark 기반 |
| BL-103 | 규정 변경 notification/subscription | 업무 owner/빈도 결정 필요 |
| BL-104 | 승인된 답변 playbook/FAQ | 원문 규정과 별도 provenance 필요 |
| BL-105 | 고급 path analytics/community detection | QA에 실질 가치가 확인될 때 |
| BL-106 | 모바일 최적화/voice | 접근성·보안 고려 후 |
| BL-107 | multilingual regulation QA | 번역본/원문 우선순위 정책 필요 |

## 명시적으로 하지 않을 것

- citation 없는 자유형 규정 답변
- 규정 준수 여부의 자동 최종 판정
- 사용자 임의 SQL/Cypher/agent tool 실행
- 승인 없이 production 규정 자동 publish
- 실제 민감 데이터로 개발/데모

