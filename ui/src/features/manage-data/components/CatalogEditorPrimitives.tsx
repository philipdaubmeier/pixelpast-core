import { useDeferredValue, type PropsWithChildren, type ReactNode } from "react";

type CatalogSectionFrameProps = PropsWithChildren<{
  title: string;
  description?: string;
  searchValue: string;
  searchPlaceholder: string;
  onSearchChange: (value: string) => void;
  addLabel: string;
  onAdd: () => void;
  statusBadge?: ReactNode;
}>;

export function CatalogSectionFrame({
  title,
  description,
  searchValue,
  searchPlaceholder,
  onSearchChange,
  addLabel,
  onAdd,
  statusBadge,
  children,
}: CatalogSectionFrameProps) {
  const deferredSearchValue = useDeferredValue(searchValue);

  return (
    <section className="flex h-full min-h-0 flex-col gap-1 overflow-hidden">
      <header className="panel-surface-strong flex flex-col gap-2 px-3 py-4 lg:px-3">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-2xl font-semibold text-slate-950">{title}</h1>
            {description ? (
              <p className="mt-1 max-w-3xl text-sm leading-6 text-slate-600">
                {description}
              </p>
            ) : null}
          </div>
          <div className="flex items-center gap-3">
            {statusBadge}
            <button
              type="button"
              onClick={onAdd}
              className="rounded-full border border-[color:var(--pp-border)] bg-slate-900 px-3 py-1.5 text-sm font-medium text-white shadow-[0_14px_30px_rgba(15,23,42,0.18)] transition hover:bg-slate-800"
            >
              {addLabel}
            </button>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex min-w-[18rem] flex-1 items-center gap-2 rounded-full border border-[color:var(--pp-border)] bg-white/75 px-3 py-1.5 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Search
            </span>
            <input
              type="search"
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder={searchPlaceholder}
              className="w-full border-none bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
            />
          </label>
          <p className="text-xs text-slate-500">
            Quick filter: {deferredSearchValue === "" ? "showing all rows" : deferredSearchValue}
          </p>
        </div>
      </header>
      <div className="min-h-0 flex flex-1 flex-col overflow-hidden">{children}</div>
    </section>
  );
}

export function CatalogTable({
  columns,
  gridClassName,
  children,
}: PropsWithChildren<{ columns: string[]; gridClassName?: string }>) {
  const resolvedGridClassName =
    gridClassName ??
    "grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(10rem,0.7fr)_minmax(8rem,0.6fr)]";

  return (
    <div className="panel-surface flex min-h-0 flex-1 flex-col overflow-hidden">
      <div
        className={[
          "grid gap-0.5 px-2 py-1.5 text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500",
          resolvedGridClassName,
        ].join(" ")}
      >
        {columns.map((column) => (
          <span key={column}>{column}</span>
        ))}
      </div>
      <div className="thin-scrollbar min-h-0 flex-1 overflow-y-auto overflow-x-hidden">{children}</div>
    </div>
  );
}

export function CatalogRow({
  children,
  gridClassName,
}: PropsWithChildren<{ gridClassName?: string }>) {
  const resolvedGridClassName =
    gridClassName ??
    "grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(10rem,0.7fr)_minmax(8rem,0.6fr)]";

  return (
    <div
      className={[
        "grid gap-0.5 px-2 py-0.5",
        resolvedGridClassName,
      ].join(" ")}
    >
      {children}
    </div>
  );
}

export function InlineTextField(props: {
  value: string;
  placeholder: string;
  onChange: (value: string) => void;
}) {
  return (
    <input
      type="text"
      value={props.value}
      onChange={(event) => props.onChange(event.target.value)}
      placeholder={props.placeholder}
      className="w-full rounded-lg border border-[color:rgba(98,80,46,0.16)] bg-white/80 px-1 py-0.5 text-sm text-slate-800 outline-none transition focus:border-slate-400 focus:bg-white"
    />
  );
}

export function ReadonlyCell({ children }: PropsWithChildren) {
  return (
    <div className="flex min-h-[2rem] items-center rounded-lg border border-dashed border-[color:rgba(98,80,46,0.16)] bg-[color:rgba(255,255,255,0.4)] px-1.5 text-sm text-slate-600">
      {children}
    </div>
  );
}

export function CatalogLoadingState({ label }: { label: string }) {
  return (
    <div className="panel-surface flex h-full min-h-[20rem] items-center justify-center px-6 text-center">
      <div>
        <p className="panel-title">Loading</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">{label}</h2>
        <p className="mt-2 text-sm text-slate-600">
          The section snapshot is being loaded into a local draft.
        </p>
      </div>
    </div>
  );
}

export function CatalogEmptyState({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  return (
    <div className="flex min-h-[18rem] items-center justify-center px-6 py-10 text-center">
      <div className="max-w-md">
        <p className="panel-title">Empty</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-slate-600">{description}</p>
      </div>
    </div>
  );
}

export function CatalogErrorState({
  title,
  description,
  onRetry,
}: {
  title: string;
  description: string;
  onRetry: () => void;
}) {
  return (
    <div className="panel-surface flex h-full min-h-[20rem] items-center justify-center px-6 text-center">
      <div className="max-w-lg">
        <p className="panel-title text-rose-600">Error</p>
        <h2 className="mt-2 text-xl font-semibold text-slate-950">{title}</h2>
        <p className="mt-2 text-sm leading-6 text-rose-700">{description}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-5 rounded-full border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-50"
        >
          Retry section load
        </button>
      </div>
    </div>
  );
}
