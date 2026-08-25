# Technology Stack

상태: Baseline

정확한 patch/minor 버전은 구현 시작 시 호환성 검증 후 lockfile로 고정한다. 여기서는 의도한 major line과 선택 이유를 정의한다.

## Frontend

| 영역 | 선택 | 이유 |
|---|---|---|
| Runtime/UI | React + TypeScript strict | 사용자 지정, typed component 생태계 |
| Build | Vite | 빠른 dev/test build, 단순 SPA 구성 |
| Routing | React Router | nested route, URL 기반 filter/deep link |
| Server state | TanStack Query | caching, retry, invalidation, async 상태 |
| Styling | Tailwind CSS + shadcn/ui | token 기반 구현과 접근 가능한 primitive |
| Graph | Cytoscape.js | interactive network visualization과 layout 확장 |
| Form | React Hook Form + Zod | 복잡한 ingestion form validation |
| Tests | Vitest, Testing Library, Playwright | unit/component/E2E 분리 |

## Backend

| 영역 | 선택 | 이유 |
|---|---|---|
| Language | Python 3.12+ | FastAPI/AI/Graph 생태계와 안정적 호환성 |
| API | FastAPI + Pydantic v2 | async typed API와 OpenAPI |
| ORM/DB | SQLAlchemy 2 + psycopg 3 + Alembic | transaction, async, migration |
| Jobs | Celery + Redis | ingestion/index/eval의 durable retry와 운영 성숙도 |
| Graph | Neo4j driver + `neo4j-graphrag` | Cypher와 공식 GraphRAG components; custom retriever 허용 |
| HTTP | httpx | provider 호출 timeout/connection pooling |
| Quality | pytest, pytest-asyncio, Testcontainers, Ruff, mypy | 빠른 검증과 실제 DB 통합 테스트 |

## Data

| 저장소 | 책임 | 기준 |
|---|---|---|
| PostgreSQL | canonical relational data와 audit | 지원되는 stable major |
| pgvector | embeddings와 similarity | HNSW cosine/inner-product, exact recall benchmark 병행 |
| Neo4j | graph projection | 공식 GraphRAG package 지원 범위 내 version |
| Redis | broker/cache/rate limit | 영구 데이터 금지 |
| Object storage | 원본 파일/대형 artifact | S3-compatible adapter, local은 MinIO 또는 filesystem profile |

## AI/Retrieval

### Reference profile

- Generation: OpenAI Responses API adapter
- 최초 accuracy baseline: `gpt-5.6`을 설정 기본 후보로 평가
- 비용/지연 비교: `gpt-5.6-terra` 등 더 작은 profile을 같은 Golden QA로 검증
- Embedding reference: `text-embedding-3-large`; dimension은 구현 benchmark와 pgvector index 제약을 확인해 1024 또는 지원 기본값으로 결정
- Reranker: 초기에는 provider-neutral cross-encoder adapter; Korean benchmark로 모델 확정
- 모델 ID, reasoning/config, prompt version을 코드에 고정하지 않고 실행 설정과 trace에 저장

운영에서 외부 provider를 사용하려면 데이터 분류, retention, region, 계약, 기관 보안 승인을 먼저 통과한다. 승인이 없으면 self-hosted adapter profile을 구현·평가한다.

### Retrieval implementation

- Lexical: PostgreSQL exact/title/locator + `pg_trgm` similarity
- Vector: pgvector HNSW
- Graph: 승인된 Cypher templates, 최대 hop/node 강제
- Fusion: Reciprocal Rank Fusion을 초기값으로 사용하고 eval로 weight 튜닝
- Rerank: top candidates에만 적용

한국어 lexical recall이 목표 미달이면 OpenSearch + Nori를 ADR로 추가하되 MVP 첫 구현에는 넣지 않는다.

## Identity/Security

- OIDC/OAuth 2.1, local Keycloak, production institution IdP
- JWT 검증은 issuer/audience/signature/expiry를 확인
- secrets는 secret manager/env injection, Git 저장 금지
- TLS, CSP, secure cookies(BFF/session profile 선택 시), rate limiting
- dependency/SBOM/license/secret/container scan

## Observability/Operations

- OpenTelemetry traces/metrics
- Prometheus + Grafana reference dashboards
- JSON structured logs, PII/redaction filter
- Sentry-compatible error adapter는 선택 사항
- Docker Compose local, Kubernetes production-neutral manifests/Helm은 delivery phase
- CI: lint → type → unit → integration → eval smoke → build/scan

## 선택하지 않은 대안

| 대안 | 보류 이유 |
|---|---|
| 별도 Pinecone/Qdrant | MVP에서 PostgreSQL metadata/ACL과 중복 운영 증가 |
| PostgreSQL만으로 graph | recursive query로 가능하나 ontology traversal/visualization/GraphRAG 운영성이 낮음 |
| Neo4j를 정본으로 사용 | 사용자 지정 PostgreSQL과 transaction/audit 정본 원칙에 부합하지 않음 |
| Microsoft GraphRAG 전체 pipeline | 규정 구조/실시간 publication/ACL에 맞춘 custom flow가 필요하고 storage contract가 과도함 |
| LangChain 전역 도입 | core domain이 framework에 결합되는 것을 피하고 필요한 adapter만 사용 |
| OpenSearch를 즉시 도입 | 목업 규모에서 운영 복잡도 대비 필요성이 아직 입증되지 않음 |

## 공식 참고

- OpenAI 모델 선택: <https://developers.openai.com/api/docs/guides/model-selection>
- OpenAI embedding model: <https://developers.openai.com/api/docs/models/text-embedding-3-large>
- pgvector: <https://github.com/pgvector/pgvector>
- Neo4j GraphRAG Python: <https://neo4j.com/docs/neo4j-graphrag-python/current/>
- Cytoscape.js: <https://js.cytoscape.org/>

