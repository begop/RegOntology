# Architecture Decision Log

상태: Baseline

## ADR-001 — PostgreSQL을 정본으로 사용

- 결정: 문서/버전/조문/청크/임베딩 메타데이터/권한/대화/감사 로그의 canonical store는 PostgreSQL이다.
- 이유: 사용자가 지정한 DB이며 transaction, constraint, migration, audit, backup 운영을 한 곳에서 일관되게 관리할 수 있다.
- 결과: 그래프 저장소 장애 시에도 원문과 publication 상태는 보존되며 projection을 재생성할 수 있다.

## ADR-002 — pgvector를 Vector DB 계층으로 사용

- 결정: 별도 managed vector DB 대신 PostgreSQL의 `pgvector`와 HNSW index를 사용한다.
- 이유: ACL, 문서 버전, 효력일 필터와 vector 검색을 같은 SQL transaction/metadata model에서 수행해 데이터 경계를 단순화한다.
- 결과: 규모/지연/recall이 목표를 넘지 못하면 평가 근거를 갖춘 뒤 별도 vector engine을 재검토한다.

## ADR-003 — Neo4j를 재구축 가능한 graph projection으로 사용

- 결정: ontology instance와 관계 탐색은 Neo4j에 projection한다.
- 이유: 다중 hop 관계 탐색, Cypher query, graph visualization payload 구성과 GraphRAG 생태계가 적합하다.
- 결과: projection watermark와 PostgreSQL source revision을 모든 graph query 결과에 포함한다.

## ADR-004 — 구조 보존 chunking

- 결정: 고정 토큰 길이만으로 자르지 않고 조/항/호를 기본 단위로 하며, 긴 단위만 child chunk로 분할한다.
- 이유: 규정 QA는 의미뿐 아니라 정확한 locator와 예외/단서 문맥이 중요하다.
- 결과: 모든 chunk는 `article_path`, `parent_text`, `effective_period`, `source_checksum`을 가진다.

## ADR-005 — Hybrid GraphRAG

- 결정: lexical + pgvector + graph expansion을 병렬 수행하고 RRF/가중 결합, rerank, context packing을 거친다.
- 이유: 조문 번호/고유 용어에는 lexical, 표현 변형에는 vector, 예외/책임/연결 규정에는 graph가 서로 보완적이다.
- 결과: 각 검색 lane의 후보와 score를 trace로 보존한다.

## ADR-006 — 모델/임베딩 provider adapter

- 결정: OpenAI를 초기 reference provider로 쓰되 도메인 port 뒤에 둔다. 모델 ID는 환경 설정과 실행 기록에 저장한다.
- 이유: 금융기관별 외부 전송 정책과 모델 교체 요구를 수용해야 한다.
- 결과: 외부 provider 전송 전 데이터 분류/최소화 정책을 적용하고, 운영 활성화는 기관 승인을 요구한다.

## ADR-007 — 모델 선택은 eval-first

- 결정: 초기 품질 기준선은 설정된 최고 정확도 profile로 만들고 Golden QA 목표 달성 후 더 빠르고 저렴한 profile을 비교한다.
- 이유: 정확도·citation·abstention이 비용 최적화보다 우선이다.
- 결과: 모델 교체는 동일 eval set, 고정 retrieval snapshot, 기록된 비용/지연으로 비교한다.

## ADR-008 — OIDC와 애플리케이션 RBAC

- 결정: 인증은 OIDC 기관 IdP, 권한은 API에서 role + document scope로 강제한다.
- 이유: 기관 IAM 통합과 세밀한 규정 접근 제어를 분리한다.
- 결과: UI 숨김은 보안 통제가 아니며 모든 검색 lane과 상세 조회에서 동일 ACL predicate를 사용한다.

## ADR-009 — Publication 전에 Human Review

- 결정: 파싱/ontology extraction/임베딩/graph projection 산출물은 curator 승인 후 공개한다.
- 이유: 규정 의미와 예외 관계의 자동 추출 오류가 잘못된 답변을 유발할 수 있다.
- 결과: bulk approve는 validation error가 0인 batch에만 허용하고 승인자를 감사 기록한다.

## ADR-010 — Ontology viewer는 Cytoscape.js

- 결정: React UI의 그래프 탐색은 Cytoscape.js를 사용한다.
- 이유: 브라우저 기반 interactive graph, layout/selection/style 확장성이 필요하다.
- 결과: 대규모 graph 전체 전송을 금지하고 server-side bounded subgraph API를 사용한다.

## ADR-011 — 실행 프로필별 데모 fallback 분리

- 결정: Docker/GHCR Web 빌드는 `VITE_DEMO_MODE=false`로 고정해 FastAPI 오류를 숨기지 않는다. API가 없는 GitHub Pages/Sites 목업 UI만 `VITE_DEMO_MODE=true`를 사용한다.
- 이유: 공개 UI 미리보기의 편의성과 실제 full-stack 장애 가시성을 같은 빌드에서 동시에 만족시킬 수 없다.
- 결과: 공개 정적 URL은 **Mock UI 검증용**으로 표시하며, PostgreSQL/pgvector/Neo4j 통합은 Docker Compose와 CI smoke test로 별도 검증한다.

## ADR-012 — MVP UI styling 예외

- 결정: 초기 실행 가능 MVP는 Tailwind CSS와 shadcn/ui 대신 소규모 typed React primitive와 repository-local CSS를 사용한다.
- 이유: 현재 화면 수에서 추가 생성·빌드 의존성 없이 접근성, 반응형 layout, dark theme를 재현 가능하게 고정하는 편이 빠른 검증에 유리하다.
- 결과: 이는 승인 기술 기준선의 명시적 MVP 예외다. 기관 디자인 시스템 통합 또는 공용 component library 확장 시 Tailwind/shadcn 도입 여부를 다시 결정하고 lockfile, 시각 회귀, 접근성 테스트를 함께 갱신한다.

## 근거 자료

- OpenAI 공식 문서는 모델 선택 시 정확도 목표와 평가 데이터셋을 먼저 정하고 이후 비용/지연을 최적화하도록 설명한다: <https://developers.openai.com/api/docs/guides/model-selection>
- pgvector 공식 저장소는 exact search와 HNSW/IVFFlat approximate index를 제공한다: <https://github.com/pgvector/pgvector>
- Neo4j의 공식 GraphRAG Python 문서: <https://neo4j.com/docs/neo4j-graphrag-python/current/>
- Cytoscape.js 공식 문서: <https://js.cytoscape.org/>
