# Documentation Guide

## 목적

이 저장소는 Markdown 문서를 사람용 기획서이자 Codex가 지속적으로 읽는 Project Knowledge Base로 사용한다. `AGENTS.md`는 짧은 인덱스와 불변 규칙만 보유하고, 상세 사실은 목적별 문서에 한 번만 정의한다.

## 문서 계층

| 경로 | 책임 | 주요 독자 |
|---|---|---|
| `AGENTS.md` | Codex 작업 규칙, 문서 지도, 불변 조건 | Codex, 개발자 |
| `docs/00-governance` | 용어, 결정, 질문, 추적 방법 | 전 팀 |
| `docs/01-product` | 문제, 사용자, 범위, 요구사항, 수용 기준 | PO, 업무, 개발 |
| `docs/02-design` | 정보 구조, 화면 흐름, 디자인 원칙 | UX, Frontend |
| `docs/03-domain` | 규정 구조, 온톨로지, 목업 데이터 규칙 | 업무, Data/AI |
| `docs/04-architecture` | 시스템, 기술, 데이터, API, RAG, 보안 | Engineering |
| `docs/05-delivery` | 실행 계획, 백로그, 테스트, 배포, 운영 | Engineering, QA, Ops |

## 정본 규칙

- 무엇을 만들지는 `REQUIREMENTS.md`와 `PRODUCT_SPEC.md`가 정본이다.
- 규정 의미 구조는 `ONTOLOGY_SPEC.md`가 정본이다.
- DB/API 계약은 `DATA_MODEL.md`와 `API_SPEC.md`가 정본이다.
- 구현 순서와 상태는 `IMPLEMENTATION_PLAN.md`와 `BACKLOG.md`가 정본이다.
- 상충 시 더 구체적인 문서가 우선하되, 충돌을 해소하는 문서 변경을 같은 작업에 포함한다.

## ID 체계

| 접두사 | 대상 | 예 |
|---|---|---|
| `FR` | 기능 요구사항 | `FR-007` |
| `NFR` | 비기능 요구사항 | `NFR-004` |
| `US` | 사용자 스토리 | `US-QA-01` |
| `AC` | 수용 기준 | `AC-FR-007-01` |
| `ADR` | 기술/제품 결정 | `ADR-004` |
| `T` | 구현 task | `T-320` |
| `MOCK` | 가상 문서/엔터티 | `MOCK-EFO-001` |

요구사항을 변경할 때 관련 AC, API, schema, test, task를 함께 검색한다.

## 문서 상태

각 핵심 문서는 제목 아래에 상태를 사용한다.

- `Draft`: 논의 중이며 구현 계약이 아님
- `Baseline`: 구현 기준으로 승인된 기본안
- `Superseded`: 다른 문서/결정으로 대체됨

현재 문서 세트는 사용자 요청을 바탕으로 한 **Baseline 제안**이다. 실제 금융기관 적용 전 보안, 법무, 준법, IT 운영 책임자의 승인이 필요하다.

## 변경 절차

1. 영향받는 requirement/ADR/task ID를 식별한다.
2. 행동 변경이면 제품 문서를 먼저 수정한다.
3. architecture/API/data/security 영향 문서를 수정한다.
4. 구현·테스트·목업/평가 데이터를 수정한다.
5. 링크 검사와 추적성 검사를 수행한다.
6. 구현 결과와 문서의 차이가 없음을 리뷰한다.

## 작성 원칙

- 모호한 형용사 대신 측정 가능한 기준을 쓴다.
- happy path와 함께 오류, 권한 거부, 빈 결과, 부분 실패를 정의한다.
- 표에는 stable ID를 사용한다.
- 실제 규정 문구를 무단 복제하지 않는다.
- 변경 가능한 모델명/endpoint/secret은 설정 키로 표현한다.
- Mermaid는 관계 이해에 유용할 때만 사용하고, 중요한 의미는 본문에도 적는다.

## 필수 검증

- Markdown 링크가 존재한다.
- JSON/JSONL 목업 데이터가 파싱된다.
- 모든 FR이 하나 이상의 AC와 plan task에 매핑된다.
- 모든 공개 API가 인증/권한/오류 형식을 정의한다.
- 모든 RAG 응답 경로가 citation 또는 abstention 중 하나로 끝난다.

