# Regulation Ontology Specification

상태: Baseline  
Ontology ID: `regula-core`  
Version: `0.1.0`

## 목적

규정 원문의 문서 구조와 규범적 의미를 분리해 표현한다. 원문 조문이 최종 근거이며, ontology node/edge는 검색·탐색·설명을 돕는 검토된 annotation이다.

## 모델 원칙

- 모든 의미 node/edge는 최소 하나의 `ASSERTED_BY` 조문 근거를 가진다.
- 자동 추출 결과는 `PROPOSED`, 사람 승인 후 `APPROVED`, publication에서만 검색 가능하다.
- 동일 entity의 별칭은 canonical entity에 연결하고 원문 표기는 보존한다.
- 시간은 node/edge의 `valid_from`, `valid_to`와 source regulation version으로 표현한다.
- 금액·기간·비율은 문자열이 아니라 단위 있는 구조화 `Condition`으로 표현한다.
- 예외는 원래 의무/금지와 명시적으로 연결한다.

## 상위 계층

```text
RegulationDocument
└─ RegulationVersion
   └─ Provision (Part/Chapter/Section/Article/Paragraph/Item/Subitem)
      └─ Norm (Obligation/Prohibition/Permission/Recommendation)
         ├─ Actor / OrganizationRole
         ├─ Action
         ├─ Object / DataCategory / System / Record
         ├─ Condition / Threshold / EffectivePeriod
         ├─ Exception
         └─ Control / EvidenceRequirement
```

## Node types

| Type | 의미 | 필수 속성 | 예 |
|---|---|---|---|
| `RegulationDocument` | 논리적 규정 | `id`, `title`, `owner_org` | 정보보호 운영규정 |
| `RegulationVersion` | 불변 revision | `id`, `version`, `effective_from`, `checksum` | v1.0 |
| `Provision` | 조문 구조 unit | `id`, `level`, `locator`, `title`, `text_hash` | 제5조 제2항 |
| `Norm` | 규범 statement 공통 | `id`, `modality`, `summary` | 접근권한 분기 검토 의무 |
| `Obligation` | 해야 함 | Norm 속성 | 로그 보관 |
| `Prohibition` | 해서는 안 됨 | Norm 속성 | 계정 공유 금지 |
| `Permission` | 할 수 있음 | Norm 속성 | 긴급 접근 허용 |
| `Recommendation` | 권고 | Norm 속성 | 정기 교육 권고 |
| `Exception` | 조건부 예외 | `id`, `summary` | 비상상황 예외 |
| `Actor` | 수행 주체 유형 | `id`, `name` | 시스템 관리자 |
| `Organization` | 조직 | `id`, `name` | 정보보호부 |
| `Action` | 정규화 행위 | `id`, `lemma` | 검토하다 |
| `DataCategory` | 정보 분류 | `id`, `name`, `classification` | 고객식별정보 |
| `System` | 정보시스템 유형 | `id`, `name` | 중요정보시스템 |
| `Control` | 통제/절차 | `id`, `name`, `control_type` | 분기 접근권한 검토 |
| `EvidenceRequirement` | 증적 요구 | `id`, `name`, `retention` | 승인 기록 5년 보관 |
| `Condition` | 적용 조건 | `id`, `expression`, `normalized` | 퇴직 후 24시간 이내 |
| `Threshold` | 수치 기준 | `id`, `value`, `unit`, `operator` | 24 hour ≤ |
| `Term` | 정의 용어 | `id`, `label`, `definition` | 중요정보시스템 |
| `Risk` | 규정이 다루는 위험 | `id`, `name` | 무단 접근 |

`Norm`은 구현 편의상 label과 `modality`를 함께 갖되 중복 의미가 생기지 않게 constraint를 둔다.

## Edge types

| Relation | From → To | 의미 |
|---|---|---|
| `HAS_VERSION` | Document → Version | 버전 소유 |
| `CONTAINS` | Version/Provision → Provision | 조문 계층 |
| `NEXT` | Provision → Provision | 원문 순서 |
| `SUPERSEDES` | Version → Version | 대체 버전 |
| `CROSS_REFERENCES` | Provision → Provision | 명시적 상호 참조 |
| `DEFINES` | Provision → Term | 용어 정의 |
| `ASSERTS` | Provision → Norm/Exception | 원문이 의미를 주장 |
| `PERFORMED_BY` | Norm → Actor/Organization | 수행 주체 |
| `HAS_ACTION` | Norm → Action | 규범 행위 |
| `TARGETS` | Norm → DataCategory/System/Record/Term | 행위 대상 |
| `UNDER_CONDITION` | Norm/Exception → Condition | 적용 조건 |
| `HAS_THRESHOLD` | Condition → Threshold | 정규화 수치 |
| `HAS_EXCEPTION` | Norm → Exception | Norm의 예외 |
| `EXCEPTION_TO` | Exception → Norm | 역방향 명시 |
| `IMPLEMENTED_BY` | Norm → Control | 의무 구현 통제 |
| `EVIDENCED_BY` | Norm/Control → EvidenceRequirement | 증적 |
| `OWNED_BY` | Document/Control/System → Organization | 책임 조직 |
| `MITIGATES` | Control → Risk | 위험 완화 |
| `RELATED_TO` | Entity → Entity | 검토된 약한 관계; 구체 relation 우선 |
| `SAME_AS` | Term/Entity → Term/Entity | canonical 동일성 |

## 공통 provenance 속성

모든 의미 node와 edge는 다음을 가진다.

| 속성 | 설명 |
|---|---|
| `source_version_id` | PostgreSQL 규정 버전 ID |
| `source_provision_id` | 근거 조문 ID |
| `source_locator` | 사람이 읽는 locator |
| `extraction_method` | `rule`, `llm`, `manual` |
| `extractor_version` | parser/model/prompt bundle version |
| `confidence` | 0–1 제안 score; 승인 후에도 원값 보존 |
| `review_status` | `PROPOSED`, `APPROVED`, `REJECTED` |
| `reviewed_by`, `reviewed_at` | 승인 정보 |
| `publication_id` | 활성 snapshot 식별자 |

## Identity 규칙

- Document: 기관 namespace + 문서 code, 예 `mock:MOCK-EFO-001`
- Version: document ID + semantic version, 예 `mock:MOCK-EFO-001:v1.0`
- Provision: version ID + canonical path, 예 `...:art-5:p-2:i-1`
- Domain entity: type + normalized Korean label + optional scope
- Norm: source provision + modality + normalized action/object fingerprint

display label 변경과 ID 변경을 분리한다.

## 제약

1. `RegulationVersion`은 하나의 `RegulationDocument`에만 속한다.
2. 같은 document의 published effective period는 겹치지 않는다.
3. `Provision`은 정확히 하나의 version tree에 속한다.
4. `Norm`은 하나 이상의 `ASSERTS` 근거가 있어야 한다.
5. `Exception`은 하나 이상의 `EXCEPTION_TO`를 가져야 한다.
6. `Threshold.value`는 숫자이고 허용 unit vocabulary를 사용한다.
7. `APPROVED` relation의 양 끝 node도 publication snapshot에 존재해야 한다.
8. Restricted source에서 파생된 node/edge는 동일하거나 더 강한 security class를 상속한다.

## 질문별 graph pattern

### “누가 무엇을 해야 하는가?”

`Provision-[:ASSERTS]->Obligation-[:PERFORMED_BY]->Actor`와 `HAS_ACTION/TARGETS`를 조회한다.

### “예외는 무엇인가?”

관련 Norm에서 `HAS_EXCEPTION → Exception → UNDER_CONDITION`을 조회하고 각 source provision을 함께 가져온다.

### “어떤 통제로 이행하는가?”

`Norm → IMPLEMENTED_BY → Control → EVIDENCED_BY → EvidenceRequirement`를 최대 3 hop으로 조회한다.

### “두 규정은 어떻게 연결되는가?”

공통 Term/Actor/Control과 명시적 `CROSS_REFERENCES`를 우선하고, `RELATED_TO`만으로 강한 결론을 만들지 않는다.

## Viewer style mapping

| Node | Shape | 의미 색상 |
|---|---|---|
| Document/Version/Provision | round-rectangle | neutral/navy |
| Obligation | rectangle | blue |
| Prohibition | octagon | red |
| Permission | ellipse | teal |
| Exception | diamond | amber |
| Actor/Organization | person/hexagon | violet |
| Control/Evidence | tag/round-rectangle | green |
| Data/System/Term | ellipse | gray/cyan |

shape와 label을 항상 사용해 색각에만 의존하지 않는다.

## Evolution

- compatible 추가: optional node/edge/property, minor version 증가
- breaking 변경: ID/필수 property/관계 의미 변경, major version 증가와 projection migration 필요
- ontology version은 각 publication과 QA trace에 저장한다.

