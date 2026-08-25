# UX Flow and Information Architecture

상태: Baseline

## 정보 구조

```text
로그인
└─ 앱 셸
   ├─ 홈 대시보드
   ├─ 규정 검색
   │  └─ 규정 상세
   │     ├─ 조문 원문
   │     ├─ 버전 이력/비교
   │     └─ 연결된 Ontology
   ├─ 규정 QA
   │  └─ 답변 → Citation → 규정 상세
   ├─ Ontology Explorer
   │  └─ Node/Path → 관련 조문
   └─ 관리
      ├─ Ingestion & Review
      ├─ Publication/Index Jobs
      ├─ Evaluation
      └─ Audit/Settings
```

관리 메뉴는 역할에 따라 노출하며 API 권한을 대체하지 않는다.

## 공통 앱 셸

- 좌측 navigation, 상단 통합 검색, 사용자/기준일 context
- 전역 `as_of`는 규정 검색, QA, graph에 전달되며 화면별로 명시적으로 표시
- 환경/데이터 상태 badge: `Mock Data`, `Degraded`, `Projection Stale`
- 모든 주요 페이지는 loading, empty, error, access denied 상태를 설계

## Flow A — 첫 질문부터 근거 확인까지

1. 사용자가 QA 페이지에서 질문과 기준일을 입력한다.
2. UI는 질문을 즉시 표시하고 검색/생성 단계를 progress로 보여준다.
3. 성공 시 answer status, 결론, 설명, citation, 적용 기준일을 표시한다.
4. 사용자가 citation을 선택하면 side preview에서 원문을 보고 새 페이지로 이동할 수 있다.
5. 사용자가 `관계 보기`를 선택하면 답변에 사용된 entity 중심 Ontology Explorer가 열린다.
6. 사용자가 feedback과 이유를 제출한다.

### 보류 상태

- 근거 부족: “등록된 규정에서 충분한 근거를 찾지 못했습니다.”
- 권한 제한: 제한 문서의 존재를 암시하지 않고 “현재 접근 범위에서 답변할 수 없습니다.”
- 모호한 질문: 시간/업무/대상을 선택하도록 clarification 제안
- 시스템 일부 장애: 사용한 lane과 제외된 lane을 표시하고 신뢰 가능한 경우에만 부분 답변

## Flow B — 규정 탐색

1. 목록에서 검색/필터/기준일을 설정한다.
2. 결과 카드에서 현재 version과 시행 기간을 확인한다.
3. 상세 화면에서 목차로 조문을 이동한다.
4. 관련 의무·예외·통제 panel을 확인한다.
5. 선택적으로 이전 version과 diff를 연다.

브라우저 뒤로가기 후 필터와 scroll 위치를 복원한다.

## Flow C — Ontology Explorer

1. 개념/조직/통제/문서/조문을 검색한다.
2. 중심 node와 1-hop subgraph를 불러온다.
3. node type, relation type, 규정, 효력일로 필터한다.
4. node를 선택해 정의, provenance, 관련 조문을 본다.
5. `확장`으로 다음 1-hop을 추가하거나 두 node path를 조회한다.
6. `조문 열기`로 원문 상세로 이동한다.

### 그래프 안전장치

- 초기 50 nodes, view 최대 200 nodes
- server가 허용된 relation과 최대 hop을 강제
- 200 nodes 도달 시 더 구체적인 필터 안내
- 색만으로 의미를 구분하지 않고 shape/label/legend 병행
- 동일 정보를 list/table로 제공

## Flow D — Ingestion/Review/Publish

1. Curator가 file, document ID, title, owner, security class, dates를 입력한다.
2. preflight 결과(checksum, 형식, 중복, 날짜)를 확인한다.
3. parsing job 후 source/parsed split view에서 locator 오류를 수정한다.
4. entity/relation suggestion을 confidence/근거별로 검토한다.
5. validation report에서 blocker/warning을 확인한다.
6. 승인 권한자가 publish한다.
7. active publication과 index/projection watermark를 확인한다.

`Publish`는 영향이 큰 행위이므로 대상 문서/버전/시행일을 확인하는 명시적 confirmation을 사용한다.

## 핵심 화면 사양

| 화면 | 주요 컴포넌트 | 완료 조건 |
|---|---|---|
| Dashboard | 최근 규정, 인기 질문, 품질/상태 카드 | 역할별 필요한 정보만 표시 |
| Regulation List | search, facet, result, pagination | URL로 필터 공유 가능 |
| Regulation Detail | TOC, article body, metadata, relations | stable locator deep link |
| QA Chat | composer, status, answer, citations, feedback | keyboard-only 이용 가능 |
| Ontology Explorer | search, graph, legend, detail, list | bounded subgraph와 대체 뷰 |
| Ingestion Review | stepper, diff, issue list, suggestion table | blocker 0건 전 publish 비활성 |
| Evaluation | run config, metric diff, failed cases | baseline 대비 회귀 식별 |
| Audit | filters, event table, detail | 권한 기반 redaction |

## Responsive 기준

- Desktop ≥ 1280px: 3-pane detail/graph 경험 최적화
- Tablet 768–1279px: detail panel을 drawer로 전환
- Mobile < 768px: QA와 규정 원문 읽기 지원, graph canvas는 list-first; curator workflow는 desktop 권장

## 접근성

- landmark, heading, focus order와 visible focus 준수
- graph node를 검색 가능한 목록으로 동기화
- citation은 링크 텍스트에 문서/locator 포함
- status는 색뿐 아니라 icon/text/ARIA live로 전달
- animation은 reduced-motion 선호를 준수

