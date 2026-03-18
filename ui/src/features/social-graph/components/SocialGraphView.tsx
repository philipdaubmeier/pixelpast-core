import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";
import { PanelCard } from "../../../components/PanelCard";
import type { PersonProjection, TagProjection } from "../../../projections/timeline";
import type {
  SocialGraphLinkProjection,
  SocialGraphPersonProjection,
  SocialGraphProjection,
} from "../../../projections/socialGraph";

type SocialGraphViewProps = {
  state: "loading" | "ready" | "error";
  error: string | null;
  graph: SocialGraphProjection | null;
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  onTogglePerson: (personId: string) => void;
};

type GraphNode = {
  id: string;
  name: string;
  occurrenceCount: number;
  radius: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
};

type GraphLink = {
  id: string;
  sourceId: string;
  targetId: string;
  weight: number;
  layoutStrength: number;
};

type GraphViewport = {
  scale: number;
  x: number;
  y: number;
};

type GraphDimensions = {
  width: number;
  height: number;
};

type LayoutState = {
  nodes: GraphNode[];
  links: GraphLink[];
  maxLinkWeight: number;
  linkWeightScale: number;
  totalKineticEnergy: number;
  alpha: number;
  tickCount: number;
  isSettled: boolean;
};

const MIN_GRAPH_WIDTH = 320;
const MIN_GRAPH_HEIGHT = 320;
const FRAME_DURATION_SECONDS = 1 / 60;
const CHARGE_FORCE = 300;
const SPRING_FORCE = 0.012;
const CENTER_FORCE = 0.0045;
const WALL_FORCE = 0.04;
const OVERLAP_PUSH_FORCE = 0.6;
const JITTER_FORCE = 0.75;
const ALPHA_INITIAL = 1;
const ALPHA_DECAY = 0.018;
const ALPHA_MIN = 0.012;
const MAX_SIMULATION_TICKS = 480;
const MAX_FRAME_DELTA_MS = 32;
const COLLISION_RAMP_TICKS = 220;
const CENTER_RAMP_TICKS = 260;
const LAYOUT_LINK_STRENGTH_THRESHOLD = 0.16;

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

function formatCompactNumber(value: number): string {
  return new Intl.NumberFormat("en", { notation: "compact" }).format(value);
}

function buildLinkId(leftPersonId: string, rightPersonId: string): string {
  return `${leftPersonId}::${rightPersonId}`;
}

function buildLinkLabel(
  personNamesById: Map<string, string>,
  leftPersonId: string,
  rightPersonId: string,
): string {
  const leftName = personNamesById.get(leftPersonId) ?? leftPersonId;
  const rightName = personNamesById.get(rightPersonId) ?? rightPersonId;
  return `${leftName} <-> ${rightName}`;
}

function getNodeRadius(
  occurrenceCount: number,
  maxOccurrenceCount: number,
  totalNodes: number,
): number {
  const safeMax = Math.max(maxOccurrenceCount, 1);
  const normalized =
    Math.log1p(occurrenceCount) / Math.log1p(safeMax);
  const densityScale = clamp(140 / Math.max(totalNodes, 24), 0.24, 1);
  return 2.4 + densityScale * 2.4 + normalized * densityScale * 4.4;
}

function getLinkStrokeWidth(weight: number, maxWeight: number): number {
  const normalized = maxWeight > 0 ? weight / maxWeight : 0;
  return 1.2 + normalized * 4.8;
}

function getLinkOpacity(weight: number, maxWeight: number): number {
  const normalized = maxWeight > 0 ? weight / maxWeight : 0;
  return 0.18 + normalized * 0.58;
}

function getQuantile(values: number[], quantile: number): number {
  if (values.length === 0) {
    return 1;
  }

  const sortedValues = [...values].sort((left, right) => left - right);
  const index = Math.max(
    0,
    Math.min(
      sortedValues.length - 1,
      Math.floor((sortedValues.length - 1) * quantile),
    ),
  );
  return sortedValues[index];
}

function getLinkStrength(weight: number, linkWeightScale: number): number {
  const safeScale = Math.max(linkWeightScale, 1);
  const normalized = Math.log1p(weight) / Math.log1p(safeScale);
  const clampedNormalized = clamp(normalized, 0, 1);
  const liftedNormalized = clamp((clampedNormalized - 0.08) / 0.5, 0, 1);
  const saturatedNormalized = 1 - (1 - liftedNormalized) * (1 - liftedNormalized);
  return 0.01 + saturatedNormalized * 1.2;
}

function createInitialLayout(
  persons: SocialGraphPersonProjection[],
  links: SocialGraphLinkProjection[],
  dimensions: GraphDimensions,
): LayoutState {
  const maxOccurrenceCount = Math.max(
    ...persons.map((person) => person.occurrenceCount),
    1,
  );
  const preparedNodes = persons.map((person) => ({
    id: person.id,
    name: person.name,
    occurrenceCount: person.occurrenceCount,
    radius: getNodeRadius(
      person.occurrenceCount,
      maxOccurrenceCount,
      persons.length,
    ),
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
  }));
  const preparedLinks = links.map((link) => ({
    id: buildLinkId(link.personIds[0], link.personIds[1]),
    sourceId: link.personIds[0],
    targetId: link.personIds[1],
    weight: link.weight,
    layoutStrength: 0,
  }));
  const linkWeightScale = Math.max(
    getQuantile(
      preparedLinks.map((link) => link.weight),
      0.8,
    ),
    1,
  );
  preparedLinks.forEach((link) => {
    link.layoutStrength = getLinkStrength(link.weight, linkWeightScale);
  });
  const centerX = dimensions.width / 2;
  const centerY = dimensions.height / 2;
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const spiralSpacing = Math.max(
    8,
    Math.min(dimensions.width, dimensions.height) * 0.018,
  );

  preparedNodes
    .sort(
      (left, right) =>
        right.occurrenceCount - left.occurrenceCount ||
        left.name.localeCompare(right.name),
    )
    .forEach((node, index) => {
      const angle = index * goldenAngle;
      const distance = spiralSpacing * Math.sqrt(index + 1);
      node.x = centerX + Math.cos(angle) * distance;
      node.y = centerY + Math.sin(angle) * distance;
    });

  return {
    nodes: preparedNodes,
    links: preparedLinks,
    maxLinkWeight: Math.max(...preparedLinks.map((link) => link.weight), 1),
    linkWeightScale,
    totalKineticEnergy: Number.POSITIVE_INFINITY,
    alpha: ALPHA_INITIAL,
    tickCount: 0,
    isSettled: false,
  };
}

function simulateLayoutStep(
  currentLayout: LayoutState,
  dimensions: GraphDimensions,
  deltaSeconds: number,
): LayoutState {
  const nodes = currentLayout.nodes.map((node) => ({ ...node }));
  const links = currentLayout.links;
  const nodeIndexById = new Map(nodes.map((node, index) => [node.id, index]));
  const centerX = dimensions.width / 2;
  const centerY = dimensions.height / 2;
  const safeDelta = deltaSeconds / FRAME_DURATION_SECONDS;
  const effectiveAlpha = Math.max(currentLayout.alpha, ALPHA_MIN);
  const damping = 0.82 - (1 - effectiveAlpha) * 0.16;
  const maxVelocity = 2.2 + effectiveAlpha * 12;
  const collisionRamp = clamp(
    currentLayout.tickCount / COLLISION_RAMP_TICKS,
    0.12,
    1,
  );
  const centerRamp = clamp(
    currentLayout.tickCount / CENTER_RAMP_TICKS,
    0.03,
    1,
  );

  for (let leftIndex = 0; leftIndex < nodes.length; leftIndex += 1) {
    const leftNode = nodes[leftIndex];

    for (
      let rightIndex = leftIndex + 1;
      rightIndex < nodes.length;
      rightIndex += 1
    ) {
      const rightNode = nodes[rightIndex];
      let dx = rightNode.x - leftNode.x;
      let dy = rightNode.y - leftNode.y;
      let distanceSquared = dx * dx + dy * dy;

      if (distanceSquared < 1) {
        dx = 0.5 - Math.random();
        dy = 0.5 - Math.random();
        distanceSquared = dx * dx + dy * dy + 0.01;
      }

      const distance = Math.sqrt(distanceSquared);
      const repulsion =
        (CHARGE_FORCE * effectiveAlpha * safeDelta) / Math.max(distanceSquared, 36);
      const repelX = (dx / distance) * repulsion;
      const repelY = (dy / distance) * repulsion;

      leftNode.vx -= repelX;
      leftNode.vy -= repelY;
      rightNode.vx += repelX;
      rightNode.vy += repelY;

      const minimumDistance = leftNode.radius + rightNode.radius + 2;
      if (distance < minimumDistance) {
        const overlap = minimumDistance - distance;
        const normalX = dx / distance;
        const normalY = dy / distance;
        const overlapRatio = overlap / minimumDistance;
        const separationDistance =
          overlap *
          (0.12 + collisionRamp * (0.4 + overlapRatio * overlapRatio * 0.95));
        const separationX = normalX * separationDistance * 0.5;
        const separationY = normalY * separationDistance * 0.5;
        const pushVelocity =
          overlapRatio *
          overlapRatio *
          OVERLAP_PUSH_FORCE *
          effectiveAlpha *
          collisionRamp;

        leftNode.x -= separationX;
        leftNode.y -= separationY;
        rightNode.x += separationX;
        rightNode.y += separationY;
        leftNode.vx -= normalX * pushVelocity;
        leftNode.vy -= normalY * pushVelocity;
        rightNode.vx += normalX * pushVelocity;
        rightNode.vy += normalY * pushVelocity;
      }
    }
  }

  for (const link of links) {
    if (link.layoutStrength < LAYOUT_LINK_STRENGTH_THRESHOLD) {
      continue;
    }

    const sourceIndex = nodeIndexById.get(link.sourceId);
    const targetIndex = nodeIndexById.get(link.targetId);

    if (sourceIndex === undefined || targetIndex === undefined) {
      continue;
    }

    const sourceNode = nodes[sourceIndex];
    const targetNode = nodes[targetIndex];
    let dx = targetNode.x - sourceNode.x;
    let dy = targetNode.y - sourceNode.y;
    let distance = Math.sqrt(dx * dx + dy * dy);

    if (distance < 1) {
      distance = 1;
      dx = 1;
      dy = 0;
    }

    const idealDistance =
      clamp(
        18 +
          (sourceNode.radius + targetNode.radius) * 1.35 -
          link.layoutStrength * 4.2,
        sourceNode.radius + targetNode.radius + 2,
        34,
      );
    const springStrength =
      SPRING_FORCE *
      link.layoutStrength *
      effectiveAlpha;
    const springDelta = (distance - idealDistance) * springStrength * safeDelta;
    const springX = (dx / distance) * springDelta;
    const springY = (dy / distance) * springDelta;

    sourceNode.vx += springX;
    sourceNode.vy += springY;
    targetNode.vx -= springX;
    targetNode.vy -= springY;
  }

  let totalKineticEnergy = 0;

  for (const node of nodes) {
    node.vx +=
      (centerX - node.x) *
      CENTER_FORCE *
      centerRamp *
      effectiveAlpha *
      safeDelta;
    node.vy +=
      (centerY - node.y) *
      CENTER_FORCE *
      centerRamp *
      effectiveAlpha *
      safeDelta;

    const padding = node.radius + 8;
    if (node.x < padding) {
      node.vx += (padding - node.x) * WALL_FORCE * safeDelta;
    } else if (node.x > dimensions.width - padding) {
      node.vx -= (node.x - (dimensions.width - padding)) * WALL_FORCE * safeDelta;
    }

    if (node.y < padding) {
      node.vy += (padding - node.y) * WALL_FORCE * safeDelta;
    } else if (node.y > dimensions.height - padding) {
      node.vy -= (node.y - (dimensions.height - padding)) * WALL_FORCE * safeDelta;
    }

    if (effectiveAlpha > 0.08) {
      const jitterAmplitude = JITTER_FORCE * effectiveAlpha * effectiveAlpha;
      node.vx += (Math.random() - 0.5) * jitterAmplitude;
      node.vy += (Math.random() - 0.5) * jitterAmplitude;
    }

    node.vx = clamp(node.vx, -maxVelocity, maxVelocity);
    node.vy = clamp(node.vy, -maxVelocity, maxVelocity);
    node.vx *= damping;
    node.vy *= damping;
    node.x += node.vx;
    node.y += node.vy;

    node.x = clamp(node.x, padding, dimensions.width - padding);
    node.y = clamp(node.y, padding, dimensions.height - padding);

    totalKineticEnergy += Math.abs(node.vx) + Math.abs(node.vy);
  }

  const nextAlpha =
    currentLayout.alpha <= ALPHA_MIN
      ? 0
      : currentLayout.alpha * (1 - ALPHA_DECAY);
  const nextTickCount = currentLayout.tickCount + 1;
  const averageKineticEnergy =
    nodes.length > 0 ? totalKineticEnergy / nodes.length : 0;
  const isSettled =
    nextTickCount >= MAX_SIMULATION_TICKS ||
    (nextAlpha <= ALPHA_MIN && averageKineticEnergy < 0.05);

  return {
    nodes,
    links,
    maxLinkWeight: currentLayout.maxLinkWeight,
    linkWeightScale: currentLayout.linkWeightScale,
    totalKineticEnergy,
    alpha: nextAlpha,
    tickCount: nextTickCount,
    isSettled,
  };
}

function getViewportTransform(viewport: GraphViewport): string {
  return `translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`;
}

function useGraphDimensions() {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dimensions, setDimensions] = useState<GraphDimensions>({
    width: 0,
    height: 0,
  });

  useEffect(() => {
    const element = containerRef.current;
    if (element === null) {
      return;
    }

    const updateDimensions = () => {
      const nextWidth = Math.max(
        Math.round(element.clientWidth),
        MIN_GRAPH_WIDTH,
      );
      const nextHeight = Math.max(
        Math.round(element.clientHeight),
        MIN_GRAPH_HEIGHT,
      );

      setDimensions((currentDimensions) =>
        currentDimensions.width === nextWidth &&
        currentDimensions.height === nextHeight
          ? currentDimensions
          : { width: nextWidth, height: nextHeight },
      );
    };

    updateDimensions();

    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });

    resizeObserver.observe(element);

    return () => {
      resizeObserver.disconnect();
    };
  }, []);

  return { containerRef, dimensions };
}

function SocialGraphCanvas({
  graph,
  selectedPersons,
  onTogglePerson,
}: {
  graph: SocialGraphProjection;
  selectedPersons: PersonProjection[];
  onTogglePerson: (personId: string) => void;
}) {
  const { containerRef, dimensions } = useGraphDimensions();
  const [layout, setLayout] = useState<LayoutState>(() =>
    createInitialLayout(graph.persons, graph.links, {
      width: MIN_GRAPH_WIDTH,
      height: MIN_GRAPH_HEIGHT,
    }),
  );
  const layoutRef = useRef(layout);
  const [viewport, setViewport] = useState<GraphViewport>({
    scale: 1,
    x: 0,
    y: 0,
  });
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredLinkId, setHoveredLinkId] = useState<string | null>(null);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const dragStateRef = useRef<{
    pointerId: number;
    originClientX: number;
    originClientY: number;
    originX: number;
    originY: number;
  } | null>(null);

  useEffect(() => {
    if (dimensions.width === 0 || dimensions.height === 0) {
      return;
    }

    const nextLayout = createInitialLayout(graph.persons, graph.links, dimensions);
    layoutRef.current = nextLayout;
    setLayout(nextLayout);
    setViewport({ scale: 1, x: 0, y: 0 });
    setHoveredNodeId(null);
    setHoveredLinkId(null);
    setFocusedNodeId(null);
  }, [dimensions, graph]);

  useEffect(() => {
    layoutRef.current = layout;
  }, [layout]);

  useEffect(() => {
    if (
      dimensions.width === 0 ||
      dimensions.height === 0 ||
      layoutRef.current.nodes.length === 0
    ) {
      return;
    }

    let animationFrameId = 0;
    let previousTimestamp: number | null = null;
    let isDisposed = false;

    const animate = (timestamp: number) => {
      if (isDisposed) {
        return;
      }

      const deltaMilliseconds =
        previousTimestamp === null
          ? 16
          : Math.min(timestamp - previousTimestamp, MAX_FRAME_DELTA_MS);
      previousTimestamp = timestamp;

      const nextLayout = simulateLayoutStep(
        layoutRef.current,
        dimensions,
        deltaMilliseconds / 1000,
      );
      layoutRef.current = nextLayout;
      setLayout(nextLayout);

      if (!nextLayout.isSettled) {
        animationFrameId = window.requestAnimationFrame(animate);
      }
    };

    animationFrameId = window.requestAnimationFrame(animate);

    return () => {
      isDisposed = true;
      window.cancelAnimationFrame(animationFrameId);
    };
  }, [dimensions, graph]);

  const personNamesById = useMemo(
    () => new Map(graph.persons.map((person) => [person.id, person.name])),
    [graph.persons],
  );
  const nodesById = useMemo(
    () => new Map(layout.nodes.map((node) => [node.id, node])),
    [layout.nodes],
  );
  const selectedPersonIds = useMemo(
    () => new Set(selectedPersons.map((person) => person.id)),
    [selectedPersons],
  );
  const showAllNodeLabels = graph.persons.length <= 80;
  const activeNodeId = hoveredNodeId ?? focusedNodeId;

  const focusedNode =
    (activeNodeId !== null ? nodesById.get(activeNodeId) : null) ?? null;
  const focusedLink =
    layout.links.find((link) => link.id === hoveredLinkId) ?? null;

  const topConnections = useMemo(() => {
    if (activeNodeId === null) {
      return [];
    }

    return [...layout.links]
      .filter(
        (link) =>
          link.sourceId === activeNodeId || link.targetId === activeNodeId,
      )
      .sort((left, right) => right.weight - left.weight)
      .slice(0, 4);
  }, [activeNodeId, layout.links]);

  const onCanvasPointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.target !== event.currentTarget) {
      return;
    }

    dragStateRef.current = {
      pointerId: event.pointerId,
      originClientX: event.clientX,
      originClientY: event.clientY,
      originX: viewport.x,
      originY: viewport.y,
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onCanvasPointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    const dragState = dragStateRef.current;
    if (dragState === null || dragState.pointerId !== event.pointerId) {
      return;
    }

    const deltaX = event.clientX - dragState.originClientX;
    const deltaY = event.clientY - dragState.originClientY;

    setViewport((currentViewport) => ({
      ...currentViewport,
      x: dragState.originX + deltaX,
      y: dragState.originY + deltaY,
    }));
  };

  const onCanvasPointerUp = (event: ReactPointerEvent<SVGSVGElement>) => {
    const dragState = dragStateRef.current;
    if (dragState === null || dragState.pointerId !== event.pointerId) {
      return;
    }

    dragStateRef.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const onCanvasWheel = (event: ReactWheelEvent<SVGSVGElement>) => {
    event.preventDefault();

    const zoomFactor = event.deltaY < 0 ? 1.08 : 0.92;

    setViewport((currentViewport) => {
      const nextScale = clamp(currentViewport.scale * zoomFactor, 0.55, 2.8);
      return {
        ...currentViewport,
        scale: nextScale,
      };
    });
  };

  const resetViewport = () => {
    setViewport({ scale: 1, x: 0, y: 0 });
  };

  return (
    <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(19rem,0.65fr)]">
      <PanelCard
        title="Social Graph"
        description="Persons cluster from weighted asset co-occurrence. Wheel zooms, drag pans, and node hover reveals local structure."
        actions={
          <button
            type="button"
            onClick={resetViewport}
            className="rounded-full border border-[color:var(--pp-border)] bg-white/80 px-3 py-1.5 text-xs font-medium text-slate-700 transition hover:bg-white"
          >
            Reset view
          </button>
        }
      >
        <div className="flex h-full min-h-0 flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-4">
            <div className="rounded-3xl border border-[color:var(--pp-border)] bg-white/80 p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Persons
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {graph.persons.length}
              </div>
            </div>
            <div className="rounded-3xl border border-[color:var(--pp-border)] bg-white/80 p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Links
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {graph.links.length}
              </div>
            </div>
            <div className="rounded-3xl border border-[color:var(--pp-border)] bg-white/80 p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Selected
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {selectedPersons.length}
              </div>
            </div>
            <div className="rounded-3xl border border-[color:var(--pp-border)] bg-white/80 p-4">
              <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Zoom
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {Math.round(viewport.scale * 100)}%
              </div>
            </div>
          </div>
          <div
            ref={containerRef}
            className="subtle-grid relative min-h-[22rem] flex-1 overflow-hidden rounded-[2rem] border border-[color:var(--pp-border)] bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.95),_rgba(244,234,219,0.92)_54%,_rgba(229,214,190,0.95))]"
          >
            <svg
              className="h-full w-full touch-none"
              viewBox={`0 0 ${Math.max(dimensions.width, MIN_GRAPH_WIDTH)} ${Math.max(dimensions.height, MIN_GRAPH_HEIGHT)}`}
              role="img"
              aria-label="Social graph of person co-occurrences"
              onPointerDown={onCanvasPointerDown}
              onPointerMove={onCanvasPointerMove}
              onPointerUp={onCanvasPointerUp}
              onPointerCancel={onCanvasPointerUp}
              onWheel={onCanvasWheel}
              onPointerLeave={() => {
                if (dragStateRef.current === null) {
                  setHoveredLinkId(null);
                  setHoveredNodeId(null);
                }
              }}
            >
              <rect
                width={Math.max(dimensions.width, MIN_GRAPH_WIDTH)}
                height={Math.max(dimensions.height, MIN_GRAPH_HEIGHT)}
                fill="transparent"
              />
              <g transform={getViewportTransform(viewport)}>
                {layout.links.map((link) => {
                  const sourceNode = nodesById.get(link.sourceId) ?? null;
                  const targetNode = nodesById.get(link.targetId) ?? null;

                  if (sourceNode === null || targetNode === null) {
                    return null;
                  }

                  const isActive =
                    hoveredLinkId === link.id ||
                    (activeNodeId !== null &&
                      (link.sourceId === activeNodeId ||
                        link.targetId === activeNodeId));
                  const linkStroke = getLinkStrokeWidth(
                    link.weight,
                    layout.maxLinkWeight,
                  );

                  return (
                    <line
                      key={link.id}
                      x1={sourceNode.x}
                      y1={sourceNode.y}
                      x2={targetNode.x}
                      y2={targetNode.y}
                      stroke={isActive ? "#7c4b21" : "#8a6b43"}
                      strokeWidth={isActive ? linkStroke + 1.2 : linkStroke}
                      strokeOpacity={
                        isActive
                          ? 0.92
                          : getLinkOpacity(link.weight, layout.maxLinkWeight)
                      }
                      className="cursor-pointer transition-[stroke-opacity,stroke-width]"
                      onPointerEnter={() => {
                        setHoveredLinkId(link.id);
                        setHoveredNodeId(null);
                      }}
                      onPointerLeave={() => {
                        setHoveredLinkId((currentValue) =>
                          currentValue === link.id ? null : currentValue,
                        );
                      }}
                    />
                  );
                })}
                {layout.nodes.map((node) => {
                  const isSelected = selectedPersonIds.has(node.id);
                  const isHovered = hoveredNodeId === node.id;
                  const isFocused = focusedNodeId === node.id;
                  const isActive = isHovered || isFocused;
                  const strokeWidth = isSelected ? 4 : isActive ? 3 : 2;
                  const shouldRenderLabel =
                    showAllNodeLabels || isSelected || isActive;

                  return (
                    <g
                      key={node.id}
                      transform={`translate(${node.x} ${node.y})`}
                      className="cursor-pointer"
                      onPointerEnter={() => {
                        setHoveredNodeId(node.id);
                        setHoveredLinkId(null);
                      }}
                      onPointerLeave={() => {
                        setHoveredNodeId((currentValue) =>
                          currentValue === node.id ? null : currentValue,
                        );
                      }}
                      onClick={() => {
                        setFocusedNodeId((currentValue) =>
                          currentValue === node.id ? null : node.id,
                        );
                      }}
                    >
                      <circle
                        r={node.radius + (isActive ? 6 : 0)}
                        fill={isSelected ? "rgba(202,159,88,0.2)" : "rgba(202,159,88,0.08)"}
                      />
                      <circle
                        r={node.radius}
                        fill={isSelected ? "#ca9f58" : isActive ? "#f0c47f" : "#f8f2e8"}
                        stroke={isSelected ? "#7c4b21" : "#8a6b43"}
                        strokeWidth={strokeWidth}
                      />
                      {shouldRenderLabel ? (
                        <text
                          y={node.radius + 14}
                          textAnchor="middle"
                          fill="#1c2430"
                          className="pointer-events-none select-none text-[10px] font-semibold tracking-[0.02em]"
                        >
                          {node.name}
                        </text>
                      ) : null}
                    </g>
                  );
                })}
              </g>
            </svg>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-between px-4 pb-4 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">
              <span>Drag to pan</span>
              <span>Wheel to zoom</span>
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
            <div className="rounded-2xl border border-[color:var(--pp-border)] bg-white/80 px-4 py-3 text-sm text-slate-700">
              {focusedLink !== null ? (
                <>
                  <span className="font-semibold text-slate-900">
                    {buildLinkLabel(
                      personNamesById,
                      focusedLink.sourceId,
                      focusedLink.targetId,
                    )}
                  </span>
                  {` `}
                  carries weight {focusedLink.weight}.
                </>
              ) : focusedNode !== null ? (
                <>
                  <span className="font-semibold text-slate-900">
                    {focusedNode.name}
                  </span>
                  {` `}
                  appears in {formatCompactNumber(focusedNode.occurrenceCount)} shared
                  asset occurrence
                  {focusedNode.occurrenceCount === 1 ? "" : "s"}.
                </>
              ) : (
                "Hover a node or link to inspect local graph structure."
              )}
            </div>
            {selectedPersons.length > 0 ? (
              <div className="rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-900">
                Selected persons remain global filters across main views.
              </div>
            ) : null}
          </div>
        </div>
      </PanelCard>
      <div className="grid min-h-0 gap-2">
        <PanelCard
          title="Focused Node"
          description="Node hover is local to the graph. Click a node to keep it pinned in the detail panel while you continue exploring."
        >
          <div className="flex min-h-0 flex-1 flex-col gap-3">
            {focusedNode !== null ? (
              <>
                <div className="rounded-2xl border border-[color:var(--pp-border)] bg-white/85 px-4 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Person
                  </div>
                  <div className="mt-2 text-xl font-semibold text-slate-950">
                    {focusedNode.name}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    {formatCompactNumber(focusedNode.occurrenceCount)} total
                    occurrences in the current range
                  </div>
                  <button
                    type="button"
                    onClick={() => onTogglePerson(focusedNode.id)}
                    className={[
                      "mt-4 rounded-full border px-3 py-1.5 text-xs font-medium transition",
                      selectedPersonIds.has(focusedNode.id)
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-[color:var(--pp-border)] bg-white text-slate-700 hover:bg-slate-50",
                    ].join(" ")}
                  >
                    {selectedPersonIds.has(focusedNode.id)
                      ? "Remove global filter"
                      : "Filter to person"}
                  </button>
                </div>
                <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto pr-1">
                  <div className="grid gap-2">
                    {topConnections.map((link) => {
                      const peerId =
                        link.sourceId === focusedNode.id
                          ? link.targetId
                          : link.sourceId;
                      const peerName = personNamesById.get(peerId) ?? peerId;

                      return (
                        <div
                          key={link.id}
                          className="rounded-2xl border border-[color:var(--pp-border)] bg-white/80 px-3 py-2"
                        >
                          <div className="text-sm font-medium text-slate-900">
                            {peerName}
                          </div>
                          <div className="mt-1 text-xs text-slate-500">
                            Shared weight {link.weight}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </>
            ) : (
              <div className="rounded-2xl border border-dashed border-[color:var(--pp-border)] bg-white/55 px-4 py-5 text-sm text-slate-600">
                No node is focused. Hover or click a person in the graph to inspect
                its local neighborhood.
              </div>
            )}
          </div>
        </PanelCard>
        <PanelCard
          title="Active Nodes"
          description="Frequent people remain easy to reselect from the side rail."
        >
          <div className="thin-scrollbar flex min-h-0 flex-1 flex-wrap content-start gap-2 overflow-y-auto pr-1">
            {[...graph.persons]
              .sort(
                (left, right) =>
                  right.occurrenceCount - left.occurrenceCount ||
                  left.name.localeCompare(right.name),
              )
              .slice(0, 16)
              .map((person) => {
                const isSelected = selectedPersonIds.has(person.id);
                const isFocused = focusedNode?.id === person.id;

                return (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => {
                      setFocusedNodeId(person.id);
                    }}
                    className={[
                      "rounded-full border px-3 py-1.5 text-left text-[12px] transition",
                      isSelected
                        ? "border-slate-900 bg-slate-900 text-white"
                        : isFocused
                          ? "border-[#7c4b21] bg-amber-100/90 text-[#5f3918]"
                          : "border-[color:var(--pp-border)] bg-white/80 text-slate-700 hover:bg-white",
                    ].join(" ")}
                  >
                    {person.name} | {person.occurrenceCount}
                  </button>
                );
              })}
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

export function SocialGraphView({
  state,
  error,
  graph,
  selectedPersons,
  selectedTags,
  onTogglePerson,
}: SocialGraphViewProps) {
  if (state === "loading") {
    return (
      <section className="panel-surface flex h-full min-h-0 items-center p-5 lg:p-6">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Social Graph
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-950">
            Loading person-network projection
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            The shell is requesting canonical co-occurrence data for the current
            time range and persistent person selection.
          </p>
        </div>
      </section>
    );
  }

  if (state === "error") {
    return (
      <section className="panel-surface flex h-full min-h-0 items-center p-5 lg:p-6">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Social Graph
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-950">
            The social graph could not load
          </h1>
          <p className="mt-3 text-sm text-rose-700">
            {error ?? "The social-graph request failed."}
          </p>
        </div>
      </section>
    );
  }

  if (graph === null || graph.persons.length === 0) {
    return (
      <section className="panel-surface flex h-full min-h-0 items-center p-5 lg:p-6">
        <div className="max-w-2xl">
          <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
            Social Graph
          </p>
          <h1 className="mt-2 text-2xl font-semibold text-slate-950">
            No person network is available
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            No qualifying person co-occurrences were found for the active time
            range and supported persistent filters.
          </p>
          {selectedTags.length > 0 ? (
            <p className="mt-3 text-sm text-amber-800">
              Tag filters remain selected globally but are not applied to the
              social graph yet.
            </p>
          ) : null}
        </div>
      </section>
    );
  }

  return (
    <SocialGraphCanvas
      graph={graph}
      selectedPersons={selectedPersons}
      onTogglePerson={onTogglePerson}
    />
  );
}
