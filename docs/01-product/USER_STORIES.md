# User Stories

상태: Baseline

## 일반 임직원

### US-QA-01 — 규정 질문

사용자로서 업무 질문을 자연어로 입력하여 현재 유효한 규정 근거와 함께 답을 받고 싶다.

- AC: 답변에는 `as_of`, 규정 버전, 조문 citation이 표시된다.
- AC: citation을 선택하면 정확한 조문 위치로 이동한다.
- AC: 답변 범위가 참고용임을 알 수 있다.
- 연결: FR-008, FR-010, NFR-002, NFR-003

### US-QA-02 — 답변 불가 확인

사용자로서 규정에 없는 내용을 질문했을 때 지어낸 답 대신 부족한 근거와 다음 행동을 알고 싶다.

- AC: `abstained` 상태와 이유 code가 표시된다.
- AC: 담당 부서 문의 또는 질문 구체화 안내가 제공된다.
- 연결: FR-009

### US-LIB-01 — 기준일 규정 탐색

사용자로서 과거 특정일에 유효했던 규정과 조문을 찾고 싶다.

- AC: `as_of` 변경 시 결과와 version badge가 함께 갱신된다.
- AC: 유효하지 않은 버전은 기본 결과에 섞이지 않는다.
- 연결: FR-002, FR-011, NFR-003

## 준법/내부통제 담당자

### US-GRAPH-01 — 책임과 통제 관계 탐색

준법 담당자로서 특정 의무가 어느 조직·통제·시스템과 연결되는지 graph로 보고 싶다.

- AC: node/edge 유형과 관련 조문을 확인할 수 있다.
- AC: 동일한 필터·선택 상태에서 2D 그래프, 3D 입체 캔버스, 접근 가능한 목록을 전환할 수 있다.
- AC: 확장 수와 hop에 제한이 있으며 path가 설명된다.
- 연결: FR-013, FR-014

### US-COMPARE-01 — 버전 변경 비교

준법 담당자로서 두 버전의 변경 조문을 비교하여 검토 대상을 좁히고 싶다.

- AC: 추가/삭제/수정이 locator별로 표시된다.
- AC: 자동 diff는 법적 영향 판단이 아님을 명시한다.
- 연결: FR-012

## Curator

### US-ING-01 — 규정 등록

Curator로서 파일과 metadata를 등록하고 구조 파싱 결과를 검토하고 싶다.

- AC: checksum 중복과 날짜 오류를 publication 전에 알린다.
- AC: source 원문과 parsed 조문을 나란히 비교할 수 있다.
- 연결: FR-001, FR-003, FR-004

### US-ING-02 — Ontology 검토

Curator로서 자동 제안된 entity와 relation의 근거를 확인하고 수정·승인하고 싶다.

- AC: 모든 제안은 source locator와 confidence를 가진다.
- AC: 수정 전/후와 reviewer가 감사 로그에 남는다.
- 연결: FR-004, NFR-005

### US-PUB-01 — 안전한 publication

Curator로서 validation을 통과한 snapshot만 사용자에게 공개하고 싶다.

- AC: index/graph build 하나라도 실패하면 active snapshot은 바뀌지 않는다.
- AC: 성공하면 동일 publication ID가 PostgreSQL, vector, graph watermark에 반영된다.
- 연결: FR-005, FR-018

## 감사자와 관리자

### US-AUD-01 — 답변 재현

감사자로서 특정 답변이 어떤 사용자·모델·prompt·검색 후보·규정 snapshot으로 생성되었는지 확인하고 싶다.

- AC: 민감 원문 권한을 존중하면서 구조화 trace를 조회한다.
- AC: raw 모델 내부 추론은 저장하지 않는다.
- 연결: FR-016, FR-020, NFR-004, NFR-005

### US-EVAL-01 — 품질 회귀 확인

관리자로서 변경 전후 Golden QA 결과를 비교해 안전하게 release하고 싶다.

- AC: 동일 dataset/snapshot/config를 고정해 비교한다.
- AC: gate 미달이면 CI/release가 실패한다.
- 연결: FR-019

### US-OPS-01 — projection 복구

관리자로서 Neo4j가 손상되거나 지연될 때 PostgreSQL 정본에서 projection을 재구축하고 싶다.

- AC: rebuild가 진행되는 동안 기존 watermark 또는 명시적 degraded mode를 사용한다.
- AC: rebuild 결과 node/edge count와 checksum을 검증한다.
- 연결: FR-018, NFR-008, NFR-012
