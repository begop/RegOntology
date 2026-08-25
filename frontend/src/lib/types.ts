export type SecurityClass = "public" | "internal" | "restricted";
export type RegulationState = "PUBLISHED" | "SUPERSEDED" | "REVIEW_REQUIRED";

export interface RegulationVersion {
  id: string;
  label: string;
  effectiveFrom: string;
  effectiveTo: string | null;
  status: RegulationState;
}

export interface Provision {
  id: string;
  locator: string;
  title: string;
  paragraphs: string[];
  concepts: string[];
}

export interface RegulationSummary {
  id: string;
  code: string;
  title: string;
  ownerOrg: string;
  documentType: string;
  securityClass: SecurityClass;
  isMock: boolean;
  currentVersion: RegulationVersion;
  snippet?: string;
  tags: string[];
}

export interface RegulationDetail extends RegulationSummary {
  institution: string;
  versions: RegulationVersion[];
  provisions: Provision[];
  relatedNodeIds: string[];
}

export type QaStatus = "answered" | "partially_answered" | "abstained";

export interface Citation {
  index: number;
  documentId: string;
  versionId: string;
  provisionId: string;
  documentTitle: string;
  versionLabel: string;
  locator: string;
  quote: string;
}

export interface QaResponse {
  queryId: string;
  status: QaStatus;
  answer: string;
  asOf: string;
  citations: Citation[];
  warnings: string[];
  reasonCode?:
    | "insufficient_evidence"
    | "access_limited"
    | "ambiguous_question"
    | "system_unavailable";
  suggestedActions?: string[];
  trace: {
    publicationId: string;
    graphMode: "healthy" | "degraded";
    lanes?: string[];
  };
}

export interface OntologyNode {
  id: string;
  type: string;
  label: string;
  securityClass: SecurityClass;
  sourceDocument?: string;
  sourceLocator?: string;
  description?: string;
}

export interface OntologyEdge {
  id: string;
  type: string;
  source: string;
  target: string;
  sourceDocument: string;
  sourceLocator: string;
  reviewStatus: "APPROVED" | "PROPOSED";
}

export interface OntologyGraph {
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  truncated: boolean;
  publicationId: string;
  watermark: string;
}

export interface SystemStatus {
  api: "healthy" | "degraded";
  graph: "healthy" | "degraded" | "stale";
  publicationId: string;
  graphWatermark: string;
  mode: "mock" | "live";
}

export interface IngestionJob {
  id: string;
  documentTitle: string;
  version: string;
  ownerOrg: string;
  state: "REVIEW_REQUIRED" | "ENRICHING" | "READY_TO_PUBLISH" | "FAILED";
  progress: number;
  issues: number;
  updatedAt: string;
}
