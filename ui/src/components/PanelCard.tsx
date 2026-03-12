import type { PropsWithChildren, ReactNode } from "react";

type PanelCardProps = PropsWithChildren<{
  eyebrow: string;
  title: string;
  description: string;
  actions?: ReactNode;
}>;

export function PanelCard({
  eyebrow,
  title,
  description,
  actions,
  children,
}: PanelCardProps) {
  return (
    <section className="panel-surface-strong flex h-full flex-col p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="panel-title">{eyebrow}</p>
          <div>
            <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
            <p className="panel-copy">{description}</p>
          </div>
        </div>
        {actions}
      </div>
      <div className="mt-5 flex-1">{children}</div>
    </section>
  );
}
