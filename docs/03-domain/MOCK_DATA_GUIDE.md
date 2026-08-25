# Mock Data Guide

상태: Baseline

## 목적과 면책

`mock-data/`는 ingestion, 검색, ontology, QA, 보안, 버전 평가에 사용할 **완전한 가상 데이터**다. `한빛금융`이라는 가상 기관과 임의 규정 문구를 사용하며 실제 법령이나 특정 금융기관 규정을 재현하지 않는다.

## 데이터 구성

| 경로 | 용도 |
|---|---|
| `mock-data/regulations/*.md` | parser/ingestion 입력 규정 원문 |
| `mock-data/ontology/ontology_seed.json` | 승인된 node/edge 기대값 seed |
| `mock-data/evaluation/qa_gold.jsonl` | answerable/unanswerable/as-of/ACL 골든 질문 |
| `mock-data/README.md` | 실행 시나리오와 식별자 설명 |

## 가상 규정 세트

| ID | 제목 | 핵심 관계 | 보안등급 |
|---|---|---|---|
| MOCK-EFO-001 | 전자금융업무 운영규정 | 장애보고, 변경승인, 로그보관 | Internal |
| MOCK-ISP-001 | 정보보호 운영규정 | 접근권한, 계정금지, 긴급접근 예외 | Internal |
| MOCK-PIP-001 | 개인정보 처리규정 | 최소수집, 파기, 위탁점검 | Restricted |

## Markdown 입력 형식

각 파일은 YAML frontmatter와 조문 Markdown을 가진다.

```yaml
document_id: MOCK-EFO-001
version: 1.0
status: published
effective_from: 2026-01-01
effective_to: null
security_class: internal
owner_org: 전자금융운영부
is_mock: true
```

heading은 문서/장/조, ordered list는 항/호로 사용한다. parser는 화면 텍스트가 아니라 canonical hierarchy를 생성해야 한다.

## 목업이 검증해야 하는 경우

- 단일 조문 직접 질문
- 여러 규정을 결합해야 하는 질문
- 의무와 예외가 다른 조문에 있는 질문
- 부서/통제/증적 graph 경로
- 효력일 전후 버전 선택
- Restricted 문서 권한 거부
- 존재하지 않는 보관 기간/금액 등 answerable하지 않은 질문
- 유사하지만 다른 용어의 vector 검색
- 정확한 조문 번호/고유 용어의 lexical 검색

## 안전 규칙

- 실제 개인 이름, 계좌, 전화, 이메일, 기관 식별자를 만들지 않는다.
- 실제 법령 번호나 감독기관 지침처럼 오인될 표현을 피한다.
- 모든 화면과 export에 `MOCK` badge 또는 `is_mock` 표시를 유지한다.
- 목업 답변을 실제 업무 판단 사례로 재사용하지 않는다.

## 확장 규칙

새 mock 규정은 다음을 함께 추가한다.

1. 고유 `MOCK-*` document ID
2. 최소 1개 cross-reference 또는 ontology relation
3. answerable 질문 2개 이상
4. unanswerable 또는 edge-case 질문 1개 이상
5. ontology seed node/edge와 source locator
6. parser expected counts

