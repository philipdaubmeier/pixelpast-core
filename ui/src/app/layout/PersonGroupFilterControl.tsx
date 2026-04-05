import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
} from "react";
import { createPortal } from "react-dom";
import type { PersonGroupProjection } from "../../api/personGroups";
import { getPersonGroupColorOption } from "../../features/person-groups/palette";

type PersonGroupFilterControlProps = {
  groups: PersonGroupProjection[];
  selectedGroupIds: string[];
  state: "loading" | "ready" | "error";
  error: string | null;
  onToggleGroup: (groupId: string) => void;
  onClear: () => void;
};

function getSwatchStyle(colorIndex: number | null): CSSProperties {
  const option = getPersonGroupColorOption(colorIndex);

  if (option === null) {
    return {
      backgroundColor: "rgba(98, 80, 46, 0.12)",
      borderColor: "rgba(98, 80, 46, 0.18)",
    };
  }

  return {
    backgroundColor: option.color,
    borderColor: option.borderColor,
  };
}

export function PersonGroupFilterControl({
  groups,
  selectedGroupIds,
  state,
  error,
  onToggleGroup,
  onClear,
}: PersonGroupFilterControlProps) {
  const [isOpen, setIsOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const popupRef = useRef<HTMLDivElement | null>(null);
  const [popupStyle, setPopupStyle] = useState<CSSProperties | null>(null);
  const selectedGroupSet = useMemo(
    () => new Set(selectedGroupIds),
    [selectedGroupIds],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    function handlePointerDown(event: MouseEvent) {
      const target = event.target as Node;

      if (
        !containerRef.current?.contains(target) &&
        !popupRef.current?.contains(target)
      ) {
        setIsOpen(false);
      }
    }

    window.addEventListener("mousedown", handlePointerDown);
    return () => window.removeEventListener("mousedown", handlePointerDown);
  }, [isOpen]);

  useLayoutEffect(() => {
    if (!isOpen) {
      setPopupStyle(null);
      return;
    }

    function updatePopupStyle() {
      const triggerRect = containerRef.current?.getBoundingClientRect();

      if (triggerRect === undefined) {
        return;
      }

      const popupWidth = 352;
      const viewportPadding = 16;
      const desiredLeft = triggerRect.left;
      const maxLeft = window.innerWidth - popupWidth - viewportPadding;
      const nextLeft = Math.min(
        Math.max(desiredLeft, viewportPadding),
        Math.max(viewportPadding, maxLeft),
      );

      setPopupStyle({
        position: "fixed",
        top: triggerRect.bottom + 9,
        left: nextLeft,
        width: `${popupWidth}px`,
        zIndex: 35,
      });
    }

    updatePopupStyle();
    window.addEventListener("resize", updatePopupStyle);
    window.addEventListener("scroll", updatePopupStyle, true);

    return () => {
      window.removeEventListener("resize", updatePopupStyle);
      window.removeEventListener("scroll", updatePopupStyle, true);
    };
  }, [isOpen]);

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setIsOpen((currentValue) => !currentValue)}
        className={[
          "flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] transition",
          isOpen
            ? "border-slate-900 bg-white text-slate-900 shadow-[0_10px_24px_rgba(61,44,15,0.12)]"
            : "border-[color:var(--pp-border)] bg-white/80 text-slate-700 hover:bg-white",
        ].join(" ")}
      >
        <span className="font-medium">Person Groups</span>
        <span
          className={[
            "rounded-full px-2 py-0.5 text-[11px] font-semibold",
            selectedGroupIds.length > 0
              ? "bg-slate-900 text-white"
              : "bg-stone-100 text-slate-600",
          ].join(" ")}
        >
          {selectedGroupIds.length}
        </span>
      </button>
      {isOpen && popupStyle !== null
        ? createPortal(
            <div
              ref={popupRef}
              className="panel-surface-strong p-3"
              style={popupStyle}
            >
              <div className="flex items-center justify-between gap-3">
                <div>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Global Filter
                  </div>
                  <p className="mt-1 text-xs text-slate-600">
                    Multi-select persisted person groups across views.
                  </p>
                </div>
                <button
                  type="button"
                  onClick={onClear}
                  disabled={selectedGroupIds.length === 0}
                  className="rounded-full border border-[color:var(--pp-border)] px-2.5 py-1 text-[11px] font-medium text-slate-700 transition hover:bg-white disabled:cursor-not-allowed disabled:opacity-45"
                >
                  Clear
                </button>
              </div>
              <div className="mt-3">
                {state === "loading" ? (
                  <div className="rounded-2xl border border-dashed border-[color:var(--pp-border)] bg-white/50 px-3 py-4 text-sm text-slate-500">
                    Loading person groups.
                  </div>
                ) : state === "error" ? (
                  <div className="rounded-2xl border border-rose-200 bg-rose-50 px-3 py-4 text-sm text-rose-700">
                    {error ?? "Person groups could not be loaded."}
                  </div>
                ) : groups.length === 0 ? (
                  <div className="rounded-2xl border border-dashed border-[color:var(--pp-border)] bg-white/50 px-3 py-4 text-sm text-slate-500">
                    No persisted person groups are available yet.
                  </div>
                ) : (
                  <div className="thin-scrollbar max-h-72 space-y-1 overflow-y-auto pr-1">
                    {groups.map((group) => {
                      const isSelected = selectedGroupSet.has(group.id);
                      const colorOption = getPersonGroupColorOption(
                        group.colorIndex,
                      );

                      return (
                        <button
                          key={group.id}
                          type="button"
                          onClick={() => onToggleGroup(group.id)}
                          className={[
                            "flex w-full items-center gap-3 rounded-2xl border px-3 py-2 text-left transition",
                            isSelected
                              ? "border-slate-900 bg-slate-900 text-white"
                              : "border-[color:var(--pp-border)] bg-white/70 text-slate-700 hover:bg-white",
                          ].join(" ")}
                        >
                          <span
                            className="h-3.5 w-3.5 shrink-0 rounded-full border"
                            style={getSwatchStyle(group.colorIndex)}
                          />
                          <span className="min-w-0 flex-1">
                            <span className="block truncate text-[12px] font-medium">
                              {group.name}
                            </span>
                            <span
                              className={[
                                "block text-[11px]",
                                isSelected ? "text-white/75" : "text-slate-500",
                              ].join(" ")}
                            >
                              {group.memberCount} member
                              {group.memberCount === 1 ? "" : "s"}
                              {colorOption !== null
                                ? ` | ${colorOption.label}`
                                : ""}
                            </span>
                          </span>
                          <span
                            className={[
                              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                              isSelected
                                ? "bg-white/15 text-white"
                                : "bg-stone-100 text-slate-600",
                            ].join(" ")}
                          >
                            {isSelected ? "On" : "Off"}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>,
            document.body,
          )
        : null}
    </div>
  );
}
