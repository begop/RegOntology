import { useQuery } from "@tanstack/react-query";
import {
  ArrowRight,
  BookOpenText,
  Box,
  CheckCircle2,
  ChevronRight,
  CircleDot,
  Filter,
  Focus,
  GitBranch,
  Grid3X3,
  List,
  Network,
  RotateCcw,
  Search,
  ShieldCheck,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { OntologyGraph } from "../components/OntologyGraph";
import { OntologyGraph3D } from "../components/OntologyGraph3D";
import { Badge, EmptyState, ErrorState, LoadingState, PageHeader } from "../components/ui";
import { useAppContext } from "../context/AppContext";
import { getOntologyGraph } from "../lib/api";
import { nodeTypeLabel, relationLabel } from "../lib/format";
import { DEFAULT_CAMERA_3D } from "../lib/ontology3d";

const availableTypes = ["Obligation", "Prohibition", "Permission", "Organization", "Actor", "System", "Control", "Risk", "RegulationDocument"];

function sourceLink(documentId: string | undefined, locator: string | undefined): string {
  if (!documentId) return "/regulations";
  const query = locator ? `?locator=${encodeURIComponent(locator)}` : "";
  return `/regulations/${encodeURIComponent(documentId)}${query}`;
}

export function OntologyPage() {
  const { asOf, theme } = useAppContext();
  const [params, setParams] = useSearchParams();
  const [view, setView] = useState<"2d" | "3d" | "list">(() => (window.innerWidth < 768 ? "list" : "2d"));
  const [camera3D, setCamera3D] = useState(() => ({ ...DEFAULT_CAMERA_3D }));
  const [query, setQuery] = useState("");
  const [enabledTypes, setEnabledTypes] = useState(() => new Set(availableTypes));
  const graphQuery = useQuery({ queryKey: ["ontology", asOf], queryFn: () => getOntologyGraph(asOf) });
  const selectedId = params.get("node") ?? graphQuery.data?.nodes.find((node) => node.type === "Obligation")?.id;

  const visibleGraph = useMemo(() => {
    if (!graphQuery.data) return null;
    const term = query.trim().toLowerCase();
    const nodes = graphQuery.data.nodes.filter((node) => enabledTypes.has(node.type) && (!term || node.label.toLowerCase().includes(term) || node.type.toLowerCase().includes(term)));
    const ids = new Set(nodes.map((node) => node.id));
    const edges = graphQuery.data.edges.filter((edge) => ids.has(edge.source) && ids.has(edge.target));
    return { ...graphQuery.data, nodes, edges };
  }, [enabledTypes, graphQuery.data, query]);

  const selectNode = useCallback((id: string) => {
    const next = new URLSearchParams(params);
    next.set("node", id);
    setParams(next, { replace: true });
  }, [params, setParams]);

  const selectedNode = graphQuery.data?.nodes.find((node) => node.id === selectedId);
  const selectedEdges = graphQuery.data?.edges.filter((edge) => edge.source === selectedId || edge.target === selectedId) ?? [];
  const selectedProvenance = {
    documentId: selectedNode?.sourceDocument || selectedEdges[0]?.sourceDocument,
    locator: selectedNode?.sourceLocator || selectedEdges[0]?.sourceLocator,
  };

  function toggleType(type: string) {
    setEnabledTypes((current) => {
      const next = new Set(current);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }

  function reset() {
    setQuery("");
    setEnabledTypes(new Set(availableTypes));
    setCamera3D({ ...DEFAULT_CAMERA_3D });
    setParams({});
  }

  return (
    <div className="page ontology-page">
      <PageHeader
        eyebrow="Knowledge graph"
        title="Ontology Explorer"
        description="규정 관계를 2D 그래프, 3D 입체 캔버스, 접근 가능한 목록으로 탐색하고 조문 provenance를 확인합니다."
        actions={(
          <div className="view-switch" role="group" aria-label="Ontology 보기 방식">
            <button type="button" className={view === "2d" ? "active" : ""} aria-pressed={view === "2d"} onClick={() => setView("2d")}><Grid3X3 /> 2D 그래프</button>
            <button type="button" className={view === "3d" ? "active" : ""} aria-pressed={view === "3d"} onClick={() => setView("3d")}><Box /> 3D 캔버스</button>
            <button type="button" className={view === "list" ? "active" : ""} aria-pressed={view === "list"} onClick={() => setView("list")}><List /> 접근 가능한 목록</button>
          </div>
        )}
      />

      {graphQuery.isPending ? <LoadingState label="Ontology projection을 불러오고 있습니다." /> : null}
      {graphQuery.isError ? <ErrorState retry={() => void graphQuery.refetch()} /> : null}
      {visibleGraph ? (
        <div className="ontology-layout">
          <aside className="ontology-filters" aria-label="Ontology 필터">
            <div className="ontology-search"><Search /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="개념, 조직, 통제 검색" aria-label="Ontology 노드 검색" /></div>
            <div className="filter-section"><div className="filter-section__title"><span><Filter /> Node type</span><button onClick={() => setEnabledTypes(new Set(availableTypes))}>전체</button></div><div className="type-filter-list">{availableTypes.map((type) => <label key={type}><input type="checkbox" checked={enabledTypes.has(type)} onChange={() => toggleType(type)} /><span className={`node-swatch node-swatch--${type.toLowerCase()}`} /><span>{nodeTypeLabel(type)}</span><small>{graphQuery.data?.nodes.filter((node) => node.type === type).length ?? 0}</small></label>)}</div></div>
            <div className="filter-section"><div className="filter-section__title"><span><GitBranch /> 관계 유형</span></div><div className="relation-key"><span>수행 주체</span><span>대상</span><span>구현 통제</span><span>위험 완화</span></div></div>
            <button className="button button--secondary button--full" onClick={reset}><RotateCcw /> 보기 초기화</button>
            <div className="graph-security"><ShieldCheck /><p>권한 필터를 통과한 승인 관계만 표시합니다.</p></div>
          </aside>

          <section className="ontology-main" aria-label="Ontology 결과">
            <div className="graph-toolbar"><div><Network /><strong>Regulation knowledge graph</strong><Badge tone="success">APPROVED</Badge></div><div><span>Nodes <strong>{visibleGraph.nodes.length}</strong>/200</span><span>Edges <strong>{visibleGraph.edges.length}</strong></span><span>1 hop</span></div></div>
            {visibleGraph.nodes.length === 0 ? <EmptyState title="일치하는 노드가 없습니다." action={<button className="button button--secondary" onClick={reset}>필터 초기화</button>} /> : view === "2d" ? (
              <OntologyGraph nodes={visibleGraph.nodes} edges={visibleGraph.edges} selectedId={selectedId} onSelect={selectNode} />
            ) : view === "3d" ? (
              <OntologyGraph3D nodes={visibleGraph.nodes} edges={visibleGraph.edges} selectedId={selectedId} onSelect={selectNode} onRequestList={() => setView("list")} camera={camera3D} setCamera={setCamera3D} theme={theme} />
            ) : (
              <div className="ontology-list-view">
                <table><caption className="sr-only">Ontology 노드 목록</caption><thead><tr><th scope="col">노드</th><th scope="col">유형</th><th scope="col">근거 규정</th><th scope="col">연결</th><th scope="col"><span className="sr-only">선택</span></th></tr></thead><tbody>{visibleGraph.nodes.map((node) => <tr key={node.id} className={selectedId === node.id ? "selected" : ""}><td><span className={`node-swatch node-swatch--${node.type.toLowerCase()}`} /><strong>{node.label}</strong></td><td>{nodeTypeLabel(node.type)}</td><td>{node.sourceDocument || "—"}<small>{node.sourceLocator}</small></td><td>{visibleGraph.edges.filter((edge) => edge.source === node.id || edge.target === node.id).length}개</td><td><button onClick={() => selectNode(node.id)}>상세 <ChevronRight /></button></td></tr>)}</tbody></table>
              </div>
            )}
            <div className="graph-statusbar"><div><span className="status-dot status-dot--ok" /> Projection 동기화됨</div><span>{view === "3d" ? "3D perspective" : view === "2d" ? "2D graph" : "Accessible list"}</span><span>Watermark {visibleGraph.watermark}</span><span>최대 200 nodes · 깊이 1–2</span></div>
          </section>

          <aside className="node-detail-panel" aria-label="선택한 노드 상세">
            {selectedNode ? (
              <>
                <div className="node-detail__header"><span className={`node-large-icon node-large-icon--${selectedNode.type.toLowerCase()}`}><CircleDot /></span><Badge tone="success"><CheckCircle2 /> APPROVED</Badge><p>{nodeTypeLabel(selectedNode.type)}</p><h2>{selectedNode.label}</h2></div>
                <section><h3>정의</h3><p>{selectedNode.description || `${selectedNode.label}에 대한 검토·승인된 규정 지식 개념입니다.`}</p></section>
                <section><div className="section-title-inline"><h3>연결 관계</h3><Badge>{selectedEdges.length}</Badge></div><div className="node-relations">{selectedEdges.length ? selectedEdges.map((edge) => { const otherId = edge.source === selectedNode.id ? edge.target : edge.source; const other = graphQuery.data?.nodes.find((node) => node.id === otherId); return <button key={edge.id} onClick={() => selectNode(otherId)}><span>{relationLabel(edge.type)}</span><strong>{other?.label ?? otherId}</strong><ArrowRight /></button>; }) : <p>현재 필터에서 표시할 직접 관계가 없습니다.</p>}</div></section>
                <section className="provenance-card"><div className="section-title-inline"><h3>근거 provenance</h3><ShieldCheck /></div><dl><div><dt>문서</dt><dd>{selectedProvenance.documentId || "승인 메타데이터"}</dd></div><div><dt>위치</dt><dd>{selectedProvenance.locator || "metadata"}</dd></div><div><dt>검토 상태</dt><dd>APPROVED</dd></div></dl><Link className="button button--primary button--full" to={sourceLink(selectedProvenance.documentId, selectedProvenance.locator)}><BookOpenText /> 근거 조문 열기</Link></section>
                <button className="button button--secondary button--full"><Focus /> 이 노드에서 1-hop 확장</button>
              </>
            ) : <EmptyState title="노드를 선택해 주세요." description="2D·3D 그래프 또는 접근 가능한 목록에서 노드를 선택하면 관계와 근거를 표시합니다." />}
          </aside>
        </div>
      ) : null}
    </div>
  );
}
