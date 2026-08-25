# Design System Direction

상태: Baseline

## 표현 목표

금융기관 업무 도구에 맞게 신뢰성, 밀도, 추적 가능성을 우선한다. 장식적 AI 채팅보다 **조문과 근거를 읽는 조사 도구**처럼 보여야 한다.

## 기술

- Tailwind CSS로 token 기반 style
- shadcn/ui를 접근 가능한 primitive 조합의 기준으로 사용
- Radix 기반 component의 keyboard/ARIA 동작 유지
- Cytoscape.js graph style은 동일 semantic token에서 파생
- icon은 Lucide React 한 세트로 제한

## Semantic token

구현 시 CSS variables로 light/dark theme를 정의한다.

| Token | 의미 | 초기 방향 |
|---|---|---|
| `--surface` | 기본 배경 | 저채도 neutral |
| `--surface-raised` | card/panel | surface와 명확한 경계 |
| `--text-primary` | 본문 | AA contrast |
| `--text-muted` | 보조 metadata | AA contrast 유지 |
| `--brand` | 주요 action | 짙은 blue |
| `--evidence` | 검증된 citation/근거 | teal/green 계열 |
| `--warning` | 부분 답변/검토 필요 | amber 계열 |
| `--danger` | 권한/실패/blocker | red 계열 |
| `--graph-obligation` | 의무 node | blue + rectangle |
| `--graph-prohibition` | 금지 node | red + octagon |
| `--graph-exception` | 예외 node | amber + diamond |

색상 값은 구현 후 contrast 자동검사와 화면 QA로 확정한다.

## Typography

- 한국어 UI: 시스템 sans-serif 우선, 배포 정책이 허용하면 Pretendard를 self-host
- 규정 원문: 읽기 폭 72–84자, line-height 1.7 이상
- 조문 번호와 metadata: tabular numerals 사용
- code/identifier만 monospace

## 핵심 컴포넌트

### AnswerCard

- `answered`, `partial`, `abstained` 상태
- 결론, 설명, 기준일, citation count, trace link, feedback
- 답변 상태와 warning을 card 첫 부분에서 인식 가능

### CitationChip / CitationPanel

- label: `[1] 정보보호 운영규정 v1.0 제5조 제2항`
- hover에만 의존하지 않고 click/focus로 preview
- source checksum이나 internal chunk ID는 일반 UI에 노출하지 않음

### RegulationArticle

- stable anchor, locator, effective badge, linked concept
- citation으로 진입 시 관련 구절 강조 및 screen reader 설명

### GraphCanvas

- legend, zoom control, fit, reset, layout selector
- selection은 URL/session state와 detail drawer에 동기화
- edge 방향과 label을 표시

### DataStatusBadge

- Mock, Draft, Published, Superseded, Projection stale, Degraded
- badge 의미를 tooltip과 text로 설명

## Content style

- 결론을 먼저 쓰고 조문 용어를 그대로 사용한다.
- “확실합니다” 같은 모호한 자신감 표현 대신 근거 범위와 기준일을 쓴다.
- 보류 메시지는 실패 원인과 사용자가 할 수 있는 다음 행동을 포함한다.
- 금융/법률 최종 판단이 아님을 반복적으로 방해하지 않되 답변 카드와 footer에서 분명히 알린다.

## QA checklist

- 200% zoom과 320px width에서 정보 손실 없음
- keyboard로 질문 → 답변 → citation → 원문 이동 가능
- screen reader가 answer status와 citation count를 읽음
- 모든 semantic status가 색 없이 구분됨
- Korean 긴 제목/조문이 겹치거나 잘리지 않음
- graph 200 nodes에서 UI가 멈추지 않고 대체 list가 동작

