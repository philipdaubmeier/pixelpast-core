import type { ReactNode } from "react";

type RightContextPaneProps = {
  children: ReactNode;
};

export function RightContextPane({ children }: RightContextPaneProps) {
  return (
    <aside className="grid h-full min-h-0 grid-rows-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,1.15fr)_auto] gap-2">
      {children}
    </aside>
  );
}
