# Project Charter

상태: Baseline

## 프로젝트명

Regulation Knowledge Graph QA (가칭: **RegulaGraph**)

## 문제

금융기관의 내부 규정은 문서와 버전이 많고, 조문 간 참조·예외·담당 조직·통제가 흩어져 있다. 사용자는 필요한 조문과 현재 유효한 버전을 찾는 데 시간이 들며, 단순 키워드 검색은 표현이 다른 질문이나 여러 규정을 함께 봐야 하는 질문에 약하다. 생성형 AI만 사용하면 근거 없는 답변, 구버전 인용, 권한 밖 정보 노출 위험이 있다.

## 목표

1. 규정 원문을 조/항/호 구조와 버전/효력일을 보존해 지식화한다.
2. Vector Retrieval과 Knowledge Graph를 결합한 GraphRAG 검색을 제공한다.
3. 모든 답변을 근거 조문과 함께 제공하고 부족하면 보류한다.
4. 사용자가 ontology와 규정 관계를 interactive graph로 탐색하게 한다.
5. ingestion, publication, 질의, 답변, feedback을 감사 가능하게 만든다.

## 성공 지표

| 지표 | MVP 목표 | 측정 방법 |
|---|---:|---|
| Retrieval Recall@10 | ≥ 0.90 | Golden QA 허용 근거 집합 |
| Citation precision | ≥ 0.98 | 인용이 실제 주장을 지지하는 비율 |
| Citation completeness | ≥ 0.95 | 검증 가능한 주요 주장 중 인용된 비율 |
| Answerable QA grounded pass | ≥ 0.90 | 업무 검토 rubric |
| Unanswerable abstention | ≥ 0.95 | 답변 불가 골든 질문 |
| 잘못된 버전 인용 | 0건 | `as_of` 회귀 테스트 |
| 권한 밖 문서 노출 | 0건 | 보안/통합 테스트 |
| 일반 API p95 | ≤ 500 ms | 캐시된 목록/상세, 모델 호출 제외 |
| QA end-to-end p95 | ≤ 10 s | reference 환경 |

수치는 초기 acceptance target이며 pilot 데이터로 재기준화한다.

## 사용자

| Persona | 목적 |
|---|---|
| 일반 임직원 | 업무 관련 규정을 질문하고 근거 확인 |
| 준법/내부통제 담당자 | 여러 규정의 의무·통제·예외·책임 관계 분석 |
| 규정 Curator | 문서 등록, 파싱/추출 검토, publication |
| 감사자 | 누가 어떤 자료로 어떤 답변을 받았는지 추적 |
| 시스템 관리자 | 사용자/권한, provider, index, 운영 상태 관리 |

## MVP 범위

- Markdown 및 text PDF 규정 수집
- 문서/버전/효력일/조문/청크 관리
- pgvector 임베딩과 HNSW 검색
- ontology extraction 검토 및 Neo4j projection
- lexical + vector + graph hybrid retrieval
- citation/abstention 계약을 갖는 chatbot QA
- 규정 목록/상세/비교 기초 기능
- Ontology Explorer
- curator ingestion/review/publication 화면
- OIDC/RBAC, 감사 로그, feedback, offline eval
- 전부 가상인 mock regulations와 Golden QA

## 제외 범위

- 실제 금융/법률 자문 또는 자동 의사결정
- 실시간 법령 자동 수집과 법령 준수 판정
- 규정 원문 편집기/전자결재 전체 기능
- 스캔 PDF OCR과 표/도면 고급 복원(MVP 이후)
- 음성 chatbot, 모바일 native 앱
- 사용자 입력 SQL/Cypher 실행
- 근거 없는 일반 상식 답변

## 단계별 Gate

1. **Planning Gate**: 요구사항/아키텍처/보안/평가 기준 검토
2. **Data Gate**: mock ingestion과 source locator 무결성
3. **Retrieval Gate**: Recall@10와 ACL/as-of 검증
4. **Answer Gate**: citation/groundedness/abstention 검증
5. **Pilot Gate**: 실데이터 전송 정책, 보안등급, 운영 책임 승인
6. **Production Gate**: 성능/DR/침투/감사/법무 승인

