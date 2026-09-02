import type { OntologyEdge, OntologyNode } from "./types";

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface Camera3D {
  yaw: number;
  pitch: number;
  zoom: number;
}

export const DEFAULT_CAMERA_3D: Camera3D = { yaw: -0.58, pitch: 0.3, zoom: 1 };

export interface ProjectedPoint {
  x: number;
  y: number;
  depth: number;
  scale: number;
  visible: boolean;
}

function compareId(left: string, right: string): number {
  if (left < right) return -1;
  if (left > right) return 1;
  return 0;
}

/**
 * Builds a stable spatial projection without persisting presentation coordinates.
 * A volume-filling seed prevents large disconnected or star graphs from collapsing,
 * then a bounded deterministic force pass shortens relationships and resolves overlap.
 */
export function createSpatialLayout(
  nodes: OntologyNode[],
  edges: OntologyEdge[],
): Map<string, Vector3> {
  const ids = [...new Set(nodes.map((node) => node.id))].sort(compareId);
  const knownIds = new Set(ids);
  const adjacency = new Map(ids.map((id) => [id, new Set<string>()]));
  const validEdges = edges.filter((edge) => knownIds.has(edge.source) && knownIds.has(edge.target))
    .sort((left, right) => compareId(`${left.source}\u0000${left.target}\u0000${left.id}`, `${right.source}\u0000${right.target}\u0000${right.id}`));

  for (const edge of validEdges) {
    adjacency.get(edge.source)!.add(edge.target);
    adjacency.get(edge.target)!.add(edge.source);
  }

  const order = [...ids].sort((left, right) => {
    const degreeDifference = adjacency.get(right)!.size - adjacency.get(left)!.size;
    return degreeDifference || compareId(left, right);
  });
  const raw = new Map<string, Vector3>();
  if (order.length === 0) return raw;
  if (order.length === 1) return new Map([[order[0]!, { x: 0, y: 0, z: 0 }]]);

  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  raw.set(order[0]!, { x: 0, y: 0, z: 0 });
  for (let index = 1; index < order.length; index += 1) {
    const fraction = (index - 0.5) / (order.length - 1);
    const directionZ = 1 - 2 * fraction;
    const directionRadius = Math.sqrt(Math.max(1 - directionZ * directionZ, 0));
    const angle = goldenAngle * (index - 1);
    const shellRadius = 51 * Math.cbrt(index);
    raw.set(order[index]!, {
      x: Math.cos(angle) * directionRadius * shellRadius,
      y: Math.sin(angle) * directionRadius * shellRadius,
      z: directionZ * shellRadius,
    });
  }

  for (let iteration = 0; iteration < 56; iteration += 1) {
    const forces = new Map(order.map((id) => [id, { x: 0, y: 0, z: 0 }]));

    for (let leftIndex = 0; leftIndex < order.length; leftIndex += 1) {
      const leftId = order[leftIndex]!;
      const left = raw.get(leftId)!;
      for (let rightIndex = leftIndex + 1; rightIndex < order.length; rightIndex += 1) {
        const rightId = order[rightIndex]!;
        const right = raw.get(rightId)!;
        const delta = { x: right.x - left.x, y: right.y - left.y, z: right.z - left.z };
        const distance = Math.max(Math.hypot(delta.x, delta.y, delta.z), 0.001);
        const unit = { x: delta.x / distance, y: delta.y / distance, z: delta.z / distance };
        const collision = distance < 38 ? (38 - distance) * 0.24 : 0;
        const repulsion = collision + 1150 / (distance * distance);
        const leftForce = forces.get(leftId)!;
        const rightForce = forces.get(rightId)!;
        leftForce.x -= unit.x * repulsion;
        leftForce.y -= unit.y * repulsion;
        leftForce.z -= unit.z * repulsion;
        rightForce.x += unit.x * repulsion;
        rightForce.y += unit.y * repulsion;
        rightForce.z += unit.z * repulsion;
      }
    }

    for (const edge of validEdges) {
      const source = raw.get(edge.source)!;
      const target = raw.get(edge.target)!;
      const delta = { x: target.x - source.x, y: target.y - source.y, z: target.z - source.z };
      const distance = Math.max(Math.hypot(delta.x, delta.y, delta.z), 0.001);
      const spring = (distance - 105) * 0.013;
      const sourceForce = forces.get(edge.source)!;
      const targetForce = forces.get(edge.target)!;
      const x = (delta.x / distance) * spring;
      const y = (delta.y / distance) * spring;
      const z = (delta.z / distance) * spring;
      sourceForce.x += x;
      sourceForce.y += y;
      sourceForce.z += z;
      targetForce.x -= x;
      targetForce.y -= y;
      targetForce.z -= z;
    }

    const cooling = 0.74 - (iteration / 56) * 0.52;
    for (const id of order) {
      const point = raw.get(id)!;
      const force = forces.get(id)!;
      force.x -= point.x * 0.0018;
      force.y -= point.y * 0.0018;
      force.z -= point.z * 0.0018;
      const magnitude = Math.max(Math.hypot(force.x, force.y, force.z), 1);
      const limit = Math.min(9 / magnitude, 1) * cooling;
      point.x += force.x * limit;
      point.y += force.y * limit;
      point.z += force.z * limit;
    }
  }

  const points = [...raw.values()];
  const centre = points.reduce(
    (sum, point) => ({ x: sum.x + point.x, y: sum.y + point.y, z: sum.z + point.z }),
    { x: 0, y: 0, z: 0 },
  );
  centre.x /= points.length;
  centre.y /= points.length;
  centre.z /= points.length;
  const maxRadius = Math.max(
    ...points.map((point) => Math.hypot(point.x - centre.x, point.y - centre.y, point.z - centre.z)),
    1,
  );
  const scale = Math.min(1.7, 285 / maxRadius);

  for (const [id, point] of raw) {
    raw.set(id, {
      x: (point.x - centre.x) * scale,
      y: (point.y - centre.y) * scale,
      z: (point.z - centre.z) * scale,
    });
  }

  return raw;
}

export function projectSpatialPoint(
  point: Vector3,
  camera: Camera3D,
  width: number,
  height: number,
): ProjectedPoint {
  const safeWidth = Math.max(width, 1);
  const safeHeight = Math.max(height, 1);
  const cosYaw = Math.cos(camera.yaw);
  const sinYaw = Math.sin(camera.yaw);
  const cosPitch = Math.cos(camera.pitch);
  const sinPitch = Math.sin(camera.pitch);
  const rotatedX = point.x * cosYaw + point.z * sinYaw;
  const yawDepth = -point.x * sinYaw + point.z * cosYaw;
  const rotatedY = point.y * cosPitch - yawDepth * sinPitch;
  const rotatedZ = point.y * sinPitch + yawDepth * cosPitch;
  const cameraDistance = 720;
  const denominator = cameraDistance - rotatedZ;
  const visible = denominator > 60;
  const focalLength = 520 * Math.min(Math.max(camera.zoom, 0.55), 2.1);
  const perspective = focalLength / Math.max(denominator, 60);

  return {
    x: safeWidth / 2 + rotatedX * perspective,
    y: safeHeight / 2 + rotatedY * perspective,
    depth: rotatedZ,
    scale: perspective,
    visible,
  };
}
