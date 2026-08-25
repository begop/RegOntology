import {
  answerDemoQuestion,
  demoOntologyGraph,
  demoRegulationDetails,
  demoRegulations,
  demoSystemStatus,
} from "../data/demo";
import type {
  Citation,
  OntologyEdge,
  OntologyGraph,
  OntologyNode,
  QaResponse,
  RegulationDetail,
  RegulationSummary,
  RegulationVersion,
  SecurityClass,
  SystemStatus,
} from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? "/api/v1").replace(/\/$/, "");
const DEMO_FALLBACK = import.meta.env.VITE_DEMO_MODE !== "false";
const REQUEST_TIMEOUT = Number(import.meta.env.VITE_API_TIMEOUT_MS ?? 2500);

type JsonObject = Record<string, unknown>;

function isObject(value: unknown): value is JsonObject {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function textValue(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function boolValue(value: unknown, fallback = false): boolean {
  return typeof value === "boolean" ? value : fallback;
}

function arrayValue(value: unknown): unknown[] {
  return Array.isArray(value) ? value : [];
}

function nestedStringValues(value: unknown): string[] {
  return arrayValue(value).flatMap((item) =>
    typeof item === "string"
      ? [item]
      : arrayValue(item).filter((nested): nested is string => typeof nested === "string"),
  );
}

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly code = "api_error",
  ) {
    super(message);
  }
}

async function fetchJsonResponse(
  path: string,
  init?: RequestInit,
): Promise<{ payload: unknown; response: Response }> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        "X-Demo-Role": "employee",
        "X-Demo-Security-Classes": "internal,public",
        ...init?.headers,
      },
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      const envelope = isObject(payload) && isObject(payload.error) ? payload.error : null;
      throw new ApiError(
        textValue(envelope?.message, "요청을 처리하지 못했습니다."),
        response.status,
        textValue(envelope?.code, "api_error"),
      );
    }
    return { payload, response };
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      error instanceof DOMException && error.name === "AbortError"
        ? "서버 응답 시간이 초과되었습니다."
        : "API 서버에 연결할 수 없습니다.",
      0,
      "network_unavailable",
    );
  } finally {
    window.clearTimeout(timer);
  }
}

async function fetchJson(path: string, init?: RequestInit): Promise<unknown> {
  return (await fetchJsonResponse(path, init)).payload;
}

async function withDemoFallback<T>(request: () => Promise<T>, fallback: () => T): Promise<T> {
  try {
    return await request();
  } catch (error) {
    if (!DEMO_FALLBACK || (error instanceof ApiError && [401, 403].includes(error.status))) {
      throw error;
    }
    return fallback();
  }
}

function normalizeVersion(raw: unknown, documentId: string): RegulationVersion {
  const value = isObject(raw) ? raw : {};
  const label = textValue(value.label ?? value.version ?? value.version_label, "1.0");
  const state = textValue(value.status, "PUBLISHED").toUpperCase();
  return {
    id: textValue(value.id ?? value.version_id, `${documentId}:v${label}`),
    label,
    effectiveFrom: textValue(value.effectiveFrom ?? value.effective_from, "2026-01-01"),
    effectiveTo: textValue(value.effectiveTo ?? value.effective_to) || null,
    status: state === "SUPERSEDED" ? "SUPERSEDED" : state === "REVIEW_REQUIRED" ? "REVIEW_REQUIRED" : "PUBLISHED",
  };
}

function normalizeRegulation(raw: unknown): RegulationSummary {
  const value = isObject(raw) ? raw : {};
  const id = textValue(value.id ?? value.document_id ?? value.code, "unknown");
  const rawCurrent = value.currentVersion ?? value.current_version ?? value.effective_version ?? value.version;
  return {
    id,
    code: textValue(value.code ?? value.document_code ?? value.document_id, id),
    title: textValue(value.title, "제목 없는 규정"),
    ownerOrg: textValue(value.ownerOrg ?? value.owner_org ?? value.owner, "담당 부서 미지정"),
    documentType: textValue(value.documentType ?? value.document_type, "규정"),
    securityClass: textValue(value.securityClass ?? value.security_class, "internal") as SecurityClass,
    isMock: boolValue(value.isMock ?? value.is_mock, false),
    currentVersion: normalizeVersion(rawCurrent, id),
    snippet:
      textValue(value.snippet ?? value.match_snippet) ||
      arrayValue(value.match_snippets).filter((item): item is string => typeof item === "string").join(" · "),
    tags: arrayValue(value.tags).filter((item): item is string => typeof item === "string"),
  };
}

function selectDemoVersion(detail: RegulationDetail, asOf: string): RegulationDetail {
  const effective = detail.versions.find(
    (version) => version.effectiveFrom <= asOf && (!version.effectiveTo || asOf < version.effectiveTo),
  );
  return effective ? { ...detail, currentVersion: effective } : detail;
}

export async function getRegulations(params: {
  query?: string;
  asOf: string;
  ownerOrg?: string;
  securityClass?: string;
}): Promise<RegulationSummary[]> {
  const query = new URLSearchParams({ as_of: params.asOf, limit: "50" });
  if (params.query) query.set("q", params.query);
  if (params.ownerOrg) query.set("owner_org", params.ownerOrg);
  if (params.securityClass) query.set("security_class", params.securityClass);

  return withDemoFallback(
    async () => {
      const payload = await fetchJson(`/regulations?${query}`);
      const items = Array.isArray(payload) ? payload : isObject(payload) ? payload.items ?? payload.results : [];
      return arrayValue(items).map(normalizeRegulation);
    },
    () => {
      const term = (params.query ?? "").trim().toLowerCase();
      return demoRegulations
        .map((item) => selectDemoVersion(demoRegulationDetails[item.id]!, params.asOf))
        .filter((item) => !params.ownerOrg || item.ownerOrg === params.ownerOrg)
        .filter((item) => !params.securityClass || item.securityClass === params.securityClass)
        .filter(
          (item) =>
            !term ||
            [item.title, item.code, item.ownerOrg, item.snippet, ...item.tags]
              .filter(Boolean)
              .some((value) => value!.toLowerCase().includes(term)),
        );
    },
  );
}

export async function getRegulationDetail(
  documentId: string,
  versionId: string | undefined,
  asOf: string,
): Promise<RegulationDetail> {
  return withDemoFallback(
    async () => {
      const documentPayload = await fetchJson(`/regulations/${encodeURIComponent(documentId)}`);
      const document = normalizeRegulation(documentPayload);
      const documentObject = isObject(documentPayload) ? documentPayload : {};
      const versions = arrayValue(documentObject.versions).map((item) => normalizeVersion(item, documentId));
      const selectedVersion =
        versions.find((item) => item.id === versionId) ??
        versions.find((item) => item.effectiveFrom <= asOf && (!item.effectiveTo || asOf < item.effectiveTo)) ??
        document.currentVersion;
      const provisionsPayload = await fetchJson(
        `/regulations/${encodeURIComponent(documentId)}/versions/${encodeURIComponent(selectedVersion.id)}/provisions?depth=3&limit=100`,
      );
      const rawProvisions = Array.isArray(provisionsPayload)
        ? provisionsPayload
        : isObject(provisionsPayload)
          ? provisionsPayload.items ?? provisionsPayload.provisions
          : [];
      return {
        ...document,
        currentVersion: selectedVersion,
        institution: textValue(documentObject.institution, "금융기관"),
        versions: versions.length ? versions : [selectedVersion],
        relatedNodeIds: arrayValue(documentObject.related_node_ids).filter((item): item is string => typeof item === "string"),
        provisions: arrayValue(rawProvisions).map((raw, index) => {
          const value = isObject(raw) ? raw : {};
          return {
            id: textValue(value.id ?? value.provision_id, `${documentId}-p-${index + 1}`),
            locator: textValue(value.locator, `조문 ${index + 1}`),
            title: textValue(value.title),
            paragraphs: arrayValue(value.paragraphs ?? value.children).length
              ? arrayValue(value.paragraphs ?? value.children).map((item) =>
                  typeof item === "string" ? item : isObject(item) ? textValue(item.text ?? item.content) : "",
                ).filter(Boolean)
              : [textValue(value.body ?? value.text ?? value.content)].filter(Boolean),
            concepts: arrayValue(value.concepts).filter((item): item is string => typeof item === "string"),
          };
        }),
      };
    },
    () => {
      const detail = demoRegulationDetails[documentId];
      if (!detail) throw new ApiError("규정을 찾을 수 없습니다.", 404, "not_found");
      const selected = versionId
        ? detail.versions.find((version) => version.id === versionId || version.label === versionId.replace(/^v/, ""))
        : undefined;
      return { ...selectDemoVersion(detail, asOf), currentVersion: selected ?? selectDemoVersion(detail, asOf).currentVersion };
    },
  );
}

function normalizeCitation(raw: unknown, index: number): Citation {
  const value = isObject(raw) ? raw : {};
  return {
    index: typeof value.index === "number" ? value.index : index + 1,
    documentId: textValue(value.documentId ?? value.document_id),
    versionId: textValue(value.versionId ?? value.version_id),
    provisionId: textValue(value.provisionId ?? value.provision_id),
    documentTitle: textValue(value.documentTitle ?? value.document_title),
    versionLabel: textValue(value.versionLabel ?? value.version_label),
    locator: textValue(value.locator),
    quote: textValue(value.quote),
  };
}

function normalizeQaResponse(raw: unknown): QaResponse {
  const value = isObject(raw) ? raw : {};
  const trace = isObject(value.trace) ? value.trace : {};
  return {
    queryId: textValue(value.queryId ?? value.query_id),
    status: textValue(value.status, "abstained") as QaResponse["status"],
    answer: textValue(value.answer),
    asOf: textValue(value.asOf ?? value.as_of),
    citations: arrayValue(value.citations).map(normalizeCitation),
    warnings: arrayValue(value.warnings).filter((item): item is string => typeof item === "string"),
    reasonCode: textValue(value.reasonCode ?? value.reason_code) as QaResponse["reasonCode"],
    suggestedActions: arrayValue(value.suggestedActions ?? value.suggested_actions).filter(
      (item): item is string => typeof item === "string",
    ),
    trace: {
      publicationId: textValue(trace.publicationId ?? trace.publication_id),
      graphMode: ["healthy", "neo4j_projection"].includes(textValue(trace.graphMode ?? trace.graph_mode)) ? "healthy" : "degraded",
      lanes: [...new Set(nestedStringValues(trace.lanes))],
    },
  };
}

export async function askQuestion(question: string, asOf: string): Promise<QaResponse> {
  return withDemoFallback(
    async () => {
      const response = await fetchJson("/qa/queries", {
        method: "POST",
        body: JSON.stringify({
          question,
          as_of: asOf,
          scope: { document_ids: [], owner_org_ids: [] },
          conversation_id: null,
          stream: false,
        }),
      });
      return normalizeQaResponse(response);
    },
    () => answerDemoQuestion(question, asOf),
  );
}

function normalizeNode(raw: unknown): OntologyNode {
  const value = isObject(raw) ? raw : {};
  const properties = isObject(value.properties) ? value.properties : {};
  return {
    id: textValue(value.id),
    type: textValue(value.type ?? value.node_type ?? properties.type),
    label: textValue(value.label ?? value.name ?? properties.label),
    securityClass: textValue(value.securityClass ?? value.security_class ?? properties.security_class, "internal") as SecurityClass,
    sourceDocument: textValue(value.sourceDocument ?? value.source_document ?? properties.source_document),
    sourceLocator: textValue(value.sourceLocator ?? value.source_locator ?? properties.source_locator),
    description: textValue(value.description ?? properties.description),
  };
}

function normalizeEdge(raw: unknown): OntologyEdge {
  const value = isObject(raw) ? raw : {};
  return {
    id: textValue(value.id),
    type: textValue(value.type ?? value.relation_type),
    source: textValue(value.source ?? value.source_id),
    target: textValue(value.target ?? value.target_id),
    sourceDocument: textValue(value.sourceDocument ?? value.source_document),
    sourceLocator: textValue(value.sourceLocator ?? value.source_locator),
    reviewStatus: textValue(value.reviewStatus ?? value.review_status, "APPROVED") as OntologyEdge["reviewStatus"],
  };
}

export async function getOntologyGraph(asOf: string): Promise<OntologyGraph> {
  return withDemoFallback(
    async () => {
      const query = new URLSearchParams({ depth: "1", max_nodes: "50", as_of: asOf });
      const payload = await fetchJson(`/ontology/subgraph?${query}`);
      const value = isObject(payload) ? payload : {};
      return {
        nodes: arrayValue(value.nodes).map(normalizeNode),
        edges: arrayValue(value.edges).map(normalizeEdge),
        truncated: boolValue(value.truncated),
        publicationId: textValue(value.publicationId ?? value.publication_id),
        watermark: textValue(value.watermark ?? value.graph_watermark),
      };
    },
    () => demoOntologyGraph,
  );
}

export async function getSystemStatus(): Promise<SystemStatus> {
  return withDemoFallback(
    async () => {
      const { payload, response } = await fetchJsonResponse("/health");
      const value = isObject(payload) ? payload : {};
      const apiState = textValue(value.api ?? value.status, "degraded");
      const graphState = textValue(
        value.graphStatus ?? value.graph_status,
        apiState,
      );
      const repositoryMode = textValue(value.mode ?? value.repository_mode, "live");
      const healthy = ["healthy", "ok", "ready"].includes(apiState);
      return {
        api: healthy ? "healthy" : "degraded",
        graph:
          graphState === "healthy"
            ? "healthy"
            : graphState === "stale"
              ? "stale"
              : "degraded",
        publicationId:
          textValue(value.publicationId ?? value.publication_id) ||
          response.headers.get("X-Publication-ID") ||
          "",
        graphWatermark:
          textValue(value.graphWatermark ?? value.graph_watermark) ||
          response.headers.get("X-Graph-Watermark") ||
          "",
        mode: /mock|memory|fixture/i.test(repositoryMode) ? "mock" : "live",
      };
    },
    () => demoSystemStatus,
  );
}
