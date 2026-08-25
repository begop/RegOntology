# Security, Privacy, and AI Safety

상태: Baseline

이 문서는 설계 기준선이며 실제 기관의 보안성 심의, 개인정보 영향평가, 법무/준법 검토를 대체하지 않는다.

## 보호 자산

- Restricted 내부 규정과 공개 전 draft
- 사용자 identity, group, document scope
- 질문/대화/feedback의 업무 정보
- source files, parsed text, embeddings, ontology 관계
- provider credential, signing key, DB secret
- publication/approval/audit 무결성

## Trust boundaries

1. Browser ↔ Web/API
2. API ↔ IdP
3. API/Worker ↔ PostgreSQL/Neo4j/Redis/Object storage
4. API/Worker ↔ 외부 LLM/embedding provider
5. Curator upload ↔ parser/extractor
6. retrieved regulation text ↔ prompt instruction

## 역할/권한

- deny by default, least privilege
- 인증: OIDC access token의 issuer/audience/signature/expiry/nonce(or PKCE flow) 검증
- 인가: role + IdP group + document scope + security class + action
- API, lexical, vector, graph, citation, export, audit에 같은 정책 적용
- admin/curator/auditor 역할 분리와 중요 publication의 2-person approval은 production profile에서 요구
- service account는 사용자 role과 분리하고 짧은 수명 credential 사용

## 위협과 통제

| 위협 | 주요 통제 | 검증 |
|---|---|---|
| 권한 밖 규정 노출 | 후보 전 ACL, graph source inheritance, 존재 은닉 | cross-role integration tests |
| Prompt injection in regulation | 원문을 비신뢰 data delimiter로 격리, tool 없음/allowlist, output schema | malicious fixture eval |
| SQL/Cypher injection | ORM/parameter binding, approved query templates, 사용자 query 실행 금지 | SAST/negative tests |
| 잘못된/구버전 답변 | publication/as-of filter, citation verifier, abstention | temporal Golden QA |
| 자동 extraction 오염 | provenance, schema validation, human review, immutable source | review workflow tests |
| 악성 upload | MIME/size allowlist, malware scan, sandboxed parser, no macro execution | security fixtures |
| SSRF/외부 fetch | ingestion에서 임의 URL fetch 금지, egress allowlist | network policy tests |
| Credential 유출 | secret manager, redaction, rotation, no Git/log/prompt | secret scan |
| Audit tampering | append-only DB role, hash chain/WORM export option | integrity verification |
| DoS/cost abuse | request/token/file/node/depth limits, per-user rate limit, queue quota | load/abuse tests |
| Cross-snapshot 혼합 | publication/watermark consistency checks | chaos/integration tests |
| Sensitive provider transfer | classification gate, minimization, approved region/provider, opt-out profile | policy test/audit |

## AI-specific controls

- system prompt보다도 server-side data/permission control을 신뢰 경계로 사용한다.
- 모델은 SQL/Cypher, publication, 권한 변경 tool을 받지 않는다.
- context에는 허용된 최소 조문만 보내며 원본 전체 파일을 보내지 않는다.
- provider 요청/응답 본문 logging은 기본 off; 필요한 eval은 mock/sanitized dataset 사용.
- 모델이 생성한 citation/ID를 신뢰하지 않고 server allowlist와 verifier로 확인한다.
- raw chain-of-thought를 저장하거나 사용자/감사 UI에 노출하지 않는다.
- 외부 모델 사용이 승인되지 않은 classification은 호출 전에 차단한다.

## 데이터 분류와 처리

| Class | 예 | 외부 provider | 기본 UI |
|---|---|---|---|
| Public | 공개 가능한 규정 | 승인된 provider 가능 | 권한 사용자 |
| Internal | 일반 내부 규정 | 기관 정책 승인 시 최소 context | Employee scope |
| Restricted | 개인정보/보안/감사 민감 규정 | 기본 금지, 명시 승인 profile만 | 제한 group |

파생 embedding과 ontology는 source 이상의 분류를 상속한다. embedding이 원문을 완전히 익명화한다고 가정하지 않는다.

## Privacy/Retention

- 질문/대화는 업무 민감정보가 될 수 있어 최소 수집, 목적 제한, retention 설정, 사용자 고지를 적용한다.
- audit에는 질문 전문 대신 query ID/hash/category를 기본으로 저장하고 조사 권한 하에 별도 원문을 참조한다.
- IP/user-agent 등 telemetry는 필요한 범위만 저장한다.
- 삭제/보존/법적 보류 절차와 backup 만료를 함께 설계한다.
- mock 데이터 외 실제 개인정보는 개발/CI 환경에서 금지한다.

## Application security baseline

- HTTPS/HSTS, CSP, frame-ancestors, strict CORS allowlist
- CSRF 보호(BFF/cookie profile), XSS escaping/sanitization, safe Markdown renderer
- 파일 content-disposition와 sniffing 방지
- request body/timeouts/concurrency 제한
- error redaction과 correlation ID
- dependency lock/SBOM/CVE/license/secret/container/IaC scan
- protected branch, reviewed migration, signed build provenance

## Database security

- API/worker/migration/read-only/audit-export 역할과 credential 분리
- public schema create 권한 제거, network private access
- encryption at rest/in transit; backup 암호화
- PostgreSQL audit/slow query에 본문/embedding이 노출되지 않도록 parameter logging 정책
- Neo4j는 API/worker만 접근하고 read/write 계정 분리
- Redis는 private network, auth/TLS, eviction과 no-persistence/cache 정책을 역할에 맞게 구성

## Security test gate

- unauthenticated/expired/wrong audience token
- role 및 document scope matrix
- Restricted source의 vector/graph/citation side-channel
- prompt injection/jailbreak 규정 fixture
- SQL/Cypher/HTML/Markdown injection
- zip bomb/oversize/polyglot/path traversal upload
- rate limit/token budget/graph expansion abuse
- dependency/secret/container scan high/critical 0
- restore/DR과 audit hash verification

## Incident response

1. affected credential/provider/publication 격리
2. active publication을 이전 검증 snapshot으로 전환 또는 QA 중지
3. request/query/audit IDs로 영향 범위 파악
4. 규정에 따른 보고와 증거 보존
5. root cause, test/eval 추가, 재발 방지 후 재활성화

## Production 승인 체크

- 기관 data flow와 provider 계약/retention/region 승인
- IdP/role/scope mapping 승인
- threat model과 침투/보안 테스트 완료
- backup/restore/DR 실증
- audit/retention/legal hold 승인
- Golden QA와 false-answer/abstention risk sign-off
- 서비스 disclaimer와 담당 부서 escalation 경로 승인

