import { Focus, Minus, Plus, RotateCcw, RotateCw } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type Dispatch, type PointerEvent, type SetStateAction } from "react";
import { nodeTypeLabel, relationLabel } from "../lib/format";
import { createSpatialLayout, DEFAULT_CAMERA_3D, projectSpatialPoint, type Camera3D, type ProjectedPoint } from "../lib/ontology3d";
import type { OntologyEdge, OntologyNode } from "../lib/types";

interface RenderedNode extends ProjectedPoint {
  id: string;
  label: string;
  type: string;
  radius: number;
}

interface DragState {
  pointerId: number;
  startX: number;
  startY: number;
  lastX: number;
  lastY: number;
  moved: boolean;
}

const nodePalette: Record<string, { fill: string; stroke: string }> = {
  Obligation: { fill: "#dcecff", stroke: "#1d6fd6" },
  Prohibition: { fill: "#fee7e5", stroke: "#c84b46" },
  Permission: { fill: "#d9f4ef", stroke: "#168a79" },
  Organization: { fill: "#eee8ff", stroke: "#7658bf" },
  Actor: { fill: "#eee8ff", stroke: "#7658bf" },
  Control: { fill: "#e1f3e8", stroke: "#278352" },
  Risk: { fill: "#fff0df", stroke: "#bf7020" },
  RegulationDocument: { fill: "#163f61", stroke: "#0b2f4f" },
};

const relationPalette: Record<string, string> = {
  OWNED_BY: "#7658bf",
  PERFORMED_BY: "#7658bf",
  TARGETS: "#1d6fd6",
  IMPLEMENTED_BY: "#278352",
  MITIGATES: "#bf7020",
  RELATED_TO: "#168a79",
  CROSS_REFERENCES: "#5d7184",
};

function polygonPath(context: CanvasRenderingContext2D, x: number, y: number, radius: number, sides: number, rotation = -Math.PI / 2) {
  context.beginPath();
  for (let index = 0; index < sides; index += 1) {
    const angle = rotation + (Math.PI * 2 * index) / sides;
    const pointX = x + Math.cos(angle) * radius;
    const pointY = y + Math.sin(angle) * radius;
    if (index === 0) context.moveTo(pointX, pointY);
    else context.lineTo(pointX, pointY);
  }
  context.closePath();
}

function roundedRectanglePath(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  const left = x - width / 2;
  const top = y - height / 2;
  const safeRadius = Math.min(radius, width / 2, height / 2);
  context.beginPath();
  context.moveTo(left + safeRadius, top);
  context.lineTo(left + width - safeRadius, top);
  context.quadraticCurveTo(left + width, top, left + width, top + safeRadius);
  context.lineTo(left + width, top + height - safeRadius);
  context.quadraticCurveTo(left + width, top + height, left + width - safeRadius, top + height);
  context.lineTo(left + safeRadius, top + height);
  context.quadraticCurveTo(left, top + height, left, top + height - safeRadius);
  context.lineTo(left, top + safeRadius);
  context.quadraticCurveTo(left, top, left + safeRadius, top);
  context.closePath();
}

function nodePath(context: CanvasRenderingContext2D, node: RenderedNode) {
  if (node.type === "Obligation") {
    roundedRectanglePath(context, node.x, node.y, node.radius * 2.15, node.radius * 1.65, 3);
  } else if (node.type === "Prohibition") {
    polygonPath(context, node.x, node.y, node.radius * 1.1, 8);
  } else if (node.type === "Organization" || node.type === "Actor") {
    polygonPath(context, node.x, node.y, node.radius * 1.12, 6);
  } else if (node.type === "Control" || node.type === "RegulationDocument") {
    roundedRectanglePath(context, node.x, node.y, node.radius * 2.45, node.radius * 1.65, node.radius * 0.45);
  } else if (node.type === "Risk") {
    polygonPath(context, node.x, node.y, node.radius * 1.1, 4, Math.PI / 4);
  } else {
    context.beginPath();
    context.arc(node.x, node.y, node.radius, 0, Math.PI * 2);
  }
}

function canvasColour(element: HTMLElement, variableName: string, fallback: string): string {
  const value = getComputedStyle(element).getPropertyValue(variableName).trim();
  return value || fallback;
}

export function OntologyGraph3D({
  nodes,
  edges,
  selectedId,
  onSelect,
  onRequestList,
  camera,
  setCamera,
  theme,
}: {
  nodes: OntologyNode[];
  edges: OntologyEdge[];
  selectedId?: string;
  onSelect: (id: string) => void;
  onRequestList: () => void;
  camera: Camera3D;
  setCamera: Dispatch<SetStateAction<Camera3D>>;
  theme: "light" | "dark";
}) {
  const shellRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const renderedNodesRef = useRef<RenderedNode[]>([]);
  const dragRef = useRef<DragState | null>(null);
  const [size, setSize] = useState({ width: 760, height: 590 });
  const [hoveredId, setHoveredId] = useState<string>();
  const [rendererError, setRendererError] = useState(false);
  const [renderGeneration, setRenderGeneration] = useState(0);
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const layout = useMemo(() => createSpatialLayout(nodes, edges), [edges, nodes]);

  const renderedNodes = useMemo(() => nodes.flatMap((node) => {
    const point = layout.get(node.id);
    if (!point) return [];
    const projected = projectSpatialPoint(point, camera, size.width, size.height);
    if (!projected.visible) return [];
    return [{
      ...projected,
      id: node.id,
      label: node.label,
      type: node.type,
      radius: Math.min(Math.max(11 * projected.scale + 4, 8), 19),
    } satisfies RenderedNode];
  }), [camera, layout, nodes, size.height, size.width]);

  renderedNodesRef.current = renderedNodes;

  useEffect(() => {
    const shell = shellRef.current;
    if (!shell) return;

    const resize = () => {
      const rectangle = shell.getBoundingClientRect();
      setSize({
        width: Math.max(Math.floor(rectangle.width || shell.clientWidth || 760), 320),
        height: Math.max(Math.floor(rectangle.height || shell.clientHeight || 590), 420),
      });
    };
    resize();

    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", resize);
      return () => window.removeEventListener("resize", resize);
    }

    const observer = new ResizeObserver(resize);
    observer.observe(shell);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const targetWidth = Math.round(size.width * pixelRatio);
    const targetHeight = Math.round(size.height * pixelRatio);
    if (canvas.width !== targetWidth) canvas.width = targetWidth;
    if (canvas.height !== targetHeight) canvas.height = targetHeight;
  }, [pixelRatio, size.height, size.width]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const handleNativeWheel = (event: globalThis.WheelEvent) => {
      if (event.ctrlKey || event.metaKey || event.deltaY === 0) return;
      event.preventDefault();
      const direction = event.deltaY > 0 ? -0.08 : 0.08;
      setCamera((current) => ({ ...current, zoom: Math.min(Math.max(current.zoom + direction, 0.6), 1.9) }));
    };
    const handleContextLost = (event: Event) => {
      event.preventDefault();
      setRendererError(true);
    };
    const handleContextRestored = () => {
      setRendererError(false);
      setRenderGeneration((current) => current + 1);
    };

    canvas.addEventListener("wheel", handleNativeWheel, { passive: false });
    canvas.addEventListener("contextlost", handleContextLost);
    canvas.addEventListener("contextrestored", handleContextRestored);
    return () => {
      canvas.removeEventListener("wheel", handleNativeWheel);
      canvas.removeEventListener("contextlost", handleContextLost);
      canvas.removeEventListener("contextrestored", handleContextRestored);
    };
  }, [setCamera]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const shell = shellRef.current;
    if (!canvas || !shell) return;

    try {
      const context = canvas.getContext("2d");
      if (!context) throw new Error("Canvas2D context unavailable");

      context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
      context.clearRect(0, 0, size.width, size.height);

      const edgeColour = canvasColour(shell, "--ontology-3d-edge", "#8195a7");
      const selectedColour = canvasColour(shell, "--ontology-3d-selected", "#ff9d2e");
      const labelBackground = canvasColour(shell, "--ontology-3d-label-bg", "rgba(247, 250, 252, 0.9)");
      const labelText = canvasColour(shell, "--ontology-3d-label", "#15344e");
      const projectedById = new Map(renderedNodes.map((node) => [node.id, node]));
      const depths = renderedNodes.map((node) => node.depth);
      const minDepth = Math.min(...depths, 0);
      const maxDepth = Math.max(...depths, 1);
      const depthRange = Math.max(maxDepth - minDepth, 1);

      const visibleEdges = edges.flatMap((edge) => {
        const source = projectedById.get(edge.source);
        const target = projectedById.get(edge.target);
        return source && target ? [{ edge, source, target, depth: (source.depth + target.depth) / 2 }] : [];
      }).sort((left, right) => left.depth - right.depth);

      for (const { edge, source, target, depth } of visibleEdges) {
        const selected = edge.source === selectedId || edge.target === selectedId;
        const highlighted = selected || edge.source === hoveredId || edge.target === hoveredId;
        const angle = Math.atan2(target.y - source.y, target.x - source.x);
        const arrowSize = selected ? 7 : 5;
        const sourcePadding = source.radius + 2;
        const targetPadding = target.radius + 3;
        const startX = source.x + Math.cos(angle) * sourcePadding;
        const startY = source.y + Math.sin(angle) * sourcePadding;
        const endX = target.x - Math.cos(angle) * targetPadding;
        const endY = target.y - Math.sin(angle) * targetPadding;
        const typeColour = relationPalette[edge.type] ?? edgeColour;
        context.save();
        context.globalAlpha = selected ? 0.96 : 0.32 + ((depth - minDepth) / depthRange) * 0.46;
        context.strokeStyle = selected ? selectedColour : typeColour;
        context.fillStyle = selected ? selectedColour : typeColour;
        context.lineWidth = selected ? 2.6 : highlighted ? 1.9 : 1.35;
        context.beginPath();
        context.moveTo(startX, startY);
        context.lineTo(endX, endY);
        context.stroke();
        context.beginPath();
        context.moveTo(endX, endY);
        context.lineTo(endX - Math.cos(angle - 0.45) * arrowSize, endY - Math.sin(angle - 0.45) * arrowSize);
        context.lineTo(endX - Math.cos(angle + 0.45) * arrowSize, endY - Math.sin(angle + 0.45) * arrowSize);
        context.closePath();
        context.fill();

        if (highlighted || visibleEdges.length <= 24) {
          const relation = relationLabel(edge.type);
          const midpointX = (startX + endX) / 2;
          const midpointY = (startY + endY) / 2;
          context.font = `${selected ? 700 : 600} 8px system-ui, sans-serif`;
          const relationWidth = Math.min(context.measureText(relation).width + 8, 110);
          context.globalAlpha = selected ? 1 : 0.82;
          context.fillStyle = labelBackground;
          context.fillRect(midpointX - relationWidth / 2, midpointY - 7, relationWidth, 13);
          context.fillStyle = labelText;
          context.textAlign = "center";
          context.textBaseline = "middle";
          context.fillText(relation, midpointX, midpointY, relationWidth - 4);
        }
        context.restore();
      }

      const depthSortedNodes = [...renderedNodes].sort((left, right) => left.depth - right.depth);
      for (const node of depthSortedNodes) {
        const selected = node.id === selectedId;
        const hovered = node.id === hoveredId;
        const palette = nodePalette[node.type] ?? { fill: "#dbe6ef", stroke: "#70869a" };
        const depthAlpha = 0.6 + ((node.depth - minDepth) / depthRange) * 0.4;
        context.save();
        context.globalAlpha = depthAlpha;
        if (selected || hovered) {
          context.beginPath();
          context.arc(node.x, node.y, node.radius + (selected ? 8 : 5), 0, Math.PI * 2);
          context.fillStyle = selectedColour;
          context.globalAlpha = selected ? 0.2 : 0.1;
          context.fill();
          context.globalAlpha = depthAlpha;
        }
        nodePath(context, node);
        context.fillStyle = palette.fill;
        context.strokeStyle = selected ? selectedColour : palette.stroke;
        context.lineWidth = selected ? 3.5 : hovered ? 2.4 : 1.5;
        context.shadowColor = selected ? selectedColour : "transparent";
        context.shadowBlur = selected ? 12 : 0;
        context.fill();
        context.stroke();

        if (selected || hovered || renderedNodes.length <= 40) {
          const text = node.label.length > 20 ? `${node.label.slice(0, 19)}…` : node.label;
          context.font = `${selected ? 700 : 600} ${selected ? 11 : 10}px system-ui, sans-serif`;
          const labelWidth = Math.min(context.measureText(text).width + 10, 160);
          const labelY = node.y + node.radius + 14;
          context.globalAlpha = selected ? 1 : Math.max(depthAlpha, 0.72);
          context.fillStyle = labelBackground;
          context.fillRect(node.x - labelWidth / 2, labelY - 10, labelWidth, 15);
          context.fillStyle = labelText;
          context.textAlign = "center";
          context.textBaseline = "middle";
          context.fillText(text, node.x, labelY - 2, labelWidth - 6);
        }
        context.restore();
      }

      setRendererError(false);
    } catch {
      setRendererError(true);
    }
  }, [edges, hoveredId, pixelRatio, renderedNodes, renderGeneration, selectedId, size.height, size.width, theme]);

  function eventPosition(event: PointerEvent<HTMLCanvasElement>) {
    const rectangle = event.currentTarget.getBoundingClientRect();
    return {
      x: (event.clientX - rectangle.left) * (size.width / (rectangle.width || size.width)),
      y: (event.clientY - rectangle.top) * (size.height / (rectangle.height || size.height)),
    };
  }

  function hitTest(x: number, y: number): RenderedNode | undefined {
    return [...renderedNodesRef.current]
      .sort((left, right) => right.depth - left.depth)
      .find((node) => Math.hypot(node.x - x, node.y - y) <= node.radius + 7);
  }

  function handlePointerDown(event: PointerEvent<HTMLCanvasElement>) {
    const position = eventPosition(event);
    dragRef.current = {
      pointerId: event.pointerId,
      startX: position.x,
      startY: position.y,
      lastX: position.x,
      lastY: position.y,
      moved: false,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
    event.currentTarget.classList.add("is-dragging");
  }

  function handlePointerMove(event: PointerEvent<HTMLCanvasElement>) {
    const position = eventPosition(event);
    const drag = dragRef.current;
    if (!drag || drag.pointerId !== event.pointerId) {
      setHoveredId(hitTest(position.x, position.y)?.id);
      return;
    }

    const deltaX = position.x - drag.lastX;
    const deltaY = position.y - drag.lastY;
    drag.lastX = position.x;
    drag.lastY = position.y;
    drag.moved ||= Math.hypot(position.x - drag.startX, position.y - drag.startY) > 4;
    setCamera((current) => ({
      ...current,
      yaw: current.yaw + deltaX * 0.008,
      pitch: Math.min(Math.max(current.pitch + deltaY * 0.008, -1.15), 1.15),
    }));
  }

  function handlePointerUp(event: PointerEvent<HTMLCanvasElement>) {
    const drag = dragRef.current;
    const position = eventPosition(event);
    if (drag?.pointerId === event.pointerId && !drag.moved) {
      const node = hitTest(position.x, position.y);
      if (node) onSelect(node.id);
    }
    dragRef.current = null;
    event.currentTarget.classList.remove("is-dragging");
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }

  function handlePointerCancel(event: PointerEvent<HTMLCanvasElement>) {
    dragRef.current = null;
    setHoveredId(undefined);
    event.currentTarget.classList.remove("is-dragging");
    if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
  }

  const selectedLabel = nodes.find((node) => node.id === selectedId)?.label;
  const selectedVisibleId = nodes.some((node) => node.id === selectedId) ? selectedId : "";

  return (
    <div ref={shellRef} className="ontology-3d-shell">
      <p id="ontology-3d-instructions" className="sr-only">
        포인터로 드래그하여 회전하고 마우스 휠로 배율을 조정합니다. 키보드에서는 회전·확대·축소·초기화 버튼과 노드 선택 목록을 사용합니다. 모든 정보는 접근 가능한 목록 보기에서도 확인할 수 있습니다.
      </p>
      <canvas
        ref={canvasRef}
        className="ontology-3d-canvas"
        role="img"
        aria-hidden={rendererError || undefined}
        aria-label={`${nodes.length}개 노드와 ${edges.length}개 관계를 원근감 있게 표시한 3D 규정 온톨로지 캔버스`}
        aria-describedby="ontology-3d-instructions"
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onPointerCancel={handlePointerCancel}
        onPointerLeave={() => {
          if (!dragRef.current) setHoveredId(undefined);
        }}
      >
        3D 캔버스를 지원하지 않는 환경에서는 접근 가능한 목록 보기를 사용해 주세요.
      </canvas>

      {rendererError ? (
        <div className="ontology-3d-error" role="alert">
          <strong>3D 캔버스를 초기화할 수 없습니다.</strong>
          <p>동일한 노드와 근거는 접근 가능한 목록에서 확인할 수 있습니다.</p>
          <button type="button" className="button button--secondary" onClick={onRequestList}>목록으로 전환</button>
        </div>
      ) : null}

      {!rendererError ? (
        <>
          <div className="ontology-3d-controls" role="group" aria-label="3D 캔버스 카메라 조작">
            <button type="button" onClick={() => setCamera((current) => ({ ...current, yaw: current.yaw - 0.18 }))} aria-label="3D 캔버스 왼쪽 회전"><RotateCcw /></button>
            <button type="button" onClick={() => setCamera((current) => ({ ...current, yaw: current.yaw + 0.18 }))} aria-label="3D 캔버스 오른쪽 회전"><RotateCw /></button>
            <button type="button" onClick={() => setCamera((current) => ({ ...current, zoom: Math.min(current.zoom + 0.1, 1.9) }))} aria-label="3D 캔버스 확대"><Plus /></button>
            <button type="button" onClick={() => setCamera((current) => ({ ...current, zoom: Math.max(current.zoom - 0.1, 0.6) }))} aria-label="3D 캔버스 축소"><Minus /></button>
            <button type="button" onClick={() => setCamera({ ...DEFAULT_CAMERA_3D })} aria-label="3D 카메라 초기화"><Focus /></button>
          </div>

          <div className="ontology-3d-node-picker">
            <label htmlFor="ontology-3d-node-select">키보드 노드 선택</label>
            <select
              id="ontology-3d-node-select"
              value={selectedVisibleId ?? ""}
              onChange={(event) => onSelect(event.target.value)}
            >
              <option value="" disabled>노드를 선택하세요</option>
              {nodes.map((node) => <option key={node.id} value={node.id}>{nodeTypeLabel(node.type)} · {node.label}</option>)}
            </select>
          </div>

          <div className="ontology-3d-hint" aria-hidden="true">Drag to orbit · Wheel to zoom</div>
        </>
      ) : null}
      <output className="sr-only" aria-live="polite">{selectedLabel ? `선택한 노드: ${selectedLabel}` : "선택한 노드 없음"}</output>
    </div>
  );
}
