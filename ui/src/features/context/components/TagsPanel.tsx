import { PanelCard } from "../../../components/PanelCard";
import { Pill } from "../../../components/Pill";
import type { TagPanelItemProjection } from "../../../projections/exploration";

type TagsPanelProps = {
  tags: TagPanelItemProjection[];
  hoveredDate: string | null;
  onToggleTag: (tagPath: string) => void;
};

export function TagsPanel({
  tags,
  hoveredDate,
  onToggleTag,
}: TagsPanelProps) {
  const hasTags = tags.length > 0;

  return (
    <PanelCard
      eyebrow="Context"
      title="Tags"
      description={
        hoveredDate
          ? `Showing tag context for ${hoveredDate} without mutating the current view mode.`
          : "Tag chips are persistent filters; hover remains temporary and contextual."
      }
    >
      {hasTags ? (
        <>
          <div className="flex flex-wrap gap-2">
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
          <div className="mt-4 space-y-2">
            {tags.map((tag) => (
              <div
                key={`${tag.path}-meta`}
                className={[
                  "rounded-2xl border px-3 py-2 text-sm text-slate-700 transition",
                  tag.isSelected
                    ? "border-slate-900/15 bg-slate-900/5"
                    : "border-transparent bg-white/60",
                  tag.isHoverHighlighted
                    ? "ring-2 ring-amber-400/60 ring-offset-2 ring-offset-[color:rgba(250,247,240,0.9)]"
                    : "",
                ].join(" ")}
              >
                {tag.path}
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="flex h-full min-h-32 items-center justify-center rounded-[22px] border border-dashed border-[color:var(--pp-border)] bg-white/35 px-4 text-center text-sm text-slate-500">
          {hoveredDate
            ? "No mocked tag context is attached to this day."
            : "Hover a day to inspect its tags. Persistent tag filters remain independent from hover."}
        </div>
      )}
    </PanelCard>
  );
}
