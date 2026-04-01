export type AlbumNodeSelection =
  | {
      kind: "folder";
      id: number;
    }
  | {
      kind: "collection";
      id: number;
    };

export type AlbumChromeState = {
  transportState: "loading" | "ready" | "error";
  transportError: string | null;
  resultSummary: string;
  hoverLabel: string;
};

export const defaultAlbumChromeState: AlbumChromeState = {
  transportState: "loading",
  transportError: null,
  resultSummary: "Preparing album navigation",
  hoverLabel: "not active",
};
