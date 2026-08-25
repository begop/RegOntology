# Deployment and Release Plan

상태: Baseline

## 환경

| 환경 | 데이터 | 목적 | 외부 모델 |
|---|---|---|---|
| Local | mock only | 개발 | fake 기본, 개인 opt-in reference |
| CI | generated/mock only | 자동 테스트 | fake only |
| Dev | mock/sanitized | 통합 | 승인된 dev project |
| Staging | production-like sanitized | 성능/UAT/보안 | production policy와 동일 |
| Production | 승인된 실제 규정 | 서비스 | 기관 승인 profile만 |

환경 간 DB dump 복사는 금지하고 승인된 export/import pipeline을 사용한다.

## Local profile

Docker Compose 서비스:

- frontend, api, worker
- PostgreSQL + pgvector
- Neo4j
- Redis
- Keycloak
- S3-compatible object storage 또는 local adapter
- optional OpenTelemetry Collector/Grafana

bootstrap은 mock regulations를 ingest하고 Golden QA smoke를 실행할 수 있어야 한다.

## Production reference

- Kubernetes 또는 기관 표준 orchestrator
- API/worker는 stateless image, non-root, read-only filesystem, resource limits
- PostgreSQL은 HA/PITR, encrypted storage, private network
- Neo4j는 운영 edition/HA/backup 또는 projection rebuild plan
- Redis broker는 HA와 persistence 정책을 queue 요구에 맞게 설정
- object storage versioning/immutability/malware scan
- ingress WAF/rate limit/TLS, IdP private integration
- secret manager와 workload identity

cloud vendor별 세부 서비스는 기관 환경 결정 후 adapter/ADR로 추가한다.

## CI/CD stages

1. docs/link/schema validation
2. lint/type/unit
3. integration with ephemeral data services
4. frontend component/E2E smoke
5. Golden QA smoke (fake provider deterministic)
6. dependency/secret/license/SBOM/container/IaC scan
7. signed immutable image/artifact publish
8. staging migration/deploy/smoke/full eval
9. 승인 후 production progressive rollout

## Configuration

- 12-factor env/secret injection과 typed validation
- 모델/provider/endpoint는 환경 설정, secret 값은 secret manager
- feature flag: graph lane, reference provider, streaming, compare 등
- config bundle version/hash를 release와 QA trace에 기록
- unsafe default: production에서 mock bypass/dev auth/fake approval 금지

## Database migration

- backward-compatible expand → migrate/backfill → contract 순서
- deployment 전에 backup/PITR 확인과 migration dry-run
- 장시간 index 생성은 concurrent/out-of-band job
- embedding dimension/model 변경은 새 column/table/profile로 병행 build 후 publication 전환
- Neo4j schema/projection은 PostgreSQL publication과 독립 staging 후 watermark 교체

## Release

1. release artifact와 migration/eval/security report 확정
2. active publication과 projection watermark 기록
3. staging full test와 운영 승인
4. API canary, error/latency/security metric 관찰
5. web rollout
6. worker rollout과 job drain 확인
7. release marker/audit event 생성

## Rollback

- application: 이전 immutable image로 롤백
- schema: destructive down migration보다 forward fix; expand/contract로 이전 app 호환 유지
- knowledge: 이전 active publication ID로 원자적 전환
- graph: 이전 watermark 사용 또는 PostgreSQL에서 rebuild
- model/prompt: 이전 config bundle로 전환

롤백 후 생성된 QA 응답에는 당시 사용한 release/config/publication이 그대로 보존된다.

## Backup/DR

- PostgreSQL PITR, 일일 full/주기 incremental; RPO 15분/RTO 4시간 목표
- object storage versioning과 cross-zone/approved region 복제
- Neo4j backup을 사용하더라도 PostgreSQL 기반 projection rebuild를 분기별 실증
- Redis cache는 복구 불필요, queue persistence는 job 상태 DB와 reconcile
- 분기별 restore drill과 evidence 보관

## Production gate

- Open Questions OQ-003, OQ-007 및 운영/보존/IdP 결정 완료
- security/penetration/privacy review
- load/DR/accessibility/eval 목표
- on-call/incident/rollback runbook과 담당자
- provider/data processing 계약과 region/retention 확인

