import type { ReactNode } from "react";

type RightContextPaneProps = {
  children: ReactNode;
};

export function RightContextPane({ children }: RightContextPaneProps) {
  return <aside className="grid auto-rows-fr gap-4">{children}</aside>;
}
