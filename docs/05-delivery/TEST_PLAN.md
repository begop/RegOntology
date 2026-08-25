# Test and Evaluation Plan

상태: Baseline

## 전략

테스트 피라미드에 retrieval/LLM eval을 별도 품질 계층으로 추가한다.

| 계층 | 대상 | 도구/방식 |
|---|---|---|
| Static | format, lint, type, schema | Ruff, mypy, ESLint, TypeScript, JSON schema |
| Unit | domain policy, parser, chunker, fusion, verifier | pytest/Vitest, pure fakes |
| Contract | repositories, provider adapters, OpenAPI | pytest, fake server, schema snapshots |
| Integration | PostgreSQL/pgvector/Neo4j/Redis/Keycloak | Testcontainers/Compose |
| Component | React states/accessibility | Testing Library, axe |
| E2E | persona workflow | Playwright |
| Eval | retrieval/graph/answer/citation/abstention | Golden QA harness |
| Nonfunctional | load, chaos, security, backup | k6/Locust, failure injection, scanners |

## 테스트 데이터

- 기본은 `mock-data/`만 사용한다.
- random data는 seed를 기록한다.
- provider test는 기본 fake adapter, 명시적 opt-in에서만 reference API를 호출한다.
- Golden QA 변경은 실패 case 해결을 숨기지 않도록 reviewer 승인과 변경 사유를 요구한다.

## 요구사항 추적

| Requirement | 핵심 test suite |
|---|---|
| FR-001~005 | ingestion preflight/parser/review/publication integration + E2E |
| FR-006~007 | chunk/embedding/index/fusion unit + retrieval eval |
| FR-008~010 | QA schema/citation/verifier/abstention + chat E2E |
| FR-011~012 | regulation API/UI/as-of/diff tests |
| FR-013~014 | ontology constraints/projection/query/viewer tests |
| FR-015~016 | feedback/audit authorization and retention tests |
| FR-017 | token/role/document scope matrix across every lane |
| FR-018 | job idempotency/retry/watermark/rebuild/chaos |
| FR-019~020 | eval reproducibility and trace redaction |
| NFR-001~006 | negative security, temporal, provenance, audit/privacy tests |
| NFR-007~015 | performance, accessibility, observability, supply chain, DR, portability |

## Parser golden tests

각 mock regulation에 expected:

- document/version metadata
- level별 provision count와 canonical path/locator
- source span/body hash
- cross-reference와 threshold 후보
- invalid fixtures의 blocker/warning

원문 whitespace 차이가 locator/body 의미를 바꾸지 않는지 검증한다.

## Retrieval evaluation

### Metric

- Recall@5, Recall@10, MRR, nDCG@10
- lane별/융합 결과와 ablation
- ACL/temporal violation count
- ANN recall vs exact pgvector baseline

### Gate

- 전체 Recall@10 ≥ 0.90
- `direct`, `exception`, `multi_hop`, `temporal` 중요 slice 각각 ≥ 0.85
- ACL/temporal violation = 0
- baseline보다 3%p 이상 하락한 slice는 blocker(업무 승인 예외 제외)

## Answer/Citation evaluation

### 자동 + 업무 rubric

- 정확성: 허용 근거와 모순 없음
- 완전성: 질문의 필수 요소(주체/행위/조건/예외/시점) 포함
- groundedness: 모든 규정 사실이 source로 지지됨
- citation precision/completeness/locator accuracy
- abstention correctness와 false-answer rate
- 표현: 법적 최종 판단처럼 과장하지 않음

### Gate

- Citation precision ≥ 0.98
- Citation completeness ≥ 0.95
- Answerable grounded pass ≥ 0.90
- Unanswerable abstention ≥ 0.95
- wrong-version/unauthorized citation = 0

## Security negative matrix

1. 무토큰/만료/잘못된 issuer/audience/signature
2. Employee가 Restricted 문서를 title/검색 count/vector/graph/citation으로 추론
3. 규정 본문에 “이전 지시 무시” 등 prompt injection
4. 질문/metadata의 SQL, Cypher, HTML, Markdown injection
5. oversize/zip bomb/path traversal/polyglot upload
6. graph depth/node 폭발, 장문 질문/token/cost abuse
7. provider timeout/partial response/malformed structured output
8. publication race와 stale watermark
9. retired publication의 version/chunk가 hydration 또는 vector 후보에 섞이지 않는지 검증
10. QA 생성 인스턴스와 조회 인스턴스를 분리하고 재시작 후 owner/auditor/document ACL 검증

## Failure/Chaos tests

| 실패 | 기대 |
|---|---|
| Neo4j down | 명시적 degraded vector+lexical 또는 abstention |
| Redis down | 새 job 접수 제한, read 유지 |
| provider timeout | 제한 retry 후 보류, request thread 고갈 없음 |
| embedding dimension mismatch | publication blocker |
| partial projection | active watermark 변경 없음 |
| PostgreSQL failover | transaction rollback, idempotent retry |
| SSE disconnect | generation cancel/budget 정책, 중복 message 없음 |

MVP 자동 회귀는 restricted document/forged Neo4j row 차단, effective-version locator가 없는
ontology assertion 제외, `as_of` 이전 edge 제외, fixed parameter Cypher와 node/edge budget,
Neo4j outage의 vector+lexical fallback 및 5초 Compose probe 미만 timeout, projection 단일
transaction rollback 계약을 포함한다.

## Performance profile

- 10,000 regulation versions, 300,000 chunks, graph 규모는 seed를 비례 확장
- 50 concurrent QA users, read-heavy 200 concurrent sessions 보조 시험
- 일반 API p50/p95/p99, retrieval lane, first SSE event, complete answer, DB saturation 측정
- warm/cold cache를 분리하고 모델 provider latency도 별도 보고

## Accessibility/E2E

- keyboard-only: 로그인, 검색, 질문, citation, graph list, curator review
- screen reader semantics와 live status
- 200% zoom/320px width, light/dark, reduced motion
- Chromium/Firefox/WebKit latest supported CI profile

## Release report

각 release candidate는 다음 artifact를 남긴다.

- source commit/image digest/SBOM
- schema migration result
- unit/integration/E2E summary
- Golden QA dataset hash와 metric/baseline diff
- security/accessibility/performance/DR 결과
- 승인된 예외와 만료일
