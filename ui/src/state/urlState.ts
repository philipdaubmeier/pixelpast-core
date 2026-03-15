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
  const viewModeParam = params.get("viewMode");

  return {
    viewMode: viewModeParam?.trim() || defaultUiState.viewMode,
    selectedPersons: parseList(params.get("persons")),
    selectedTags: parseList(params.get("tags")),
  };
}

export function writePersistentUiState(state: PersistentUiState): string {
  const params = new URLSearchParams();

  if (state.viewMode !== defaultUiState.viewMode) {
    params.set("viewMode", state.viewMode);
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
