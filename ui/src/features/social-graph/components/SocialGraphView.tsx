import {
  useEffect,
  useMemo,
  useState,
  type CSSProperties,
  type Dispatch,
  type SetStateAction,
} from "react";
import {
  SigmaContainer,
  useCamera,
  useRegisterEvents,
  useSetSettings,
  useSigma,
} from "@react-sigma/core";
import { useWorkerLayoutForceAtlas2 } from "@react-sigma/layout-forceatlas2";
import { UndirectedGraph } from "graphology";
import { EdgeLineProgram, NodeCircleProgram } from "sigma/rendering";
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

type SigmaNodeAttributes = {
  label: string;
  size: number;
  color: string;
  type: "circle";
  x: number;
  y: number;
  occurrenceCount: number;
  forceLabel?: boolean;
};

type SigmaEdgeAttributes = {
  label: string;
  size: number;
  color: string;
  type: "line";
  weight: number;
  layoutWeight: number;
};

type SigmaStyle = CSSProperties & Record<`--${string}`, string>;

type GraphLinkDetails = SocialGraphLinkProjection & {
  id: string;
};

type SocialGraphSigmaSceneProps = {
  sigmaGraph: UndirectedGraph<SigmaNodeAttributes, SigmaEdgeAttributes>;
  showAllNodeLabels: boolean;
  activeNodeId: string | null;
  focusedNodeId: string | null;
  hoveredLinkId: string | null;
  resetSequence: number;
  selectedPersonIds: Set<string>;
  activeNeighborhoodIds: Set<string>;
  activeLinkIds: Set<string>;
  setHoveredNodeId: Dispatch<SetStateAction<string | null>>;
  setHoveredLinkId: Dispatch<SetStateAction<string | null>>;
  setFocusedNodeId: Dispatch<SetStateAction<string | null>>;
  setCameraRatio: Dispatch<SetStateAction<number>>;
};

type SigmaProgramRegistrar = {
  registerEdgeProgram: (key: string, programClass: typeof EdgeLineProgram) => void;
  registerNodeProgram: (
    key: string,
    programClass: typeof NodeCircleProgram,
    hoverProgramClass?: typeof NodeCircleProgram,
  ) => void;
};

const BASE_NODE_COLOR = "#f8f2e8";
const ACTIVE_NODE_COLOR = "#f0c47f";
const SELECTED_NODE_COLOR = "#ca9f58";
const BASE_NODE_STROKE = "#8a6b43";
const ACTIVE_EDGE_COLOR = "#7c4b21";
const BASE_EDGE_RGB = "138, 107, 67";
const MIN_CAMERA_RATIO = 0.08;
const MAX_CAMERA_RATIO = 4;
const FORCE_ATLAS2_MIN_RUNTIME_MS = 2400;
const FORCE_ATLAS2_MAX_RUNTIME_MS = 6500;
const FORCE_ATLAS2_NODE_RUNTIME_MS = 24;
const FORCE_ATLAS2_EDGE_RUNTIME_MS = 7;
const FORCE_ATLAS2_SETTINGS = {
  settings: {
    adjustSizes: true,
    barnesHutOptimize: false,
    edgeWeightInfluence: 1,
    gravity: 0.18,
    linLogMode: true,
    scalingRatio: 7,
    slowDown: 1.4,
    strongGravityMode: false,
  },
  getEdgeWeight: "layoutWeight" as const,
};
const SIGMA_STYLE: SigmaStyle = {
  "--sigma-background-color": "transparent",
  "--sigma-controls-background-color": "rgba(255, 249, 241, 0.96)",
  "--sigma-controls-background-color-hover": "rgba(202, 159, 88, 0.18)",
  "--sigma-controls-border-color": "rgba(98, 80, 46, 0.22)",
  "--sigma-controls-color": "#7c4b21",
};
const SIGMA_SETTINGS = {
  allowInvalidContainer: true,
  defaultEdgeColor: `rgba(${BASE_EDGE_RGB}, 0.28)`,
  defaultEdgeType: "line",
  defaultNodeColor: BASE_NODE_COLOR,
  defaultNodeType: "circle",
  enableEdgeEvents: true,
  edgeProgramClasses: {
    line: EdgeLineProgram,
  },
  hideEdgesOnMove: false,
  hideLabelsOnMove: false,
  labelColor: { color: "#1c2430" },
  labelFont: "Aptos, Segoe UI, sans-serif",
  labelSize: 13,
  labelWeight: "600",
  maxCameraRatio: MAX_CAMERA_RATIO,
  minCameraRatio: MIN_CAMERA_RATIO,
  nodeHoverProgramClasses: {
    circle: NodeCircleProgram,
  },
  nodeProgramClasses: {
    circle: NodeCircleProgram,
  },
  renderEdgeLabels: false,
  renderLabels: true,
  stagePadding: 36,
  zIndex: true,
} as const;

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

function getLayoutEdgeWeight(weight: number, linkWeightScale: number): number {
  const safeScale = Math.max(linkWeightScale, 1);
  const normalized = Math.log1p(weight) / Math.log1p(safeScale);
  return 1 + clamp(normalized, 0, 1) * 7;
}

function createSigmaGraph(
  projection: SocialGraphProjection,
  showAllNodeLabels: boolean,
): UndirectedGraph<SigmaNodeAttributes, SigmaEdgeAttributes> {
  const sigmaGraph =
    new UndirectedGraph<SigmaNodeAttributes, SigmaEdgeAttributes>();
  const personNamesById = new Map(
    projection.persons.map((person) => [person.id, person.name]),
  );
  const maxOccurrenceCount = Math.max(
    ...projection.persons.map((person) => person.occurrenceCount),
    1,
  );
  const maxLinkWeight = Math.max(...projection.links.map((link) => link.weight), 1);
  const linkWeightScale = Math.max(
    getQuantile(
      projection.links.map((link) => link.weight),
      0.8,
    ),
    1,
  );
  const goldenAngle = Math.PI * (3 - Math.sqrt(5));
  const spiralSpacing = 2.35;

  [...projection.persons]
    .sort(
      (left, right) =>
        right.occurrenceCount - left.occurrenceCount ||
        left.name.localeCompare(right.name),
    )
    .forEach((person, index) => {
      const angle = index * goldenAngle;
      const distance = spiralSpacing * Math.sqrt(index + 1);

      sigmaGraph.addNode(person.id, {
        label: person.name,
        size: getNodeRadius(
          person.occurrenceCount,
          maxOccurrenceCount,
          projection.persons.length,
        ),
        color: BASE_NODE_COLOR,
        occurrenceCount: person.occurrenceCount,
        type: "circle",
        x: Math.cos(angle) * distance,
        y: Math.sin(angle) * distance,
        forceLabel: showAllNodeLabels,
      });
    });

  projection.links.forEach((link) => {
    const [sourceId, targetId] = link.personIds;
    const linkId = buildLinkId(sourceId, targetId);

    if (
      sourceId === targetId ||
      !sigmaGraph.hasNode(sourceId) ||
      !sigmaGraph.hasNode(targetId) ||
      sigmaGraph.hasEdge(linkId)
    ) {
      return;
    }

    const edgeOpacity = getLinkOpacity(link.weight, maxLinkWeight);

    sigmaGraph.addEdgeWithKey(linkId, sourceId, targetId, {
      label: buildLinkLabel(personNamesById, sourceId, targetId),
      size: getLinkStrokeWidth(link.weight, maxLinkWeight),
      color: `rgba(${BASE_EDGE_RGB}, ${edgeOpacity.toFixed(3)})`,
      type: "line",
      weight: link.weight,
      layoutWeight: getLayoutEdgeWeight(link.weight, linkWeightScale),
    });
  });

  return sigmaGraph;
}

function SocialGraphSigmaScene({
  sigmaGraph,
  showAllNodeLabels,
  activeNodeId,
  focusedNodeId,
  hoveredLinkId,
  resetSequence,
  selectedPersonIds,
  activeNeighborhoodIds,
  activeLinkIds,
  setHoveredNodeId,
  setHoveredLinkId,
  setFocusedNodeId,
  setCameraRatio,
}: SocialGraphSigmaSceneProps) {
  const sigma = useSigma<SigmaNodeAttributes, SigmaEdgeAttributes>();
  const sigmaProgramRegistrar = sigma as unknown as SigmaProgramRegistrar;
  const registerEvents = useRegisterEvents<
    SigmaNodeAttributes,
    SigmaEdgeAttributes
  >();
  const setSettings = useSetSettings<SigmaNodeAttributes, SigmaEdgeAttributes>();
  const { gotoNode, reset } = useCamera({ duration: 280 });
  const { kill, start, stop } =
    useWorkerLayoutForceAtlas2(FORCE_ATLAS2_SETTINGS);
  const layoutRuntimeMs = useMemo(
    () =>
      clamp(
        FORCE_ATLAS2_MIN_RUNTIME_MS +
          sigmaGraph.order * FORCE_ATLAS2_NODE_RUNTIME_MS +
          sigmaGraph.size * FORCE_ATLAS2_EDGE_RUNTIME_MS,
        FORCE_ATLAS2_MIN_RUNTIME_MS,
        FORCE_ATLAS2_MAX_RUNTIME_MS,
      ),
    [sigmaGraph],
  );

  useEffect(() => {
    sigmaProgramRegistrar.registerNodeProgram(
      "circle",
      NodeCircleProgram,
      NodeCircleProgram,
    );
    sigmaProgramRegistrar.registerEdgeProgram("line", EdgeLineProgram);
    setSettings({
      defaultEdgeType: "line",
      defaultNodeType: "circle",
      edgeProgramClasses: {
        line: EdgeLineProgram,
      },
      nodeHoverProgramClasses: {
        circle: NodeCircleProgram,
      },
      nodeProgramClasses: {
        circle: NodeCircleProgram,
      },
    });
  }, [setSettings, sigmaProgramRegistrar]);

  useEffect(() => {
    setCameraRatio(sigma.getCamera().getState().ratio);
  }, [setCameraRatio, sigma, sigmaGraph]);

  useEffect(() => {
    if (sigmaGraph.order <= 1) {
      reset({ duration: 180 });
      return;
    }

    let stopTimer = 0;
    let resetTimer = 0;

    resetTimer = window.setTimeout(() => {
      reset({ duration: 220 });
      start();
      stopTimer = window.setTimeout(() => {
        stop();
        reset({ duration: 260 });
      }, layoutRuntimeMs);
    }, 60);

    return () => {
      window.clearTimeout(resetTimer);
      window.clearTimeout(stopTimer);
      stop();
      kill();
    };
  }, [kill, layoutRuntimeMs, reset, sigmaGraph, start, stop]);

  useEffect(() => {
    if (focusedNodeId === null || !sigmaGraph.hasNode(focusedNodeId)) {
      return;
    }

    gotoNode(focusedNodeId, { duration: 260 });
  }, [focusedNodeId, gotoNode, sigmaGraph]);

  useEffect(() => {
    if (resetSequence === 0) {
      return;
    }

    reset({ duration: 260 });
  }, [reset, resetSequence]);

  useEffect(() => {
    registerEvents({
      clickNode: ({ node }) => {
        setFocusedNodeId((currentValue) =>
          currentValue === node ? null : node,
        );
        setHoveredNodeId(node);
        setHoveredLinkId(null);
      },
      clickStage: () => {
        setHoveredNodeId(null);
        setHoveredLinkId(null);
      },
      enterEdge: ({ edge }) => {
        setHoveredLinkId(edge);
        setHoveredNodeId(null);
      },
      enterNode: ({ node }) => {
        setHoveredNodeId(node);
        setHoveredLinkId(null);
      },
      leaveEdge: ({ edge }) => {
        setHoveredLinkId((currentValue) =>
          currentValue === edge ? null : currentValue,
        );
      },
      leaveNode: ({ node }) => {
        setHoveredNodeId((currentValue) =>
          currentValue === node ? null : currentValue,
        );
      },
      leaveStage: () => {
        setHoveredNodeId(null);
        setHoveredLinkId(null);
      },
      updated: () => {
        setCameraRatio(sigma.getCamera().getState().ratio);
      },
    });
  }, [
    registerEvents,
    setCameraRatio,
    setFocusedNodeId,
    setHoveredLinkId,
    setHoveredNodeId,
    sigma,
  ]);

  useEffect(() => {
    setSettings({
      edgeReducer: (edge, data) => {
        const isHovered = hoveredLinkId === edge;
        const isIncidentToActiveNode = activeLinkIds.has(edge);
        const isActive = isHovered || isIncidentToActiveNode;

        if (activeNodeId !== null && !isActive) {
          return {
            ...data,
            color: `rgba(${BASE_EDGE_RGB}, 0.1)`,
            size: Math.max(0.6, data.size * 0.72),
            zIndex: 0,
          };
        }

        return {
          ...data,
          color: isActive ? ACTIVE_EDGE_COLOR : data.color,
          size: isActive ? data.size + 1.2 : data.size,
          zIndex: isActive ? 2 : 1,
        };
      },
      labelRenderedSizeThreshold: showAllNodeLabels ? 0 : 9,
      nodeReducer: (node, data) => {
        const isActive = activeNodeId === node;
        const isFocused = focusedNodeId === node;
        const isSelected = selectedPersonIds.has(node);
        const isInActiveNeighborhood = activeNeighborhoodIds.has(node);
        const shouldDim =
          activeNodeId !== null &&
          !isInActiveNeighborhood &&
          !isFocused &&
          !isSelected;

        return {
          ...data,
          color: isSelected
            ? SELECTED_NODE_COLOR
            : isActive || isFocused
              ? ACTIVE_NODE_COLOR
              : shouldDim
                ? "rgba(248, 242, 232, 0.4)"
                : data.color,
          forceLabel:
            showAllNodeLabels || isSelected || isActive || isFocused,
          highlighted: isActive || isFocused || isSelected,
          size:
            data.size +
            (isSelected ? 1.4 : 0) +
            (isFocused ? 0.8 : 0) +
            (isActive ? 1.2 : 0),
          zIndex: isActive ? 3 : isFocused || isSelected ? 2 : 1,
        };
      },
    });
    sigma.refresh();

    return () => {
      setSettings({
        edgeReducer: null,
        nodeReducer: null,
      });
    };
  }, [
    activeLinkIds,
    activeNeighborhoodIds,
    activeNodeId,
    focusedNodeId,
    hoveredLinkId,
    selectedPersonIds,
    setSettings,
    showAllNodeLabels,
    sigma,
  ]);

  return null;
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
  const [cameraRatio, setCameraRatio] = useState(1);
  const [focusedNodeId, setFocusedNodeId] = useState<string | null>(null);
  const [hoveredLinkId, setHoveredLinkId] = useState<string | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [resetSequence, setResetSequence] = useState(0);
  const links = useMemo<GraphLinkDetails[]>(
    () =>
      graph.links.map((link) => ({
        ...link,
        id: buildLinkId(link.personIds[0], link.personIds[1]),
      })),
    [graph.links],
  );
  const showAllNodeLabels = graph.persons.length <= 80;
  const sigmaGraph = useMemo(
    () => createSigmaGraph(graph, showAllNodeLabels),
    [graph, showAllNodeLabels],
  );
  const personsById = useMemo(
    () => new Map(graph.persons.map((person) => [person.id, person])),
    [graph.persons],
  );
  const personNamesById = useMemo(
    () => new Map(graph.persons.map((person) => [person.id, person.name])),
    [graph.persons],
  );
  const linksById = useMemo(
    () => new Map(links.map((link) => [link.id, link])),
    [links],
  );
  const selectedPersonIds = useMemo(
    () => new Set(selectedPersons.map((person) => person.id)),
    [selectedPersons],
  );
  const activeNodeId = hoveredNodeId ?? focusedNodeId;
  const detailPerson =
    (activeNodeId !== null ? personsById.get(activeNodeId) : null) ?? null;
  const focusedLink =
    (hoveredLinkId !== null ? linksById.get(hoveredLinkId) : null) ?? null;
  const activeNeighborhoodIds = useMemo(() => {
    const neighborhoodIds = new Set<string>();

    if (activeNodeId === null) {
      return neighborhoodIds;
    }

    neighborhoodIds.add(activeNodeId);

    links.forEach((link) => {
      const [sourceId, targetId] = link.personIds;

      if (sourceId === activeNodeId) {
        neighborhoodIds.add(targetId);
      } else if (targetId === activeNodeId) {
        neighborhoodIds.add(sourceId);
      }
    });

    return neighborhoodIds;
  }, [activeNodeId, links]);
  const activeLinkIds = useMemo(() => {
    const linkIds = new Set<string>();

    if (activeNodeId === null) {
      return linkIds;
    }

    links.forEach((link) => {
      const [sourceId, targetId] = link.personIds;

      if (sourceId === activeNodeId || targetId === activeNodeId) {
        linkIds.add(link.id);
      }
    });

    return linkIds;
  }, [activeNodeId, links]);
  const topConnections = useMemo(() => {
    if (activeNodeId === null) {
      return [];
    }

    return [...links]
      .filter(
        (link) =>
          link.personIds[0] === activeNodeId ||
          link.personIds[1] === activeNodeId,
      )
      .sort((left, right) => right.weight - left.weight)
      .slice(0, 4);
  }, [activeNodeId, links]);
  const zoomPercent = Math.round((1 / clamp(cameraRatio, MIN_CAMERA_RATIO, MAX_CAMERA_RATIO)) * 100);

  useEffect(() => {
    const availablePersonIds = new Set(graph.persons.map((person) => person.id));
    const availableLinkIds = new Set(links.map((link) => link.id));

    setCameraRatio(1);
    setHoveredNodeId((currentValue) =>
      currentValue !== null && availablePersonIds.has(currentValue)
        ? currentValue
        : null,
    );
    setFocusedNodeId((currentValue) =>
      currentValue !== null && availablePersonIds.has(currentValue)
        ? currentValue
        : null,
    );
    setHoveredLinkId((currentValue) =>
      currentValue !== null && availableLinkIds.has(currentValue)
        ? currentValue
        : null,
    );
  }, [graph.persons, links]);

  return (
    <div className="grid h-full min-h-0 gap-3 xl:grid-cols-[minmax(0,1.35fr)_minmax(19rem,0.65fr)]">
      <PanelCard
        title="Social Graph"
        description="ForceAtlas2 clusters weighted co-occurrence links. Drag pans, wheel zooms, and hover reveals local structure."
        actions={
          <button
            type="button"
            onClick={() => {
              setResetSequence((currentValue) => currentValue + 1);
            }}
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
                {zoomPercent}%
              </div>
            </div>
          </div>
          <div className="subtle-grid relative min-h-[22rem] flex-1 overflow-hidden rounded-[2rem] border border-[color:var(--pp-border)] bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.95),_rgba(244,234,219,0.92)_54%,_rgba(229,214,190,0.95))]">
            <SigmaContainer
              className="h-full w-full"
              graph={sigmaGraph}
              style={SIGMA_STYLE}
              settings={SIGMA_SETTINGS}
            >
              <SocialGraphSigmaScene
                sigmaGraph={sigmaGraph}
                showAllNodeLabels={showAllNodeLabels}
                activeNodeId={activeNodeId}
                focusedNodeId={focusedNodeId}
                hoveredLinkId={hoveredLinkId}
                resetSequence={resetSequence}
                selectedPersonIds={selectedPersonIds}
                activeNeighborhoodIds={activeNeighborhoodIds}
                activeLinkIds={activeLinkIds}
                setHoveredNodeId={setHoveredNodeId}
                setHoveredLinkId={setHoveredLinkId}
                setFocusedNodeId={setFocusedNodeId}
                setCameraRatio={setCameraRatio}
              />
            </SigmaContainer>
            <div className="pointer-events-none absolute inset-x-0 bottom-0 flex justify-between px-4 pb-4 text-[11px] font-medium uppercase tracking-[0.18em] text-slate-500">
              <span>ForceAtlas2</span>
              <span>Drag to pan | Wheel to zoom</span>
            </div>
          </div>
          <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_auto]">
            <div className="rounded-2xl border border-[color:var(--pp-border)] bg-white/80 px-4 py-3 text-sm text-slate-700">
              {focusedLink !== null ? (
                <>
                  <span className="font-semibold text-slate-900">
                    {buildLinkLabel(
                      personNamesById,
                      focusedLink.personIds[0],
                      focusedLink.personIds[1],
                    )}
                  </span>
                  {` `}
                  carries weight {focusedLink.weight}.
                </>
              ) : detailPerson !== null ? (
                <>
                  <span className="font-semibold text-slate-900">
                    {detailPerson.name}
                  </span>
                  {` `}
                  appears in {formatCompactNumber(detailPerson.occurrenceCount)} shared
                  asset occurrence
                  {detailPerson.occurrenceCount === 1 ? "" : "s"}.
                </>
              ) : (
                "Hover a node or link to inspect the current cluster and its strongest local ties."
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
          description="Hover inspects the current cluster locally. Click a node to keep it pinned in the detail rail while you continue exploring."
        >
          <div className="flex min-h-0 flex-1 flex-col gap-3">
            {detailPerson !== null ? (
              <>
                <div className="rounded-2xl border border-[color:var(--pp-border)] bg-white/85 px-4 py-3">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Person
                  </div>
                  <div className="mt-2 text-xl font-semibold text-slate-950">
                    {detailPerson.name}
                  </div>
                  <div className="mt-1 text-sm text-slate-600">
                    {formatCompactNumber(detailPerson.occurrenceCount)} total
                    occurrences in the current range
                  </div>
                  <button
                    type="button"
                    onClick={() => onTogglePerson(detailPerson.id)}
                    className={[
                      "mt-4 rounded-full border px-3 py-1.5 text-xs font-medium transition",
                      selectedPersonIds.has(detailPerson.id)
                        ? "border-slate-900 bg-slate-900 text-white"
                        : "border-[color:var(--pp-border)] bg-white text-slate-700 hover:bg-slate-50",
                    ].join(" ")}
                  >
                    {selectedPersonIds.has(detailPerson.id)
                      ? "Remove global filter"
                      : "Filter to person"}
                  </button>
                </div>
                <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto pr-1">
                  <div className="grid gap-2">
                    {topConnections.map((link) => {
                      const [sourceId, targetId] = link.personIds;
                      const peerId =
                        sourceId === detailPerson.id ? targetId : sourceId;
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
                const isFocused = focusedNodeId === person.id;
                const isSelected = selectedPersonIds.has(person.id);

                return (
                  <button
                    key={person.id}
                    type="button"
                    onClick={() => {
                      setHoveredLinkId(null);
                      setHoveredNodeId(null);
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
