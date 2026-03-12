import { PanelCard } from "../../../components/PanelCard";
import { Pill } from "../../../components/Pill";
import type { PersonProjection } from "../../../projections/timeline";

type PersonsPanelProps = {
  persons: PersonProjection[];
  selectedPersonIds: string[];
  hoveredDate: string | null;
  onTogglePerson: (personId: string) => void;
};

export function PersonsPanel({
  persons,
  selectedPersonIds,
  hoveredDate,
  onTogglePerson,
}: PersonsPanelProps) {
  return (
    <PanelCard
      eyebrow="Context"
      title="Persons"
      description={
        hoveredDate
          ? `Reacting to ${hoveredDate} while keeping persistent person filters visible.`
          : "Hover a day to preview its people, or pin people as durable filters."
      }
    >
      <div className="flex flex-wrap gap-2">
        {persons.map((person) => (
          <Pill
            key={person.id}
            active={selectedPersonIds.includes(person.id)}
            onClick={() => onTogglePerson(person.id)}
          >
            {person.name}
          </Pill>
        ))}
      </div>
      <div className="mt-4 space-y-2">
        {persons.map((person) => (
          <div
            key={`${person.id}-meta`}
            className="flex items-center justify-between rounded-2xl bg-white/60 px-3 py-2 text-sm"
          >
            <span className="font-medium text-slate-800">{person.name}</span>
            <span className="text-slate-500">{person.role}</span>
          </div>
        ))}
      </div>
    </PanelCard>
  );
}
