# Open Questions and Assumptions

상태: Baseline

사용자가 자동 진행을 선호하므로 MVP 설계에 필요한 기본값은 결정했다. 아래 항목은 개발을 막지 않지만 실제 기관 적용 전 반드시 확정해야 한다.

| ID | 항목 | 현재 기본값 | 확정 시점/책임 |
|---|---|---|---|
| OQ-001 | 배포 위치 | local Docker Compose + cloud-neutral Kubernetes 설계 | 운영 설계 전 / IT 운영 |
| OQ-002 | 기관 IdP | local Keycloak, 운영 OIDC-compatible IdP | 통합 테스트 전 / IAM |
| OQ-003 | 외부 LLM 전송 허용 | mock/public 등급만 reference provider 전송 | 실데이터 PoC 전 / 보안·준법 |
| OQ-004 | 원본 형식 | MVP Markdown + text PDF, OCR은 후속 | 실제 자료 inventory 후 / 업무 |
| OQ-005 | 한국어 lexical search | MVP PostgreSQL trigram; 품질 미달 시 OpenSearch/Nori 평가 | retrieval benchmark 후 / Data |
| OQ-006 | 보존 기간 | audit 7년, 대화 1년을 초기 가정 | 운영 승인 전 / 법무·보안 |
| OQ-007 | 규정 분류/보안등급 | Public/Internal/Restricted 3단계 | ingestion UAT 전 / 정보보호 |
| OQ-008 | Neo4j 배포/라이선스 | 개발 Community, 운영 edition은 조달 검토 | production design 전 / 조달 |
| OQ-009 | SLA | MVP 목표만 적용, 운영 SLA 별도 계약 | pilot 종료 전 / 서비스 오너 |
| OQ-010 | 법령/외부 규정 포함 | MVP 내부 규정만 | phase 2 scope / 준법 |

## 확인이 필요한 가장 중요한 결정

실제 규정 투입 전에는 `OQ-003`(외부 모델 전송)과 `OQ-007`(문서 보안등급)을 먼저 닫아야 한다. 이 둘이 확정되지 않으면 실데이터 ingestion과 운영 QA를 시작하지 않는다.

