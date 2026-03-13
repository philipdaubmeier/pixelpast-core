import type { ReactNode } from "react";

type RightContextPaneProps = {
  children: ReactNode;
};

export function RightContextPane({ children }: RightContextPaneProps) {
  return <aside className="grid h-full min-h-0 grid-rows-3 gap-2">{children}</aside>;
}
