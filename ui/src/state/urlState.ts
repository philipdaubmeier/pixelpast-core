import { defaultUiState, type PersistentUiState } from "./ui-state";

function parseList(value: string | null): string[] {
  if (!value) {
    return [];
  }

  return Array.from(
    new Set(
      value
        .split(",")
        .map((entry) => entry.trim())
        .filter(Boolean),
    ),
  );
}

export function readPersistentUiState(search: string): PersistentUiState {
  const params = new URLSearchParams(search);
  const mainViewParam = params.get("mainView");
  const gridViewParam = params.get("gridView") ?? params.get("viewMode");

  return {
    mainView:
      mainViewParam?.trim() === "social_graph"
        ? "social_graph"
        : mainViewParam?.trim() === "photo_album"
          ? "photo_album"
        : mainViewParam?.trim() === "day_grid"
          ? "day_grid"
          : defaultUiState.mainView,
    gridView: gridViewParam?.trim() || defaultUiState.gridView,
    selectedPersons: parseList(params.get("persons")),
    selectedTags: parseList(params.get("tags")),
  };
}

export function writePersistentUiState(state: PersistentUiState): string {
  const params = new URLSearchParams();

  if (state.mainView !== defaultUiState.mainView) {
    params.set("mainView", state.mainView);
  }

  if (state.gridView !== defaultUiState.gridView) {
    params.set("gridView", state.gridView);
  }

  if (state.selectedPersons.length > 0) {
    params.set("persons", state.selectedPersons.join(","));
  }

  if (state.selectedTags.length > 0) {
    params.set("tags", state.selectedTags.join(","));
  }

  const serialized = params.toString();
  return serialized.length > 0 ? `?${serialized}` : "";
}
