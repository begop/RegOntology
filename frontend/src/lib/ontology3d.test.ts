import { describe, expect, it } from "vitest";
import { createSpatialLayout, projectSpatialPoint } from "./ontology3d";
import type { OntologyEdge, OntologyNode } from "./types";

function node(id: string): OntologyNode {
  return { id, type: "Obligation", label: id, securityClass: "internal" };
}

function edge(id: string, source: string, target: string): OntologyEdge {
  return {
    id,
    type: "RELATED_TO",
    source,
    target,
    sourceDocument: "MOCK-TEST-001",
    sourceLocator: "제1조",
    reviewStatus: "APPROVED",
  };
}

function minimumDistance(points: Array<{ x: number; y: number; z: number }>): number {
  let minimum = Number.POSITIVE_INFINITY;
  for (let left = 0; left < points.length; left += 1) {
    for (let right = left + 1; right < points.length; right += 1) {
      const first = points[left]!;
      const second = points[right]!;
      minimum = Math.min(minimum, Math.hypot(first.x - second.x, first.y - second.y, first.z - second.z));
    }
  }
  return minimum;
}

describe("ontology3d spatial projection — FR-013 / NFR-009", () => {
  it("creates deterministic finite positions for connected and isolated nodes", () => {
    const nodes = [node("c"), node("a"), node("b"), node("isolated")];
    const edges = [edge("e-1", "a", "b"), edge("e-2", "b", "c")];

    const first = [...createSpatialLayout(nodes, edges).entries()];
    const second = [...createSpatialLayout([...nodes].reverse(), [...edges].reverse()).entries()];

    expect(first).toEqual(second);
    expect(first.map(([id]) => id).sort()).toEqual(["a", "b", "c", "isolated"]);
    for (const [, point] of first) {
      expect(Number.isFinite(point.x)).toBe(true);
      expect(Number.isFinite(point.y)).toBe(true);
      expect(Number.isFinite(point.z)).toBe(true);
    }
  });

  it("handles empty, single-node, and maximum 200-node inputs", () => {
    expect(createSpatialLayout([], [])).toEqual(new Map());
    expect(createSpatialLayout([node("only")], []).get("only")).toEqual({ x: 0, y: 0, z: 0 });

    const nodes = Array.from({ length: 200 }, (_, index) => node(`node-${String(index).padStart(3, "0")}`));
    const edges = nodes.slice(1).map((current, index) => edge(`edge-${index}`, nodes[index]!.id, current.id));
    const layout = createSpatialLayout(nodes, edges);
    expect(layout.size).toBe(200);
    expect(Math.max(...[...layout.values()].map((point) => Math.hypot(point.x, point.y, point.z)))).toBeLessThanOrEqual(311);
    expect(minimumDistance([...layout.values()])).toBeGreaterThan(18);

    const disconnectedLayout = createSpatialLayout(nodes, []);
    expect(minimumDistance([...disconnectedLayout.values()])).toBeGreaterThan(18);
  });

  it("projects spatial points with bounded zoom and visible perspective depth", () => {
    const point = { x: 120, y: -35, z: 80 };
    const normal = projectSpatialPoint(point, { yaw: -0.5, pitch: 0.3, zoom: 1 }, 800, 600);
    const zoomed = projectSpatialPoint(point, { yaw: -0.5, pitch: 0.3, zoom: 1.6 }, 800, 600);

    expect(normal.visible).toBe(true);
    expect([normal.x, normal.y, normal.depth, normal.scale].every(Number.isFinite)).toBe(true);
    expect(zoomed.scale).toBeGreaterThan(normal.scale);
    expect(Math.abs(zoomed.x - 400)).toBeGreaterThan(Math.abs(normal.x - 400));
  });
});
