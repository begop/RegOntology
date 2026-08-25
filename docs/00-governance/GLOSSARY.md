# Glossary

상태: Baseline

| 용어 | 정의 |
|---|---|
| 규정집 | 기관이 관리하는 하나 이상의 내부 규정 문서 집합 |
| 규정 문서 | 제목과 식별자를 가진 논리적 문서. 여러 버전을 가질 수 있음 |
| 규정 버전 | 특정 공포일·시행일·종료일과 원문 snapshot을 가진 불변 revision |
| 조문 | 편/장/절/조/항/호/목 계층의 addressable unit |
| 효력일(`as_of`) | 어떤 버전/조문이 유효한지 판단하는 기준 시점 |
| Knowledge Database | 문서, 버전, 조문, 청크, 임베딩, provenance, 감사 정보를 저장하는 PostgreSQL 중심 지식 저장소 |
| Ontology | 규정 도메인의 개념 유형, 관계 유형, 제약을 정의한 명시적 모델 |
| Knowledge Graph | 특정 규정에서 추출·승인된 ontology instance와 관계의 집합 |
| Graph projection | PostgreSQL 정본에서 Neo4j로 동기화한 재구축 가능 표현 |
| Chunk | 검색을 위한 텍스트 단위. 조문 locator와 부모 문맥을 보존함 |
| Vector retrieval | 임베딩 유사도로 관련 청크를 찾는 검색 |
| Lexical retrieval | 제목, 조문 번호, 용어, 원문 문자열을 이용한 검색 |
| Graph retrieval | entity와 관계를 따라 관련 조문·의무·예외를 찾는 검색 |
| GraphRAG | vector/lexical 후보와 graph neighborhood를 결합해 LLM context를 만드는 RAG 방식 |
| Citation | 답변 주장을 원문 조문으로 역추적하는 구조화 근거 |
| Groundedness | 답변 내용이 제공된 근거로 지지되는 정도 |
| Abstention | 충분한 근거가 없거나 권한 밖일 때 답변을 생성하지 않는 동작 |
| Provenance | source file, checksum, parser/model/prompt version, 검토자 등 데이터 생성 이력 |
| Publication | 검토 완료 버전과 파생 index/graph를 일반 사용자 검색에 활성화하는 원자적 상태 전이 |
| Curator | 규정 수집, 파싱 결과, ontology extraction, publication을 검토하는 담당자 |
| Golden QA | 기대 답변, 허용 근거, 답변 가능 여부를 사람이 확정한 회귀평가 데이터 |

