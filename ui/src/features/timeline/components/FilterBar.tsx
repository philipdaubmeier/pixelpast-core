import type {
  PersonProjection,
  TagProjection,
} from "../../../projections/timeline";
import type { PersonGroupProjection } from "../../../api/personGroups";
import { getPersonGroupColorOption } from "../../person-groups/palette";

type FilterBarProps = {
  scopeLabel: string;
  selectedPersons: PersonProjection[];
  selectedPersonGroups: PersonGroupProjection[];
  selectedTags: TagProjection[];
  resultSummary: string;
  hasPersistentFilters: boolean;
  transportState: "loading" | "ready" | "error";
  transportError: string | null;
  hoverLabel: string;
  onRemovePerson: (personId: string) => void;
  onRemovePersonGroup: (groupId: string) => void;
  onRemoveTag: (tagPath: string) => void;
  onClear: () => void;
};

export function FilterBar({
  scopeLabel,
  selectedPersons,
  selectedPersonGroups,
  selectedTags,
  resultSummary,
  hasPersistentFilters,
  transportState,
  transportError,
  hoverLabel,
  onRemovePerson,
  onRemovePersonGroup,
  onRemoveTag,
  onClear,
}: FilterBarProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        View: {scopeLabel}
      </div>
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        {hasPersistentFilters
          ? resultSummary
          : `${resultSummary} · no persistent filters`}
      </div>
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        {transportState === "loading"
          ? "Data: updating"
          : transportState === "error"
            ? transportError ?? "Data: request failed"
            : "Data: synced"}
      </div>
      <div className="rounded-full bg-white/70 px-3 py-1.5 text-[12px] text-slate-700">
        Hover: {hoverLabel}
      </div>
      {selectedPersons.map((person) => (
        <button
          key={person.id}
          type="button"
          onClick={() => onRemovePerson(person.id)}
          className="rounded-full border border-[color:var(--pp-border)] bg-white px-3 py-1.5 text-[12px] text-slate-700 transition hover:border-slate-900 hover:text-slate-900"
        >
          Person: {person.name} x
        </button>
      ))}
      {selectedPersonGroups.map((group) => {
        const colorOption = getPersonGroupColorOption(group.colorIndex);

        return (
          <button
            key={group.id}
            type="button"
            onClick={() => onRemovePersonGroup(group.id)}
            className="flex items-center gap-2 rounded-full border border-[color:var(--pp-border)] bg-white px-3 py-1.5 text-[12px] text-slate-700 transition hover:border-slate-900 hover:text-slate-900"
          >
            <span
              className="h-2.5 w-2.5 rounded-full border"
              style={{
                backgroundColor:
                  colorOption?.color ?? "rgba(98, 80, 46, 0.16)",
                borderColor:
                  colorOption?.borderColor ?? "rgba(98, 80, 46, 0.18)",
              }}
            />
            <span>Group: {group.name} x</span>
          </button>
        );
      })}
      {selectedTags.map((tag) => (
        <button
          key={tag.path}
          type="button"
          onClick={() => onRemoveTag(tag.path)}
          className="rounded-full border border-[color:var(--pp-border)] bg-white px-3 py-1.5 text-[12px] text-slate-700 transition hover:border-slate-900 hover:text-slate-900"
        >
          Tag: {tag.label} x
        </button>
      ))}
      <button
        type="button"
        onClick={onClear}
        disabled={!hasPersistentFilters}
        className="rounded-full border border-[color:var(--pp-border)] px-3 py-1.5 text-[12px] text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-45"
      >
        Clear selections
      </button>
    </div>
  );
}
