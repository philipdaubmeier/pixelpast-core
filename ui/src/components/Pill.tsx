import type { PropsWithChildren } from "react";

type PillProps = PropsWithChildren<{
  active?: boolean;
  muted?: boolean;
  onClick?: () => void;
}>;

export function Pill({
  active = false,
  muted = false,
  onClick,
  children,
}: PillProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        "rounded-full border px-3 py-1.5 text-sm transition",
        active
          ? "border-slate-900 bg-slate-900 text-white"
          : muted
            ? "border-transparent bg-white/60 text-slate-500"
            : "border-[color:var(--pp-border)] bg-white/70 text-slate-700 hover:bg-white",
      ].join(" ")}
    >
      {children}
    </button>
  );
}
