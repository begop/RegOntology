# Implementation Plan

상태: Baseline

## 현재 구현 스냅샷 — 2026-09-02

이 문서의 phase/task 전체를 완료로 간주하지 않는다. 현재 저장소는 기획을 검증하는 **Mock-first executable MVP**이며 다음 vertical slice를 구현한다.

- 구현·검증: 규정 Markdown seed/구조 조회, 기준일·ACL 필터, PostgreSQL/pgvector 정본 profile, 재구축 가능한 Neo4j projection과 bounded graph lane, hybrid retrieval, 근거 citation/검증/보류 QA, 규정·QA·Ontology UI(2D/3D/list), 감사·요청 ID, Docker Compose와 GHCR CI/CD
- 정적 데모: GitHub Pages/Sites UI는 embedded mock response만 사용하며 FastAPI·PostgreSQL·Neo4j의 원격 상태를 나타내지 않는다.
- 후속 구현 필요: 기관 OIDC/Keycloak login UI, 실제 파일 upload/object storage/malware scan, curator review·원자적 publication workflow, Celery ingestion worker, version diff·feedback·SSE conversation, OpenTelemetry/성능·복구 훈련
- 운영 금지: Phase 6 pilot readiness와 기관 보안·법무 승인이 끝나기 전에는 실제 규정 또는 production 서비스로 표시하지 않는다.

## 실행 원칙

- 한 번에 한 task를 구현하고 requirement/AC/test를 연결한다.
- 각 phase는 실행 가능한 vertical slice와 검증 gate로 끝난다.
- 구현 전에 관련 문서를 검토하고 충돌/누락을 먼저 수정한다.
- 외부 LLM 없이도 mock ingestion, auth, retrieval unit/integration test가 가능해야 한다.

## Phase 0 — Spec Review & Repository Foundation

목표: 문서 기준선을 검토하고 반복 가능한 개발환경을 만든다.

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-001 | 전체 spec/architecture/security review, conflict/open question 기록 | 전체 | review report와 승인된 문서 변경 |
| T-010 | monorepo skeleton: `frontend`, `backend`, `infra`, `tests` | NFR-011 | clean checkout bootstrap |
| T-020 | Python/Node package, lockfile, lint/type/test scripts | NFR-011 | local/CI 동일 명령 통과 |
| T-030 | Docker Compose: PostgreSQL+pgvector, Neo4j, Redis, Keycloak, object storage | NFR-008 | healthcheck와 smoke connection |
| T-040 | CI pipeline와 artifact/SBOM/secret scan | NFR-011 | sample PR gate 통과 |
| T-050 | typed settings, `.env.example`, secret policy | NFR-006 | missing/invalid config fail fast |

Gate P0: `lint + type + unit + compose smoke + secret scan` 통과.

## Phase 1 — Identity, Canonical Data, Regulation Read UI

목표: 인증된 사용자가 PostgreSQL 정본의 목업 규정을 탐색한다.

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-100 | FastAPI layered skeleton, error/request ID middleware | NFR-010 | OpenAPI + error contract tests |
| T-110 | OIDC token validation, role/scope policy engine | FR-017, NFR-001 | token/role matrix tests |
| T-120 | SQLAlchemy models/Alembic: document, version, provision, organization | FR-002, FR-003 | migration up/down on empty DB |
| T-130 | mock Markdown parser와 seed command | FR-001, FR-003 | expected provision counts/locators |
| T-140 | regulation list/detail/provision APIs | FR-010, FR-011 | ACL/as-of integration tests |
| T-150 | React app shell, OIDC, generated API client | FR-017 | login/logout/session expiry E2E |
| T-160 | regulation list/detail/TOC/deep link UI | FR-010, FR-011 | keyboard/responsive E2E |
| T-170 | audit event foundation | FR-016, NFR-005 | read/change event tests |

Gate P1: Restricted mock 문서 cross-role leak 0, stable locator deep link, as-of test 통과.

## Phase 2 — Ingestion, Version, Review, Publication

목표: Curator가 파일을 등록하고 검토된 snapshot을 publish한다.

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-200 | object storage upload/preflight/malware adapter | FR-001 | invalid/duplicate/oversize fixtures |
| T-210 | Celery job model, idempotency, retry/dead-letter | FR-018 | duplicate delivery 안전성 |
| T-220 | structure parser, issue model, source spans | FR-003, FR-004 | parser golden fixtures |
| T-230 | version date/exclusion constraints와 supersede flow | FR-002 | overlap rejected |
| T-240 | curator ingestion/parse review APIs/UI | FR-004 | correction/audit E2E |
| T-250 | publication manifest/state machine | FR-005 | failed build leaves active snapshot |
| T-260 | compare API/UI basic structural diff | FR-012 | added/removed/modified cases |

Gate P2: 새 mock version을 이전 active snapshot 손상 없이 publish/rollback할 수 있다.

## Phase 3 — Vector and Lexical Retrieval

목표: ACL/as-of aware hybrid text retrieval을 제공한다.

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-300 | structure-aware chunker와 chunk provenance | FR-006 | locator/context/hash tests |
| T-310 | embedding provider port + fake/reference adapters | FR-006, NFR-014 | contract tests, no-network fake |
| T-320 | pgvector schema/HNSW/index build/versioning | FR-006 | exact vs ANN recall benchmark |
| T-330 | lexical retriever(title/locator/trigram) | FR-007 | exact term/오타 cases |
| T-340 | vector retriever with prefilter/iterative fallback | FR-007, FR-017 | ACL/as-of candidate tests |
| T-350 | RRF fusion, trace schema, retrieval eval CLI | FR-007, FR-019, FR-020 | Recall@10 ≥ 0.90 |
| T-360 | search UI match snippet/lane-safe display | FR-011 | no restricted snippet leak |

Gate P3: Golden retrieval 목표와 security/temporal violation 0.

## Phase 4 — Ontology and Knowledge Graph

목표: 승인된 ontology를 projection하고 graph로 탐색한다.

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-400 | ontology schema/entity/assertion/provenance DB | FR-004, FR-014 | constraint tests |
| T-410 | deterministic extractor: refs/terms/thresholds | FR-014 | fixture precision tests |
| T-420 | LLM structured extraction adapter + fake | FR-014 | schema/injection/error tests |
| T-430 | proposal review API/UI | FR-004 | approve/edit/reject audit E2E |
| T-440 | Neo4j projection builder/watermark/validator | FR-005, FR-018 | rebuild/count/checksum |
| T-450 | bounded graph query templates/API | FR-013, FR-014 | depth/node/ACL tests |
| T-460 | Cytoscape 2D + Canvas2D 원근 투영 3D Ontology Explorer + list fallback | FR-013, NFR-009 | 결정적 projection unit, 2D/3D/list 상태 동기화와 accessibility component test |

Gate P4: seed ontology와 projection checksum 일치, Restricted derived node leak 0, viewer 200 node budget.

## Phase 5 — Grounded QA

목표: GraphRAG 답변이 citation 또는 abstention으로 종료된다.

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-500 | query analysis/entity linking | FR-014 | intent/entity eval |
| T-510 | graph retriever와 hybrid fusion integration | FR-007 | lane ablation과 multi-hop cases |
| T-520 | rerank/context packing/version consistency | FR-007, NFR-003 | context snapshot tests |
| T-530 | generation provider port, structured answer schema | FR-008, NFR-014 | fake/reference contract tests |
| T-540 | citation span/support/coverage verifier | FR-008, NFR-002 | unsupported claim blocked |
| T-550 | abstention/conflict/degraded policy | FR-009, NFR-008 | negative/chaos cases |
| T-560 | QA REST/SSE, conversation, trace, audit | FR-008, FR-016, FR-020 | disconnect/retry/idempotency |
| T-570 | chat/citation/detail/feedback UI | FR-010, FR-015 | keyboard and source navigation |
| T-580 | Golden QA harness와 metric report | FR-019 | 모든 project quality target |

Gate P5: citation/groundedness/abstention 목표 충족, security/as-of 위반 0.

## Phase 6 — Hardening and Pilot

| Task | 작업 | 연결 | 완료/검증 |
|---|---|---|---|
| T-600 | OpenTelemetry, dashboards, alerts, cost/latency metrics | NFR-010 | trace across API/job/provider |
| T-610 | rate/budget/upload/graph abuse limits | NFR-001, NFR-007 | abuse/load tests |
| T-620 | performance test at NFR-013 scale | NFR-007, NFR-013 | p95 target report |
| T-630 | backup/restore/projection rebuild drill | NFR-012 | RPO/RTO evidence |
| T-640 | dependency/container/IaC/security tests | NFR-011 | high/critical 0 or approved exception |
| T-650 | accessibility/cross-browser/responsive QA | NFR-009 | WCAG checklist |
| T-660 | operations runbook and release/rollback | NFR-008 | game-day exercise |
| T-670 | institution policy decisions and production review | OQ-003/007 등 | signed approvals |

Gate P6: pilot readiness review. Production은 별도 승인 전 활성화하지 않는다.

## 표준 검증 명령(구현 후 확정)

```text
make bootstrap
make lint
make typecheck
make test-unit
make test-integration
make test-e2e
make eval-smoke
make eval-full
make security-scan
make docs-check
```

실제 script가 만들어지면 `AGENTS.md`와 이 목록을 정확한 명령으로 갱신한다.

## 첫 Codex 구현 요청 템플릿

```text
Read AGENTS.md and the Phase 0 documents referenced there.
Do not implement yet.
Review T-001 through T-050 for missing requirements, conflicts, security risks,
and validation gaps. Update the planning documents first. Then propose a
small, traceable implementation plan for T-010 only, including files,
data flow, failure behavior, security impact, and validation commands.
```
