# Requirements

상태: Baseline

## 기능 요구사항

| ID | 요구사항 | 우선순위 | MVP |
|---|---|---:|:---:|
| FR-001 | Curator는 Markdown 및 text PDF 규정 파일과 문서 메타데이터를 등록할 수 있어야 한다. | Must | ✓ |
| FR-002 | 시스템은 문서별 다중 버전, 공포/시행/종료일, 대체 관계와 checksum을 보존해야 한다. | Must | ✓ |
| FR-003 | 시스템은 편/장/절/조/항/호/목 구조와 stable locator를 보존해 파싱해야 한다. | Must | ✓ |
| FR-004 | Curator는 파싱 오류와 ontology extraction을 검토·수정·승인·반려할 수 있어야 한다. | Must | ✓ |
| FR-005 | 승인된 규정만 원자적으로 publication하고 index/graph 상태를 추적해야 한다. | Must | ✓ |
| FR-006 | 시스템은 조문 구조를 보존한 chunk와 embedding을 생성하고 pgvector에서 검색해야 한다. | Must | ✓ |
| FR-007 | 시스템은 lexical, vector, graph retrieval을 결합한 GraphRAG를 제공해야 한다. | Must | ✓ |
| FR-008 | 사용자는 자연어 질문에 답변, 구조화 citation, 적용 기준일, 신뢰/주의 안내를 받아야 한다. | Must | ✓ |
| FR-009 | 충분한 근거가 없거나 질문이 권한 밖이면 시스템은 이유와 다음 행동을 포함해 답변을 보류해야 한다. | Must | ✓ |
| FR-010 | 사용자는 citation을 열어 해당 규정 버전과 조문 원문을 확인할 수 있어야 한다. | Must | ✓ |
| FR-011 | 사용자는 문서/상태/효력일/보안등급/키워드로 규정을 검색하고 상세를 볼 수 있어야 한다. | Must | ✓ |
| FR-012 | 사용자는 두 규정 버전의 조문 차이를 비교할 수 있어야 한다. | Should | 부분 |
| FR-013 | 사용자는 ontology node/edge를 검색·필터·확장하고 관련 조문으로 이동할 수 있어야 한다. | Must | ✓ |
| FR-014 | 시스템은 질문 entity를 연결하고 의무·금지·예외·담당 조직·통제를 제한된 hop으로 확장해야 한다. | Must | ✓ |
| FR-015 | 사용자는 답변에 도움이 됨/문제 있음 feedback과 사유를 남길 수 있어야 한다. | Should | ✓ |
| FR-016 | 감사자는 ingestion, 승인, publication, 질의, 답변, feedback 이벤트를 검색할 수 있어야 한다. | Must | ✓ |
| FR-017 | 시스템은 OIDC 인증과 역할/문서 scope 기반 권한을 모든 API와 검색 lane에 적용해야 한다. | Must | ✓ |
| FR-018 | 관리자는 index/projection build 상태, 실패 원인, watermark를 확인하고 안전하게 재시도할 수 있어야 한다. | Must | ✓ |
| FR-019 | 시스템은 Golden QA dataset으로 retrieval/answer/citation/abstention을 재현 가능하게 평가해야 한다. | Must | ✓ |
| FR-020 | 사용자는 질의별 retrieval trace 요약을 권한 범위 내에서 볼 수 있어야 한다. | Should | ✓ |

## 비기능 요구사항

| ID | 요구사항 | 검증 기준 |
|---|---|---|
| NFR-001 | 보안 경계 | 인증 누락/권한 밖 요청은 fail closed, 검색 후보에도 ACL 사전 적용 |
| NFR-002 | 근거성 | 주요 주장은 citation 보유, verifier 실패 시 재생성 1회 후 보류 |
| NFR-003 | 시간 정확성 | `as_of`에 유효하지 않은 버전/조문 인용 0건 |
| NFR-004 | 재현성 | model/prompt/embedding/ontology/index/source version과 trace ID 저장 |
| NFR-005 | 감사성 | 중요 읽기/모든 변경/AI 실행은 actor, time, action, target, outcome 기록 |
| NFR-006 | 데이터 최소화 | provider로 보내는 텍스트는 검색된 최소 조문과 질문으로 제한 |
| NFR-007 | 성능 | 프로젝트 헌장의 p95 목표 충족, timeout 시 명시적 부분 실패/보류 |
| NFR-008 | 가용성 | MVP 월 99.5% 목표, graph 장애 시 표시 후 vector-only degraded mode 가능 |
| NFR-009 | 접근성 | WCAG 2.2 AA 목표, graph 대체 list/detail 탐색 제공 |
| NFR-010 | 관측성 | request/job/model 호출에 trace, metric, 구조화 log, correlation ID |
| NFR-011 | 공급망 | lockfile, SBOM, dependency/license/secret scan, signed release artifact |
| NFR-012 | 백업/복구 | PostgreSQL RPO 15분/RTO 4시간 목표, Neo4j는 projection rebuild 가능 |
| NFR-013 | 확장 기준선 | 10,000 규정 버전, 300,000 chunk, 50 동시 QA 사용자에서 benchmark |
| NFR-014 | 이식성 | LLM/embedding/graph provider를 domain port로 분리 |
| NFR-015 | 개인정보 | 분류/마스킹/retention 적용, 로그 본문 저장 최소화 |

## 핵심 수용 기준

| ID | 연결 | Given / When / Then |
|---|---|---|
| AC-FR-002-01 | FR-002 | 같은 문서의 새 버전을 publish하면 이전 버전은 보존되고 효력 기간이 겹치지 않는다. |
| AC-FR-003-01 | FR-003 | 목업 규정을 ingest하면 모든 조/항/호가 원문과 동일한 계층 locator로 조회된다. |
| AC-FR-005-01 | FR-005 | graph build가 실패하면 publication은 활성화되지 않고 기존 snapshot은 유지된다. |
| AC-FR-007-01 | FR-007 | 골든 질문의 허용 근거가 top 10 후보에 90% 이상 포함된다. |
| AC-FR-008-01 | FR-008 | 답변 카드에 적용 기준일과 최소 1개 조문 citation이 표시된다. |
| AC-FR-009-01 | FR-009 | 데이터에 없는 질문에는 답을 만들지 않고 `insufficient_evidence`를 반환한다. |
| AC-FR-010-01 | FR-010 | citation 선택 시 정확한 버전/locator로 이동하고 인용 구절이 강조된다. |
| AC-FR-013-01 | FR-013 | node 선택 시 1-hop 관계와 관련 조문이 표시되며 최대 node 제한을 넘지 않는다. |
| AC-FR-013-02 | FR-013 | 사용자가 2D 그래프, 3D 입체 캔버스, 접근 가능한 목록을 전환해도 동일한 ACL/기준일/검색/유형 필터 결과와 선택 node·provenance가 유지된다. |
| AC-FR-017-01 | FR-017 | Restricted 권한이 없는 사용자의 모든 검색, graph, citation에 해당 문서가 나타나지 않는다. |
| AC-FR-019-01 | FR-019 | 동일 snapshot/config/seed에서 eval 결과와 trace artifact를 재생성할 수 있다. |
| AC-NFR-002-01 | NFR-002 | citation이 answer claim을 지지하지 않으면 verifier가 응답을 차단한다. |
| AC-NFR-003-01 | NFR-003 | 시행일 전/종료일 후 질문에서 해당 버전이 검색되지 않는다. |
| AC-NFR-009-01 | NFR-009 | 3D 캔버스는 자동 회전 없이 동작하고 키보드 node 선택과 동기화된 list/detail을 제공하며, Canvas 초기화 실패 시 목록 전환 경로를 표시한다. |

전체 story 수준 수용 기준은 `USER_STORIES.md`, 테스트 매핑은 `../05-delivery/TEST_PLAN.md`에서 관리한다.
