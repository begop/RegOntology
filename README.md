# Regulation Knowledge Graph QA

금융기관 내부 규정집을 구조화·버전화하고, Vector Retrieval과 Knowledge Graph를 결합한 GraphRAG로 근거 인용형 QA와 Ontology Explorer를 제공하는 프로젝트다.

> 현재 상태: **Mock-first 실행 가능 MVP**. 실제 기관 데이터와 외부 모델 없이도 샘플 규정 검색, 근거 인용 QA, 규정 상세, Ontology Explorer를 검증할 수 있다. Compose 실행 시 Alembic migration 후 PostgreSQL/pgvector 정본과 Neo4j projection을 생성하며, 메모리 Mock profile은 빠른 개발·테스트용으로 별도 유지한다.

## 빠른 실행

Docker Desktop을 시작한 뒤 저장소 루트에서 실행한다.

```powershell
pwsh ./scripts/dev.ps1 bootstrap
```

이 명령은 기존 `.env`를 수정하지 않고 git-ignored `.env.local`에 로컬 DB 비밀번호를 무작위 생성하며, 전체 Docker 이미지를 빌드하고 health check가 통과할 때까지 기다린다.

- Web UI: <http://127.0.0.1:8080>
- API health: <http://127.0.0.1:8000/api/v1/health>
- OpenAPI: <http://127.0.0.1:8000/api/docs>

기본 `REGONTOLOGY_AI_PROVIDER=fake` 모드는 OpenAI API key가 필요 없다. 키를 나중에 수동 생성할 때에만 `.env.local`에서 provider를 `openai`로 변경하고 키를 주입한다. Compose는 migration, 가상 규정 seed, pgvector embedding 적재, Neo4j projection을 순서대로 수행한 뒤 API를 시작한다. 자세한 실행, 이미지 pull, GHCR release 절차는 [배포 가이드](deploy/README.md)를 따른다.

Docker/GHCR용 Web 이미지는 빌드 시 `VITE_DEMO_MODE=false`를 고정하므로 API 오류를 내장 데모 응답으로 숨기지 않는다. 반면 GitHub Pages mock UI는 이 값을 명시적으로 `true`로 설정하고, Sites 정적 데모도 기존 fallback을 유지한다. 백엔드의 `fake` AI provider와 프런트의 embedded demo fallback은 서로 다른 기능이다.

## 핵심 사용자 가치

- 자연어로 규정을 질문하고 조/항/호 단위 근거를 확인한다.
- 특정 기준일에 유효한 규정만 조회한다.
- 의무·금지·예외·담당 조직·통제 간 관계를 2D 그래프, 3D 입체 캔버스, 접근 가능한 목록으로 탐색한다.
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

## 저장소 구조

```text
frontend/            React 애플리케이션
backend/             FastAPI 애플리케이션
deploy/              Dockerfile, nginx, DB bootstrap, 배포 가이드
.github/workflows/   품질·보안·Compose smoke·GHCR release
docs/                제품·설계·아키텍처·실행 문서
mock-data/           모두 가상인 규정, 그래프 seed, 골든 QA
```

## 검증과 컨테이너 이미지

```powershell
pwsh ./scripts/dev.ps1 test
pwsh ./scripts/dev.ps1 health
```

기본 브랜치(`main` 또는 `master`) 및 `v*` tag CI가 통과하면 SBOM, provenance, keyless signature가 포함된 `ghcr.io/begop/regontology-api`와 `ghcr.io/begop/regontology-web` 이미지를 발행한다. 저장소 Settings에서 GitHub Pages의 GitHub Actions source를 활성화하면 mock 전용 공개 UI는 <https://begop.github.io/RegOntology/>에 배포된다. 실제 API까지 포함한 원격 full-stack URL은 별도 호스팅과 DNS/TLS가 필요하며, 로컬 검증 URL은 위의 `127.0.0.1:8080`이다.

## 목업 데이터 주의

`mock-data/`의 기관, 규정, 조직, 사람, 날짜와 임계값은 전부 가상이다. 실제 법령, 감독규정, 금융기관의 내부 규정 또는 법률 자문으로 사용하면 안 된다.
