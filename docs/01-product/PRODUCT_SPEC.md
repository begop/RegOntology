# Product Specification

상태: Baseline

## 제품 원칙

1. **Evidence before eloquence**: 자연스러운 문장보다 정확한 근거를 우선한다.
2. **Version-aware by default**: 모든 검색과 답변은 `as_of`를 가진다.
3. **Human-reviewed knowledge**: publication 전 사람이 추출 결과를 승인한다.
4. **Least privilege everywhere**: 목록, vector, graph, citation 모두 동일 권한 경계를 적용한다.
5. **Explainable retrieval**: 어떤 규정과 관계가 답변에 사용됐는지 추적한다.
6. **Safe abstention**: 모르는 것을 그럴듯하게 채우지 않는다.

## 전역 상태 모델

### 규정 버전

`UPLOADED → PARSING → REVIEW_REQUIRED → ENRICHING → READY_TO_PUBLISH → PUBLISHED`

- 어떤 단계에서도 복구 가능한 `FAILED`로 전이할 수 있다.
- 새 버전이 유효해지면 기존 버전은 `SUPERSEDED`가 되지만 삭제하지 않는다.
- `PUBLISHED`만 일반 검색과 QA에 포함한다.

### QA 응답

- `answered`: 충분한 근거와 유효한 citation이 있음
- `partially_answered`: 일부만 근거가 있어 범위를 명확히 제한함
- `abstained`: `insufficient_evidence`, `access_limited`, `ambiguous_question`, `system_unavailable` 중 하나

## Feature 1 — Regulation Library

### 목적

유효 규정과 버전을 검색하고 원문 구조를 탐색한다.

### 입력/필터

- 검색어, 문서 유형, 소유 부서, 상태, 보안등급
- 기준일 `as_of` (기본 오늘)
- 태그/ontology concept

### 결과

- 문서명, 현재 버전, 시행 기간, 소유 부서, 상태, 보안등급
- 일치한 조문 snippet과 locator

### 실패/빈 상태

- 결과 없음: 필터 초기화 및 다른 용어 안내
- 권한 제한: 존재 여부를 추론할 수 있는 문서 메타데이터도 노출하지 않음

## Feature 2 — Regulation Detail & Version Compare

- 좌측 조문 목차, 중앙 원문, 우측 metadata/관계/citation panel
- 영구 URL: `/regulations/{documentId}/versions/{versionId}?locator=...`
- 이전/다음 버전 및 효력 기간 표시
- compare는 조문 stable key 기준 added/removed/modified를 표시하며 의미적 판단을 자동 확정하지 않음

## Feature 3 — Grounded QA Chat

### 입력

- 질문, `as_of`, 선택적 document/department scope
- 대화 내 후속 질문은 이전 질문을 참조하되 매 turn 검색을 다시 수행

### 답변 카드

- 상태 badge, 짧은 결론, 근거 기반 설명
- 적용 기준일과 사용한 규정 버전
- `[1]`, `[2]` citation list: 문서명, 버전, locator, 짧은 인용
- 관련 규정/ontology 탐색 링크
- 주의 문구와 담당 부서 확인 권고
- feedback control

### 생성 계약

- context 밖 사실을 규정 사실처럼 진술하지 않는다.
- citation은 source chunk ID가 아니라 사용자 이해 가능한 조문 locator로 표시한다.
- 상충 근거가 있으면 하나를 고르지 말고 충돌과 버전을 설명한다.
- 질문이 모호하면 가능한 해석을 짧게 제시하고 필요한 정보를 요청한다.

## Feature 4 — Ontology Explorer

### 구성

- 검색/필터 bar: node type, 규정, 부서, 효력일
- graph canvas: node/edge type별 시각 인코딩
- detail drawer: 정의, 관계, 관련 조문, provenance, 검토 상태
- path panel: 두 node 사이 제한 길이 경로
- list/table 대체 뷰

### 상호작용

- 초기에는 검색 결과 중심 최대 50 node
- 1-hop 확장, 최대 200 node/session view
- 의무/금지/예외 edge를 구분
- node에서 근거 조문으로 이동
- layout/zoom/filter는 URL 또는 session state로 복원

## Feature 5 — Ingestion & Review

1. 파일과 metadata 등록
2. checksum/중복/형식 검사
3. 조문 파싱 preview와 오류 목록
4. chunk preview
5. ontology entity/relation 제안 검토
6. embedding/index/graph dry-run validation
7. 승인 및 publication

모든 단계는 job ID, actor, tool/model version, outcome을 기록한다. Curator는 원문을 바꾸는 대신 파싱 locator와 ontology annotation을 수정한다.

## Feature 6 — Audit & Evaluation

- 감사자는 기간/actor/action/target/outcome으로 audit event 검색
- 관리자는 index build, projection watermark, 실패 queue를 확인
- evaluator는 Golden QA suite를 실행하고 baseline과 비교
- raw chain-of-thought는 저장/노출하지 않으며 구조화 retrieval/citation trace만 보존

## 역할과 권한

| 행위 | Employee | Compliance | Curator | Auditor | Admin |
|---|:---:|:---:|:---:|:---:|:---:|
| 허용 문서 검색/QA | ✓ | ✓ | ✓ | ✓ | ✓ |
| Ontology 탐색 | ✓ | ✓ | ✓ | ✓ | ✓ |
| Restricted 업무 scope |  | 조건부 | 조건부 | 조건부 | 설정 |
| Ingestion/review |  | 조회 | ✓ | 조회 | ✓ |
| Publish |  | 승인 옵션 | ✓ | 조회 | ✓ |
| Audit 조회 | 본인 일부 | 업무 범위 | 업무 범위 | ✓ | ✓ |
| 권한/provider 설정 |  |  |  | 조회 | ✓ |

실제 권한은 IdP group과 document scope의 교집합이다.

## Analytics

- 질문 수, answered/abstained 비율, citation open rate
- feedback 분포와 문제 유형
- 검색 lane별 Recall/MRR, latency, 비용
- 문서별 질문 coverage와 low-confidence topic
- ingestion lead time과 review backlog

질문 본문 analytics는 별도 동의/정책에 따라 비식별화하거나 저장하지 않을 수 있다.

