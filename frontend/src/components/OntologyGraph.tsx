import cytoscape, { type Core, type ElementDefinition, type StylesheetStyle } from "cytoscape";
import { Focus, Minus, Plus } from "lucide-react";
import { useEffect, useRef } from "react";
import type { OntologyEdge, OntologyNode } from "../lib/types";

export function OntologyGraph({
  nodes,
  edges,
  selectedId,
  onSelect,
}: {
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  selectedId?: string;
  onSelect: (id: string) => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const coreRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const elements: ElementDefinition[] = [
      ...nodes.map((node) => ({
        data: { id: node.id, label: node.label, type: node.type },
        classes: node.id === selectedId ? "selected" : "",
      })),
      ...edges.map((edge) => ({
        data: { id: edge.id, source: edge.source, target: edge.target, label: edge.type },
      })),
    ];
    const styles: StylesheetStyle[] = [
      {
        selector: "node",
        style: {
          label: "data(label)",
          shape: "ellipse",
          "background-color": "#dbe6ef",
          "border-color": "#70869a",
          "border-width": 1.5,
          color: "#15344e",
          "font-family": "system-ui, sans-serif",
          "font-size": 10,
          "font-weight": 600,
          width: 64,
          height: 42,
          padding: "8px",
          "text-wrap": "wrap",
          "text-max-width": "90px",
          "text-valign": "center",
          "text-halign": "center",
          "overlay-opacity": 0,
        },
      },
      { selector: "node[type = 'Obligation']", style: { shape: "rectangle", "background-color": "#dcecff", "border-color": "#1d6fd6", color: "#12477f" } },
      { selector: "node[type = 'Prohibition']", style: { shape: "octagon", "background-color": "#fee7e5", "border-color": "#c84b46", color: "#7d2a26" } },
      { selector: "node[type = 'Permission']", style: { "background-color": "#d9f4ef", "border-color": "#168a79", color: "#0d6357" } },
      { selector: "node[type = 'Organization'], node[type = 'Actor']", style: { shape: "hexagon", "background-color": "#eee8ff", "border-color": "#7658bf", color: "#4e3789" } },
      { selector: "node[type = 'Control']", style: { shape: "round-rectangle", "background-color": "#e1f3e8", "border-color": "#278352", color: "#1b633f" } },
      { selector: "node[type = 'Risk']", style: { "background-color": "#fff0df", "border-color": "#bf7020", color: "#78450e" } },
      { selector: "node[type = 'RegulationDocument']", style: { shape: "round-rectangle", "background-color": "#163f61", "border-color": "#0b2f4f", color: "#ffffff", width: 76 } },
      { selector: "node.selected", style: { "border-width": 4, "border-color": "#ff9d2e", "underlay-color": "#ffb45f", "underlay-opacity": 0.16, "underlay-padding": 8 } },
      {
        selector: "edge",
        style: {
          width: 1.5,
          "line-color": "#9aabba",
          "target-arrow-color": "#758b9f",
          "target-arrow-shape": "triangle",
          "curve-style": "bezier",
          label: "data(label)",
          color: "#5c7184",
          "font-size": 7,
          "text-background-color": "#f7fafc",
          "text-background-opacity": 0.9,
          "text-background-padding": "2px",
          "text-rotation": "autorotate",
          "overlay-opacity": 0,
        },
      },
    ];

    const cy = cytoscape({
      container: containerRef.current,
      elements,
      style: styles,
      minZoom: 0.35,
      maxZoom: 2.2,
      wheelSensitivity: 0.18,
      layout: { name: "cose", animate: false, fit: true, padding: 38, nodeRepulsion: () => 5200, idealEdgeLength: () => 95 },
    });
    coreRef.current = cy;
    cy.on("tap", "node", (event) => onSelect(event.target.id()));
    return () => {
      coreRef.current = null;
      cy.destroy();
    };
  }, [edges, nodes, onSelect, selectedId]);

  return (
    <div className="cytoscape-shell">
      <div ref={containerRef} className="cytoscape-canvas" role="img" aria-label={`${nodes.length}개 노드와 ${edges.length}개 관계를 표시한 규정 온톨로지 그래프`} />
      <div className="graph-zoom-controls" aria-label="그래프 확대 축소">
        <button onClick={() => coreRef.current?.zoom({ level: Math.min((coreRef.current?.zoom() ?? 1) + 0.2, 2.2), renderedPosition: { x: 300, y: 220 } })} aria-label="확대"><Plus /></button>
        <button onClick={() => coreRef.current?.zoom({ level: Math.max((coreRef.current?.zoom() ?? 1) - 0.2, 0.35), renderedPosition: { x: 300, y: 220 } })} aria-label="축소"><Minus /></button>
        <button onClick={() => coreRef.current?.fit(undefined, 36)} aria-label="화면에 맞춤"><Focus /></button>
      </div>
    </div>
  );
}
