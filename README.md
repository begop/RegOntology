# Regulation Knowledge Graph QA

금융기관 내부 규정집을 구조화·버전화하고, Vector Retrieval과 Knowledge Graph를 결합한 GraphRAG로 근거 인용형 QA와 Ontology Explorer를 제공하는 프로젝트다.

> 현재 상태: **기획 및 실행 기준선 완료 단계**. 애플리케이션 코드는 아직 구현하지 않는다.

## 핵심 사용자 가치

- 자연어로 규정을 질문하고 조/항/호 단위 근거를 확인한다.
- 특정 기준일에 유효한 규정만 조회한다.
- 의무·금지·예외·담당 조직·통제 간 관계를 그래프로 탐색한다.
- 규정 변경, 인덱싱, 질의와 답변을 감사 가능한 형태로 추적한다.
- 근거가 부족하면 시스템이 명확히 답변을 보류한다.

## 기획 문서 읽기

1. [프로젝트 헌장](docs/01-product/PROJECT_CHARTER.md)
2. [요구사항](docs/01-product/REQUIREMENTS.md)
3. [제품 명세](docs/01-product/PRODUCT_SPEC.md)
4. [UX 흐름](docs/02-design/UX_FLOW.md)
5. [시스템 아키텍처](docs/04-architecture/ARCHITECTURE.md)
6. [데이터 모델](docs/04-architecture/DATA_MODEL.md)
7. [RAG 파이프라인](docs/04-architecture/RAG_PIPELINE.md)
8. [구현 계획](docs/05-delivery/IMPLEMENTATION_PLAN.md)

Codex는 루트 [AGENTS.md](AGENTS.md)를 작업 규칙과 인덱스로 사용한다.

## 기존 자료 경계

`doc/` 폴더의 기존 `core-prd.md`는 인력·역량 온톨로지를 다루는 별도 초안이다. 이번 프로젝트의 정본은 `docs/`이며, 기존 파일은 보존하되 현재 구현 범위에 포함하지 않는다.

## 계획된 저장소 구조

```text
frontend/            React 애플리케이션
backend/             FastAPI 애플리케이션과 worker
infra/               local/CI/deployment 구성
docs/                제품·설계·아키텍처·실행 문서
mock-data/           모두 가상인 규정, 그래프 seed, 골든 QA
tests/               계약/E2E/평가 테스트
```

## 목업 데이터 주의

`mock-data/`의 기관, 규정, 조직, 사람, 날짜와 임계값은 전부 가상이다. 실제 법령, 감독규정, 금융기관의 내부 규정 또는 법률 자문으로 사용하면 안 된다.
