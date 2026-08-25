# Operations Runbook

상태: Baseline

## 관측 지표

### API/UX

- request rate/error/p50/p95/p99, auth/403/429
- QA time-to-first-event/complete, answered/partial/abstained
- citation verifier failure/retry
- citation open/feedback(비식별 집계)

### Retrieval/AI

- lane별 latency/candidate/timeout/empty
- graph degraded/stale watermark
- model/embedding request, token, estimated cost, rate limit
- Golden QA trend와 slice regression

### Data/Jobs

- queue depth/age/retry/dead-letter
- ingestion stage duration와 parser blocker
- embedding coverage와 index build
- publication state/watermark mismatch
- PostgreSQL connection/lock/storage/replication/PITR, Neo4j health

## Alert 초기 기준

| Alert | 조건 예 | 대응 |
|---|---|---|
| Publication mismatch | active ID ≠ graph/vector watermark 5분 | graph lane 비활성/빌드 조사 |
| QA false-output risk | verifier failure 급증 또는 violation 1건 | QA 중지/이전 config 전환 |
| Restricted access anomaly | deny/비정상 query 급증 | 보안 대응, token/scope 조사 |
| Queue stuck | oldest job > 15분 | worker/provider/lock 확인 |
| DB capacity | connection/storage/lag 임계 | scale/traffic 제한 |
| Provider failure | error/timeout budget 초과 | fallback/degraded/보류 전환 |

임계값은 pilot baseline 뒤 확정한다.

## 반복 작업

- 매일: failed jobs, watermark, backup 성공, provider budget
- 매주: feedback/abstention top cases, dead-letter triage, dependency alerts
- 매 release: full eval, SBOM/security, migration/rollback check
- 매월: access review, retention jobs, ANN exact recall comparison
- 분기: restore/projection rebuild drill, threat model/role review, Golden QA 업무 검토

## Runbook — Stale graph projection

1. active publication과 Neo4j watermark를 확인한다.
2. graph lane을 disabled/degraded로 표시한다.
3. build manifest, failed batch, node/edge count/checksum을 확인한다.
4. 동일 publication ID로 idempotent rebuild한다.
5. validation 후 watermark를 교체하고 smoke multi-hop QA를 실행한다.
6. incident/audit event와 원인을 기록한다.

## Runbook — 의심스러운 답변

1. query ID로 publication, model/config, retrieval/citation trace를 보존한다.
2. 권한과 source version/as-of를 확인한다.
3. claim-source verifier를 재실행하고 분류: retrieval, graph, generation, citation, data 오류.
4. 심각한 오답/노출이면 관련 config/publication 또는 QA를 비활성화한다.
5. Golden QA case와 회귀 test를 추가한다.
6. 업무/보안 책임자의 승인 후 재활성화한다.

## Runbook — Provider outage

1. network/credential/quota/region/status를 구분한다.
2. 제한된 retry가 storm을 만들지 않는지 확인한다.
3. 승인된 fallback profile이 있으면 정책/데이터 class를 확인 후 전환한다.
4. 없으면 원문 검색만 제공하고 QA는 `system_unavailable`로 보류한다.
5. 복구 후 queued background job을 rate-limited replay한다.

## Runbook — Access incident

1. 노출 가능성이 있는 token/session/service account를 폐기한다.
2. audit/query/retrieval IDs와 affected source scope를 보존한다.
3. 해당 document scope 또는 QA/export 기능을 fail closed한다.
4. 기관 incident process에 따라 보안/법무/준법에 보고한다.
5. policy/compiler/index/graph cache를 수정하고 cross-lane test 후 복구한다.

## 데이터 품질 운영

- publication마다 parser issue, source coverage, ontology review coverage를 보고한다.
- 낮은 confidence 제안은 QA에서 제외하고 review backlog로 보낸다.
- feedback은 원문 오류/검색 실패/답변 실패/UI 문제로 triage한다.
- 동일 질문을 FAQ로 고정 답변화하기 전에 source/version/owner 승인 체계를 만든다.

## Cost controls

- per-user/org rate와 daily token budget
- query/context/output token 상한
- embedding content hash reuse와 batch
- failed/retried provider 호출 계측
- 정확도 gate를 유지하는 범위에서 작은 모델 profile 비교
- 비용 초과 시 근거 없는 저품질 모델로 자동 하향하지 않고 명시적 제한/보류

