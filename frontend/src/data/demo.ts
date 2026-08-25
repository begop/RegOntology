import type {
  IngestionJob,
  OntologyEdge,
  OntologyGraph,
  OntologyNode,
  QaResponse,
  RegulationDetail,
  RegulationSummary,
  RegulationVersion,
  SystemStatus,
} from "../lib/types";

// Curated UI fixtures derived from the repository's synthetic `mock-data/` set.
// They intentionally contain no customer, account, or real-institution data.
const ispVersions: RegulationVersion[] = [
  {
    id: "MOCK-ISP-001:v1.1",
    label: "1.1",
    effectiveFrom: "2026-07-01",
    effectiveTo: null,
    status: "PUBLISHED",
  },
  {
    id: "MOCK-ISP-001:v1.0",
    label: "1.0",
    effectiveFrom: "2026-01-01",
    effectiveTo: "2026-07-01",
    status: "SUPERSEDED",
  },
];

const efoVersion: RegulationVersion = {
  id: "MOCK-EFO-001:v1.0",
  label: "1.0",
  effectiveFrom: "2026-01-01",
  effectiveTo: null,
  status: "PUBLISHED",
};

export const demoRegulations: RegulationSummary[] = [
  {
    id: "MOCK-ISP-001",
    code: "MOCK-ISP-001",
    title: "정보보호 운영규정",
    ownerOrg: "정보보호부",
    documentType: "운영규정",
    securityClass: "internal",
    isMock: true,
    currentVersion: ispVersions[0]!,
    snippet: "중요정보시스템의 접근권한 검토·회수와 긴급 접근계정 운영 기준",
    tags: ["접근권한", "계정", "정보보호", "긴급접근"],
  },
  {
    id: "MOCK-EFO-001",
    code: "MOCK-EFO-001",
    title: "전자금융업무 운영규정",
    ownerOrg: "전자금융운영부",
    documentType: "업무규정",
    securityClass: "internal",
    isMock: true,
    currentVersion: efoVersion,
    snippet: "전자금융시스템 변경·사고 보고·접근 및 거래 로그 관리 기준",
    tags: ["전자금융", "사고보고", "로그", "변경관리"],
  },
];

export const demoRegulationDetails: Record<string, RegulationDetail> = {
  "MOCK-ISP-001": {
    ...demoRegulations[0]!,
    institution: "한빛금융 (가상)",
    versions: ispVersions,
    relatedNodeIds: [
      "obligation:분기접근권한검토",
      "prohibition:계정공유금지",
      "permission:긴급접근",
    ],
    provisions: [
      {
        id: "isp-art-1",
        locator: "제1조",
        title: "목적",
        paragraphs: [
          "이 규정은 한빛금융의 정보자산을 보호하기 위한 접근통제와 보안운영의 기본 사항을 정한다.",
          "전자금융시스템의 거래 및 사고 관리는 전자금융업무 운영규정과 함께 적용한다.",
        ],
        concepts: ["정보자산", "접근통제"],
      },
      {
        id: "isp-art-3",
        locator: "제3조",
        title: "계정 발급",
        paragraphs: [
          "시스템 관리계정은 사용자별로 발급해야 하며 신청자와 승인자를 분리해야 한다.",
          "계정 발급 요청에는 업무 목적, 대상 시스템, 필요한 권한과 사용기간을 기록해야 한다.",
          "사용기간이 끝난 임시계정은 자동으로 비활성화해야 한다.",
        ],
        concepts: ["관리계정", "승인 분리"],
      },
      {
        id: "isp-art-4",
        locator: "제4조",
        title: "계정 공유 금지",
        paragraphs: [
          "임직원은 개인계정과 관리계정을 다른 사람과 공유해서는 안 된다.",
          "공용 기술계정이 불가피한 경우 정보보호부장의 사전 승인을 받고 사용 주체를 식별할 수 있는 별도 로그를 남겨야 한다.",
        ],
        concepts: ["계정 공유 금지", "공용 기술계정"],
      },
      {
        id: "isp-art-5",
        locator: "제5조",
        title: "접근권한 검토 및 회수",
        paragraphs: [
          "시스템 소유부서는 중요정보시스템의 접근권한을 분기마다 검토해야 한다.",
          "부서 이동 또는 직무 변경이 확인되면 소유부서는 8시간 이내에 불필요한 권한을 회수해야 한다.",
          "퇴직자의 모든 접근권한은 퇴직 효력 발생 후 24시간 이내에 회수해야 한다.",
        ],
        concepts: ["분기 접근권한 검토", "권한 회수", "시스템 소유부서"],
      },
      {
        id: "isp-art-6",
        locator: "제6조",
        title: "긴급 접근계정",
        paragraphs: [
          "중대한 장애 또는 보안사고의 복구를 위해 긴급 접근계정을 사용할 수 있으며 사용시간은 4시간을 초과할 수 없다.",
          "긴급 접근계정 사용자는 사용 종료 후 1영업일 이내에 목적, 수행 작업과 결과를 기록하고 시스템 소유부장의 사후 승인을 받아야 한다.",
          "긴급 접근 로그와 승인 기록은 5년간 보관해야 한다.",
        ],
        concepts: ["긴급 접근", "사후 승인", "승인 기록"],
      },
      {
        id: "isp-art-7",
        locator: "제7조",
        title: "통제 점검",
        paragraphs: [
          "정보보호부는 접근권한 검토와 긴급 접근계정 운영 상태를 반기마다 점검해야 한다.",
          "중대한 미비점은 발견 후 10영업일 이내에 개선계획을 수립하고 정보보호부장의 승인을 받아야 한다.",
        ],
        concepts: ["통제 점검", "개선계획"],
      },
    ],
  },
  "MOCK-EFO-001": {
    ...demoRegulations[1]!,
    institution: "한빛금융 (가상)",
    versions: [efoVersion],
    relatedNodeIds: ["obligation:중대사고30분보고", "obligation:로그5년보관"],
    provisions: [
      {
        id: "efo-art-1",
        locator: "제1조",
        title: "목적",
        paragraphs: [
          "이 규정은 한빛금융의 전자금융업무를 안정적으로 운영하기 위한 기본 절차를 정함을 목적으로 한다.",
          "이 규정에 정하지 않은 정보보호 사항은 정보보호 운영규정에 따른다.",
        ],
        concepts: ["전자금융업무", "안정적 운영"],
      },
      {
        id: "efo-art-3",
        locator: "제3조",
        title: "시스템 변경 승인",
        paragraphs: [
          "시스템 소유부서는 운영환경 변경 전에 영향도와 복구계획을 작성하고 변경관리책임자의 승인을 받아야 한다.",
          "중요전자금융시스템의 고위험 변경은 정보보호부의 보안성 검토를 추가로 받아야 한다.",
          "서비스 복구를 위한 긴급 변경은 우선 실시할 수 있다. 이 경우 실시 후 2영업일 이내에 사후 승인을 완료해야 한다.",
        ],
        concepts: ["변경 승인", "복구계획"],
      },
      {
        id: "efo-art-4",
        locator: "제4조",
        title: "전자금융사고 보고",
        paragraphs: [
          "운영담당자는 전자금융사고를 인지한 즉시 업무연속성센터에 보고해야 한다.",
          "중대한 전자금융사고인 경우 업무연속성센터는 인지 후 30분 이내에 전자금융운영부장과 정보보호부장에게 보고해야 한다.",
          "사고 보고와 조치 기록은 사고 종료일부터 5년간 보관해야 한다.",
        ],
        concepts: ["중대한 전자금융사고", "30분 보고"],
      },
      {
        id: "efo-art-5",
        locator: "제5조",
        title: "접근 및 거래 로그",
        paragraphs: [
          "중요전자금융시스템은 관리자 접근, 고객 거래, 보안 경보 로그를 생성해야 한다.",
          "로그는 위변조를 방지하는 방식으로 5년간 보관하고 정보보호부가 매월 무결성을 점검해야 한다.",
          "관리자 접근권한의 부여와 검토는 정보보호 운영규정 제5조에 따른다.",
        ],
        concepts: ["로그 5년 보관", "무결성 점검"],
      },
      {
        id: "efo-art-6",
        locator: "제6조",
        title: "정기 점검",
        paragraphs: [
          "전자금융운영부는 중요전자금융시스템의 복구 절차를 반기마다 시험해야 한다.",
          "시험 결과와 개선계획은 전자금융운영부장의 승인을 받아 3년간 보관해야 한다.",
        ],
        concepts: ["복구 절차", "정기 점검"],
      },
    ],
  },
};

export const demoOntologyNodes: OntologyNode[] = [
  { id: "doc:MOCK-EFO-001", type: "RegulationDocument", label: "전자금융업무 운영규정", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "metadata" },
  { id: "doc:MOCK-ISP-001", type: "RegulationDocument", label: "정보보호 운영규정", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "metadata" },
  { id: "org:전자금융운영부", type: "Organization", label: "전자금융운영부", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "metadata" },
  { id: "org:정보보호부", type: "Organization", label: "정보보호부", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "metadata" },
  { id: "org:업무연속성센터", type: "Organization", label: "업무연속성센터", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "제4조 제2항" },
  { id: "system:중요정보시스템", type: "System", label: "중요정보시스템", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항" },
  { id: "system:중요전자금융시스템", type: "System", label: "중요전자금융시스템", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "제5조 제1항" },
  { id: "actor:시스템소유부서", type: "Actor", label: "시스템 소유부서", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항" },
  { id: "obligation:분기접근권한검토", type: "Obligation", label: "분기 접근권한 검토", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항", description: "시스템 소유부서가 중요정보시스템 접근권한을 분기마다 검토하는 의무" },
  { id: "prohibition:계정공유금지", type: "Prohibition", label: "개인·관리계정 공유 금지", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제4조 제1항" },
  { id: "permission:긴급접근", type: "Permission", label: "중대한 장애·사고 시 긴급 접근", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제6조 제1항" },
  { id: "obligation:긴급접근사후승인", type: "Obligation", label: "긴급 접근 사후 승인", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제6조 제2항" },
  { id: "obligation:중대사고30분보고", type: "Obligation", label: "중대한 전자금융사고 30분 이내 보고", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "제4조 제2항" },
  { id: "obligation:로그5년보관", type: "Obligation", label: "접근·거래 로그 5년 보관", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "제5조 제2항" },
  { id: "control:월간로그무결성점검", type: "Control", label: "월간 로그 무결성 점검", securityClass: "internal", sourceDocument: "MOCK-EFO-001", sourceLocator: "제5조 제2항" },
  { id: "risk:무단접근", type: "Risk", label: "무단 접근", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항" },
  { id: "control:접근권한검토", type: "Control", label: "접근권한 정기 검토", securityClass: "internal", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항" },
];

export const demoOntologyEdges: OntologyEdge[] = [
  { id: "e01", type: "OWNED_BY", source: "doc:MOCK-EFO-001", target: "org:전자금융운영부", sourceDocument: "MOCK-EFO-001", sourceLocator: "metadata", reviewStatus: "APPROVED" },
  { id: "e02", type: "OWNED_BY", source: "doc:MOCK-ISP-001", target: "org:정보보호부", sourceDocument: "MOCK-ISP-001", sourceLocator: "metadata", reviewStatus: "APPROVED" },
  { id: "e04", type: "PERFORMED_BY", source: "obligation:분기접근권한검토", target: "actor:시스템소유부서", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항", reviewStatus: "APPROVED" },
  { id: "e05", type: "TARGETS", source: "obligation:분기접근권한검토", target: "system:중요정보시스템", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항", reviewStatus: "APPROVED" },
  { id: "e06", type: "IMPLEMENTED_BY", source: "obligation:분기접근권한검토", target: "control:접근권한검토", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항", reviewStatus: "APPROVED" },
  { id: "e07", type: "MITIGATES", source: "control:접근권한검토", target: "risk:무단접근", sourceDocument: "MOCK-ISP-001", sourceLocator: "제5조 제1항", reviewStatus: "APPROVED" },
  { id: "e09", type: "TARGETS", source: "permission:긴급접근", target: "system:중요정보시스템", sourceDocument: "MOCK-ISP-001", sourceLocator: "제6조 제1항", reviewStatus: "APPROVED" },
  { id: "e10", type: "RELATED_TO", source: "permission:긴급접근", target: "obligation:긴급접근사후승인", sourceDocument: "MOCK-ISP-001", sourceLocator: "제6조 제1항~제2항", reviewStatus: "APPROVED" },
  { id: "e11", type: "PERFORMED_BY", source: "obligation:중대사고30분보고", target: "org:업무연속성센터", sourceDocument: "MOCK-EFO-001", sourceLocator: "제4조 제2항", reviewStatus: "APPROVED" },
  { id: "e12", type: "TARGETS", source: "obligation:중대사고30분보고", target: "org:전자금융운영부", sourceDocument: "MOCK-EFO-001", sourceLocator: "제4조 제2항", reviewStatus: "APPROVED" },
  { id: "e13", type: "TARGETS", source: "obligation:중대사고30분보고", target: "org:정보보호부", sourceDocument: "MOCK-EFO-001", sourceLocator: "제4조 제2항", reviewStatus: "APPROVED" },
  { id: "e14", type: "TARGETS", source: "obligation:로그5년보관", target: "system:중요전자금융시스템", sourceDocument: "MOCK-EFO-001", sourceLocator: "제5조 제2항", reviewStatus: "APPROVED" },
  { id: "e15", type: "IMPLEMENTED_BY", source: "obligation:로그5년보관", target: "control:월간로그무결성점검", sourceDocument: "MOCK-EFO-001", sourceLocator: "제5조 제2항", reviewStatus: "APPROVED" },
  { id: "e21", type: "CROSS_REFERENCES", source: "doc:MOCK-EFO-001", target: "doc:MOCK-ISP-001", sourceDocument: "MOCK-EFO-001", sourceLocator: "제5조 제3항", reviewStatus: "APPROVED" },
];

export const demoOntologyGraph: OntologyGraph = {
  nodes: demoOntologyNodes,
  edges: demoOntologyEdges,
  truncated: false,
  publicationId: "mock-publication-2026-08-24",
  watermark: "mock-graph-2026-08-24T09:30:00Z",
};

export const demoSystemStatus: SystemStatus = {
  api: "healthy",
  graph: "healthy",
  publicationId: "mock-publication-2026-08-24",
  graphWatermark: "2026-08-24 09:30 KST",
  mode: "mock",
};

export const demoIngestionJobs: IngestionJob[] = [
  { id: "ING-2026-014", documentTitle: "정보보호 운영규정", version: "1.2 (초안)", ownerOrg: "정보보호부", state: "REVIEW_REQUIRED", progress: 58, issues: 2, updatedAt: "2026-08-24T14:35:00+09:00" },
  { id: "ING-2026-013", documentTitle: "전자금융업무 운영규정", version: "1.1 (초안)", ownerOrg: "전자금융운영부", state: "ENRICHING", progress: 76, issues: 0, updatedAt: "2026-08-24T13:12:00+09:00" },
  { id: "ING-2026-012", documentTitle: "개인정보 처리규정", version: "1.0", ownerOrg: "개인정보보호부", state: "READY_TO_PUBLISH", progress: 100, issues: 0, updatedAt: "2026-08-23T17:48:00+09:00" },
];

function citation(
  index: number,
  documentId: "MOCK-ISP-001" | "MOCK-EFO-001",
  provisionId: string,
  locator: string,
  quote: string,
  asOf: string,
): QaResponse["citations"][number] {
  const detail = demoRegulationDetails[documentId]!;
  const version = documentId === "MOCK-ISP-001" && asOf < "2026-07-01" ? ispVersions[1]! : detail.currentVersion;
  return {
    index,
    documentId,
    versionId: version.id,
    provisionId,
    documentTitle: detail.title,
    versionLabel: version.label,
    locator,
    quote,
  };
}

export function answerDemoQuestion(question: string, asOf: string): QaResponse {
  const normalized = question.replace(/\s/g, "").toLowerCase();
  const base = {
    queryId: `mock-query-${Date.now()}`,
    asOf,
    warnings: ["mock_data"],
    trace: {
      publicationId: "mock-publication-2026-08-24",
      graphMode: "healthy" as const,
      lanes: ["lexical", "vector", "graph"],
    },
  };

  if (normalized.includes("개인정보") || normalized.includes("파기")) {
    return {
      ...base,
      status: "abstained",
      answer: "현재 접근 범위에서 이 질문에 답변할 수 없습니다.",
      citations: [],
      reasonCode: "access_limited",
      suggestedActions: ["권한이 있는 담당 부서에 문의해 주세요.", "접근 가능한 업무 규정 범위로 질문을 좁혀 주세요."],
    };
  }

  if (normalized.includes("수수료") || normalized.includes("해외송금") || normalized.includes("한도")) {
    return {
      ...base,
      status: "abstained",
      answer: "등록된 규정에서 충분한 근거를 찾지 못했습니다.",
      citations: [],
      reasonCode: "insufficient_evidence",
      suggestedActions: ["질문에 대상 업무나 규정명을 추가해 주세요.", "담당 부서의 최신 업무 기준을 확인해 주세요."],
    };
  }

  if (normalized.includes("긴급") && normalized.includes("접근")) {
    return {
      ...base,
      status: "answered",
      answer: "중대한 장애 또는 보안사고 복구를 위해 긴급 접근계정을 최대 4시간 사용할 수 있습니다. 사용 종료 후 1영업일 이내에 작업 기록을 남기고 시스템 소유부장의 사후 승인을 받아야 합니다.",
      citations: [
        citation(1, "MOCK-ISP-001", "isp-art-6", "제6조 제1항", "중대한 장애 또는 보안사고의 복구를 위해 긴급 접근계정을 사용할 수 있으며 사용시간은 4시간을 초과할 수 없다.", asOf),
        citation(2, "MOCK-ISP-001", "isp-art-6", "제6조 제2항", "사용 종료 후 1영업일 이내에 목적, 수행 작업과 결과를 기록하고 시스템 소유부장의 사후 승인을 받아야 한다.", asOf),
      ],
    };
  }

  if (normalized.includes("사고") && (normalized.includes("보고") || normalized.includes("몇분"))) {
    return {
      ...base,
      status: "answered",
      answer: "중대한 전자금융사고는 인지 후 30분 이내에 전자금융운영부장과 정보보호부장에게 보고해야 합니다.",
      citations: [citation(1, "MOCK-EFO-001", "efo-art-4", "제4조 제2항", "업무연속성센터는 인지 후 30분 이내에 전자금융운영부장과 정보보호부장에게 보고해야 한다.", asOf)],
    };
  }

  if (normalized.includes("로그") && (normalized.includes("보관") || normalized.includes("점검"))) {
    return {
      ...base,
      status: "answered",
      answer: "중요전자금융시스템 로그는 위변조를 방지하는 방식으로 5년간 보관하며, 정보보호부가 매월 무결성을 점검해야 합니다.",
      citations: [citation(1, "MOCK-EFO-001", "efo-art-5", "제5조 제2항", "로그는 위변조를 방지하는 방식으로 5년간 보관하고 정보보호부가 매월 무결성을 점검해야 한다.", asOf)],
    };
  }

  if (normalized.includes("퇴직") && normalized.includes("권한")) {
    return {
      ...base,
      status: "answered",
      answer: "퇴직자의 모든 접근권한은 퇴직 효력 발생 후 24시간 이내에 회수해야 합니다.",
      citations: [citation(1, "MOCK-ISP-001", "isp-art-5", "제5조 제3항", "퇴직자의 모든 접근권한은 퇴직 효력 발생 후 24시간 이내에 회수해야 한다.", asOf)],
    };
  }

  if (normalized.includes("접근권한") || normalized.includes("권한검토")) {
    return {
      ...base,
      status: "answered",
      answer: "시스템 소유부서는 중요정보시스템의 접근권한을 분기마다 검토해야 합니다.",
      citations: [citation(1, "MOCK-ISP-001", "isp-art-5", "제5조 제1항", "시스템 소유부서는 중요정보시스템의 접근권한을 분기마다 검토해야 한다.", asOf)],
    };
  }

  return {
    ...base,
    status: "abstained",
    answer: "질문의 대상 업무와 시점을 특정하기 어려워 근거를 확정하지 못했습니다.",
    citations: [],
    reasonCode: "ambiguous_question",
    suggestedActions: ["대상 시스템이나 업무명을 포함해 질문해 주세요.", "규정명을 선택한 뒤 다시 질문해 주세요."],
  };
}
