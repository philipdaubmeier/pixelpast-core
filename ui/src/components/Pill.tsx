import type { PropsWithChildren } from "react";

type PillProps = PropsWithChildren<{
  active?: boolean;
  hoverHighlighted?: boolean;
  muted?: boolean;
  onClick?: () => void;
}>;

export function Pill({
  active = false,
  hoverHighlighted = false,
  muted = false,
  onClick,
  children,
}: PillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-full border px-2.5 py-1 text-[12px] leading-5 transition",
        active
          ? "border-slate-900 bg-slate-900 text-white"
          : muted
            ? "border-transparent bg-white/60 text-slate-500"
            : "border-[color:var(--pp-border)] bg-white/70 text-slate-700 hover:bg-white",
        hoverHighlighted
          ? "ring-2 ring-amber-400/70 ring-offset-2 ring-offset-[color:rgba(250,247,240,0.95)]"
          : "",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
