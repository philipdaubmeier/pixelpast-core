import type { ReactNode } from "react";

type MainSplitLayoutProps = {
  left: ReactNode;
  right: ReactNode;
};

export function MainSplitLayout({ left, right }: MainSplitLayoutProps) {
  return (
    <div className="grid h-full min-h-0 gap-2 xl:grid-cols-[minmax(0,1fr)_22rem]">
      {left}
      {right}
    </div>
  );
}
