# API Specification

상태: Baseline  
Base path: `/api/v1`  
Format: JSON, UTF-8; QA streaming은 SSE

구현 시 FastAPI OpenAPI를 생성하고 frontend type을 자동 생성한다. 이 문서는 행동 계약의 정본이다.

## 공통 계약

### 인증

`Authorization: Bearer <OIDC access token>`. API는 issuer, audience, signature, expiry를 검증한다. 인증 실패는 401, 권한 부족은 리소스 존재 여부를 노출하지 않는 403/404 정책을 endpoint별로 적용한다.

### Headers

- 요청: `X-Request-ID` 선택; 없으면 서버 생성
- 응답: `X-Request-ID`, `X-Publication-ID`, graph 사용 시 `X-Graph-Watermark`
- 변경 요청: `Idempotency-Key` 필수인 endpoint를 명시

### Error envelope

```json
{
  "error": {
    "code": "validation_error",
    "message": "요청을 처리할 수 없습니다.",
    "request_id": "...",
    "details": [{"field": "as_of", "reason": "invalid_date"}]
  }
}
```

내부 stack, SQL/Cypher, provider 원문 오류, 권한 대상명은 노출하지 않는다.

### Pagination

목록은 cursor 기반: `limit` 기본 20, 최대 100, `next_cursor`. cursor는 opaque signed value다.

## Health

| Method/Path | 설명 | Auth |
|---|---|---|
| `GET /api/v1/health` | canonical store와 graph projection 상태. Graph만 장애/stale이면 HTTP 200 + `status=degraded`, `graph_status` 표시 | 무인증 최소정보 |
| `GET /health/live` | process liveness | 내부/무인증 최소정보 |
| `GET /health/ready` | PostgreSQL readiness. Graph 장애는 서비스 가능 상태로 `degraded` 표시 | 내부 |
| `GET /system/status` | publication/projection/provider degraded 상태 | Admin |

`graph_status`는 `healthy`, `stale`, `unavailable` 중 하나다. Graph 장애는 PostgreSQL
정본을 요구하는 API 전체를 중단시키지 않으며 QA는 graph lane을 제외하고 품질 기준을 다시
적용한다.

## Regulation

### `GET /regulations`

Query: `q`, `as_of`, `owner_org`, `document_type`, `security_class`, `status`, `cursor`, `limit`.

Response item: document ID/code/title, effective version summary, owner, class, match snippets. ACL과 `as_of`는 후보 생성 전에 적용한다.

### `GET /regulations/{document_id}`

문서 metadata와 현재/허용 version 목록. 권한 밖이면 존재 여부를 숨긴다.

### `GET /regulations/{document_id}/versions/{version_id}`

version metadata와 top-level TOC.

### `GET /regulations/{document_id}/versions/{version_id}/provisions`

Query: `parent_id`, `locator`, `depth`, `cursor`. 최대 depth와 page size 강제.

### `GET /provisions/{provision_id}`

조문 원문, hierarchy breadcrumb, version/effective metadata, 허용된 ontology link를 반환한다.

### `GET /regulations/{document_id}/compare`

Query: `from_version_id`, `to_version_id`, optional `locator`. 구조 diff를 반환하며 자동 의미 판정은 반환하지 않는다.

## QA

### `POST /qa/queries`

```json
{
  "question": "중요정보시스템 접근권한은 얼마나 자주 검토해야 하나요?",
  "as_of": "2026-08-24",
  "scope": {"document_ids": [], "owner_org_ids": []},
  "conversation_id": null,
  "stream": false
}
```

동기 응답:

```json
{
  "query_id": "uuid",
  "status": "answered",
  "answer": "...",
  "as_of": "2026-08-24",
  "citations": [
    {
      "index": 1,
      "document_id": "uuid",
      "version_id": "uuid",
      "provision_id": "uuid",
      "document_title": "정보보호 운영규정",
      "version_label": "1.0",
      "locator": "제5조 제2항",
      "quote": "..."
    }
  ],
  "warnings": ["mock_data"],
  "trace": {"publication_id": "uuid", "graph_mode": "healthy"}
}
```

`status`: `answered`, `partially_answered`, `abstained`. Abstained 응답은 `reason_code`와 `suggested_actions`를 가진다.

### `POST /qa/queries:stream`

SSE event: `accepted`, `retrieval_started`, `sources_ready`, `answer_delta`, `citation`, `completed`, `error`. `answer_delta`를 받았더라도 `completed` 전까지 검증 완료 답변으로 취급하지 않으며 UI는 provisional 상태를 표시한다.

### `GET /qa/queries/{query_id}`

본인 또는 허용 역할만 구조화 결과 조회. 결과와 소유권은 PostgreSQL 정본에 저장되므로 API
재시작과 다중 인스턴스 간에도 유지된다. 조회 시 현재 principal의 document scope와 citation
source 무결성을 다시 검사하며, 권한 밖이거나 source가 현재 허용 snapshot에 없으면 404로 숨긴다.

### `GET /qa/queries/{query_id}/trace`

권한에 따라 lane, source, rank, selected path의 요약을 반환한다. prompt secret, raw chain-of-thought, 권한 밖 source는 제외한다.

### `POST /qa/queries/{query_id}/feedback`

`rating: helpful|not_helpful`, `reason_codes`, optional sanitized comment. Idempotency key 사용.

## Ontology

### `GET /ontology/search`

Query: `q`, `types`, `as_of`, `document_ids`, `limit`. 승인된 entity만 반환.

### `GET /ontology/subgraph`

Query: `seed_ids`, `relation_types`, `depth`(1–2), `max_nodes`(≤200), `as_of`. Response: nodes, edges, truncation flag, expansion cursor, publication/watermark.

### `GET /ontology/nodes/{node_id}`

properties, provenance, related provisions, review status.

### `GET /ontology/paths`

Query: `from_id`, `to_id`, `max_depth`(≤4), allowed relation list. 모든 path는 ACL filter 후 반환한다.

사용자 제공 Cypher endpoint는 없다.

## Ingestion/Admin

| Method/Path | 행동 | Role |
|---|---|---|
| `POST /admin/ingestions` | metadata 등록, upload URL/job 생성 | Curator |
| `POST /admin/ingestions/{id}/complete-upload` | checksum/format preflight | Curator |
| `POST /admin/ingestions/{id}/parse` | parse job 시작 | Curator |
| `GET /admin/ingestions/{id}` | 상태/issue/preview | Curator |
| `PATCH /admin/provisions/{id}` | parsed locator correction | Curator |
| `GET /admin/ontology/proposals` | 제안 목록 | Curator |
| `PATCH /admin/ontology/proposals/{id}` | 수정/승인/반려 | Curator |
| `POST /admin/publications` | validation/build 시작 | Curator/Admin |
| `POST /admin/publications/{id}/activate` | 원자적 activation | 승인 역할 |
| `POST /admin/jobs/{id}/retry` | retryable 실패 재시도 | Admin |

파일 upload는 MIME/크기/확장자/악성코드 검사를 통과해야 하며 API process가 대형 파일을 직접 메모리에 보관하지 않는다.

## Audit/Evaluation

- `GET /admin/audit-events`: 기간/actor/action/target/outcome filter, Auditor/Admin
- `POST /admin/evaluations`: dataset/snapshot/config로 run 시작
- `GET /admin/evaluations/{id}`: metrics, baseline delta, failed cases
- `GET /admin/evaluations/{id}/artifact`: 권한 있는 signed artifact download

## Status code

| Code | 사용 |
|---|---|
| 200/201/202 | 조회/생성/비동기 접수 |
| 400 | malformed/business validation |
| 401 | 인증 실패 |
| 403 | 행위 권한 부족(존재 공개가 안전한 admin resource) |
| 404 | 없음 또는 존재 은닉 |
| 409 | version/publication 상태 충돌, duplicate checksum |
| 413/415 | 파일 크기/형식 오류 |
| 422 | field validation |
| 429 | rate limit |
| 503 | 필수 dependency 불가; retry hint 포함 |

QA의 근거 부족은 transport error가 아니므로 200 + `abstained`를 사용한다.
