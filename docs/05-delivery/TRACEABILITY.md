# Requirement Traceability Matrix

상태: Baseline

| Requirement | Product/Design | Architecture | Plan | Primary verification |
|---|---|---|---|---|
| FR-001 | Product F5 | API/Data | T-200 | upload/preflight integration |
| FR-002 | Library/Detail | Data | T-120, T-230 | effective overlap/as-of |
| FR-003 | Detail/Ingestion | Data/RAG build | T-130, T-220 | parser golden |
| FR-004 | Ingestion Review | Ontology/Data | T-240, T-430 | review/audit E2E |
| FR-005 | Publication | Architecture/RAG | T-250, T-440 | atomic failure/rollback |
| FR-006 | Search | Data/RAG | T-300~320 | embedding/index recall |
| FR-007 | QA/Search | RAG | T-330~350, T-510 | Recall@10/ablation |
| FR-008 | QA Chat | API/RAG | T-530~570 | answer/citation eval |
| FR-009 | QA Chat | RAG abstention | T-550 | negative Golden QA |
| FR-010 | Citation/Detail | API/Data | T-140, T-570 | deep-link E2E |
| FR-011 | Library | API/Data | T-140, T-160 | filter/ACL/as-of |
| FR-012 | Compare | API/Data | T-260 | structural diff cases |
| FR-013 | Explorer 2D/3D/list | Ontology/API | T-450, T-460 | bounded graph + deterministic 3D projection + view state tests |
| FR-014 | Explorer/QA | Ontology/RAG | T-410~450, T-500 | entity/path eval |
| FR-015 | QA feedback | API/Data | T-570 | authorization/idempotency |
| FR-016 | Audit | Security/Data | T-170, T-560 | audit completeness |
| FR-017 | Global roles | Security/API | T-110 | cross-lane scope matrix |
| FR-018 | Admin jobs | Architecture | T-210, T-440 | retry/rebuild/chaos |
| FR-019 | Evaluation | RAG/Test | T-350, T-580 | reproducible eval |
| FR-020 | QA trace | API/RAG/Security | T-350, T-560 | trace/redaction |
| NFR-001~006 | Global | Security/Data/RAG | P1~P6 | security/temporal/audit |
| NFR-007~010 | UX/Operations | Architecture | T-600~650 | load/a11y/observability |
| NFR-011~015 | Governance | Tech/Security/Deploy | T-010~050, T-630~670 | scans/DR/portability/privacy |

새 requirement는 최소 하나의 acceptance criterion, implementation task, primary verification을 추가해야 Baseline이 된다.
