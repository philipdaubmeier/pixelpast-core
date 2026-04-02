import type { PropsWithChildren, ReactNode } from "react";

type PanelCardProps = PropsWithChildren<{
  title?: string;
  description?: string;
  actions?: ReactNode;
}>;

export function PanelCard({
  title,
  description,
  actions,
  children,
}: PanelCardProps) {
  const hasHeader = title !== undefined || description !== undefined || actions !== undefined;

  return (
    <section className="panel-surface-strong flex h-full min-h-0 flex-col p-3 lg:p-3.5">
      {hasHeader ? (
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            {title ? <h2 className="text-lg font-semibold text-slate-900">{title}</h2> : null}
            {description ? <p className="panel-copy mt-1">{description}</p> : null}
          </div>
          {actions}
        </div>
      ) : null}
      <div className={[hasHeader ? "mt-3" : "", "min-h-0 flex-1"].join(" ").trim()}>
        {children}
      </div>
    </section>
  );
}
