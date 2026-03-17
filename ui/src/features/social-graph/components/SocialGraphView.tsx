import { PanelCard } from "../../../components/PanelCard";
import type { PersonProjection, TagProjection } from "../../../projections/timeline";
import type { SocialGraphProjection } from "../../../projections/socialGraph";

type SocialGraphViewProps = {
  state: "loading" | "ready" | "error";
  error: string | null;
  graph: SocialGraphProjection | null;
  selectedPersons: PersonProjection[];
  selectedTags: TagProjection[];
  onTogglePerson: (personId: string) => void;
};

function buildLinkLabel(
  personNamesById: Map<string, string>,
  leftPersonId: string,
  rightPersonId: string,
): string {
  const leftName = personNamesById.get(leftPersonId) ?? leftPersonId;
  const rightName = personNamesById.get(rightPersonId) ?? rightPersonId;
  return `${leftName} <-> ${rightName}`;
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

  const personNamesById = new Map(graph.persons.map((person) => [person.id, person.name]));
  const strongestLinks = [...graph.links]
    .sort((left, right) => right.weight - left.weight)
    .slice(0, 8);
  const topPersons = [...graph.persons]
    .sort(
      (left, right) => right.occurrenceCount - left.occurrenceCount || left.name.localeCompare(right.name),
    )
    .slice(0, 12);

  return (
    <section className="grid h-full min-h-0 gap-2 xl:grid-cols-[minmax(0,1.25fr)_minmax(20rem,0.75fr)]">
      <PanelCard
        title="Social Graph"
        description="Transport and shell are active. The force-directed renderer lands in the next task."
      >
        <div className="flex h-full min-h-0 flex-col gap-4">
          <div className="grid gap-3 sm:grid-cols-3">
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
                Selected persons
              </div>
              <div className="mt-2 text-3xl font-semibold text-slate-950">
                {selectedPersons.length}
              </div>
            </div>
          </div>
          <div className="flex min-h-[18rem] flex-1 items-center justify-center rounded-[2rem] border border-dashed border-[color:var(--pp-border)] bg-[radial-gradient(circle_at_top,_rgba(255,255,255,0.92),_rgba(241,245,249,0.88)_48%,_rgba(226,232,240,0.92))] p-6">
            <div className="max-w-xl text-center">
              <p className="text-[11px] font-semibold uppercase tracking-[0.22em] text-slate-500">
                Visualization Frame
              </p>
              <h2 className="mt-2 text-xl font-semibold text-slate-950">
                Graph canvas reserved for the physics view
              </h2>
              <p className="mt-3 text-sm text-slate-600">
                This ready-state placeholder confirms that switching, request
                transport, and view lifecycle are wired before the heavier
                simulation runtime is introduced.
              </p>
            </div>
          </div>
          {selectedTags.length > 0 ? (
            <div className="rounded-2xl border border-amber-200 bg-amber-50/90 px-4 py-3 text-sm text-amber-900">
              Active tag filters are preserved globally, but the current social
              graph endpoint only applies person and date filters.
            </div>
          ) : null}
        </div>
      </PanelCard>
      <div className="grid min-h-0 gap-2">
        <PanelCard
          title="Active Nodes"
          description="Selected people stay globally active and can still be refined from the graph shell."
        >
          <div className="thin-scrollbar flex min-h-0 flex-1 flex-wrap content-start gap-2 overflow-y-auto pr-1">
            {topPersons.map((person) => {
              const isSelected = selectedPersons.some(
                (selectedPerson) => selectedPerson.id === person.id,
              );

              return (
                <button
                  key={person.id}
                  type="button"
                  onClick={() => onTogglePerson(person.id)}
                  className={[
                    "rounded-full border px-3 py-1.5 text-left text-[12px] transition",
                    isSelected
                      ? "border-slate-900 bg-slate-900 text-white"
                      : "border-[color:var(--pp-border)] bg-white/80 text-slate-700 hover:bg-white",
                  ].join(" ")}
                >
                  {person.name} · {person.occurrenceCount}
                </button>
              );
            })}
          </div>
        </PanelCard>
        <PanelCard
          title="Strongest Links"
          description="A debug-ready edge list keeps the shell useful before the force layout exists."
        >
          <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto pr-1">
            <div className="grid gap-2">
              {strongestLinks.map((link) => (
                <div
                  key={`${link.personIds[0]}-${link.personIds[1]}`}
                  className="rounded-2xl border border-[color:var(--pp-border)] bg-white/80 px-3 py-2"
                >
                  <div className="text-sm font-medium text-slate-900">
                    {buildLinkLabel(
                      personNamesById,
                      link.personIds[0],
                      link.personIds[1],
                    )}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">
                    Weight {link.weight}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </PanelCard>
      </div>
    </section>
  );
}
