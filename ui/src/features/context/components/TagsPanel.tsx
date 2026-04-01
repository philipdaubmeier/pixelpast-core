import { PanelCard } from "../../../components/PanelCard";
import { Pill } from "../../../components/Pill";
import type { TagPanelItemProjection } from "../../../projections/exploration";

type HoverContextStatus = "idle" | "loading" | "ready" | "error";

type TagsPanelProps = {
  tags: TagPanelItemProjection[];
  contextLabel: string | null;
  contextStatus: HoverContextStatus;
  contextError: string | null;
  loadingMessage?: string;
  errorMessage?: string;
  emptySelectionMessage?: string;
  onToggleTag: (tagPath: string) => void;
};

export function TagsPanel({
  tags,
  contextLabel,
  contextStatus,
  contextError,
  loadingMessage,
  errorMessage,
  emptySelectionMessage,
  onToggleTag,
}: TagsPanelProps) {
  const hasTags = tags.length > 0;

  return (
    <PanelCard title="Tags">
      {contextLabel !== null && contextStatus !== "ready" ? (
        <div
          className={[
            "mb-3 rounded-2xl border px-3 py-2 text-sm",
            contextStatus === "error"
              ? "border-rose-200 bg-rose-50 text-rose-700"
              : "border-amber-200 bg-amber-50 text-amber-700",
          ].join(" ")}
        >
          {contextStatus === "error"
            ? contextError ?? errorMessage ?? "Unable to load tag context."
            : loadingMessage ?? `Loading tag context for ${contextLabel}.`}
        </div>
      ) : null}
      {hasTags ? (
        <div className="thin-scrollbar -m-1 flex h-full content-start flex-wrap gap-2 overflow-y-auto p-2 pr-3">
          {tags.map((tag) => (
            <Pill
              key={tag.path}
              active={tag.isSelected}
              hoverHighlighted={tag.isHoverHighlighted}
              onClick={() => onToggleTag(tag.path)}
            >
              {tag.label}
            </Pill>
          ))}
        </div>
      ) : (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          {contextLabel && contextStatus === "loading"
            ? loadingMessage ?? "Loading tags linked to this selection."
            : contextLabel && contextStatus === "error"
              ? errorMessage ?? "Tag context could not be loaded."
            : contextLabel
            ? emptySelectionMessage ?? "No tags in the current selection."
            : "No tags in the current context."}
        </div>
      )}
    </PanelCard>
  );
}
