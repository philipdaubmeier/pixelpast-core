import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  defaultUiState,
  type HoveredPanelItem,
  type PixelPastUiState,
  type ViewMode,
} from "./ui-state";
import { readPersistentUiState, writePersistentUiState } from "./urlState";

type UiStateContextValue = {
  state: PixelPastUiState;
  setHoveredDate: (date: string | null) => void;
  setHoveredPanelItem: (item: HoveredPanelItem | null) => void;
  setViewMode: (viewMode: ViewMode) => void;
  togglePerson: (personId: string) => void;
  toggleTag: (tagPath: string) => void;
  clearSelections: () => void;
};

const UiStateContext = createContext<UiStateContextValue | null>(null);

function createInitialState(): PixelPastUiState {
  if (typeof window === "undefined") {
    return defaultUiState;
  }

  return {
    ...defaultUiState,
    ...readPersistentUiState(window.location.search),
  };
}

export function UiStateProvider({ children }: PropsWithChildren) {
  const [state, setState] = useState<PixelPastUiState>(createInitialState);

  useEffect(() => {
    const nextSearch = writePersistentUiState({
      viewMode: state.viewMode,
      selectedPersons: state.selectedPersons,
      selectedTags: state.selectedTags,
    });
    const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;

    window.history.replaceState(null, "", nextUrl);
  }, [state.selectedPersons, state.selectedTags, state.viewMode]);

  useEffect(() => {
    function handlePopState() {
      const persistentState = readPersistentUiState(window.location.search);
      setState((currentState) => ({
        ...currentState,
        ...persistentState,
      }));
    }

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const value: UiStateContextValue = {
    state,
    setHoveredDate(date) {
      setState((currentState) => ({
        ...currentState,
        hoveredDate: date,
      }));
    },
    setHoveredPanelItem(item) {
      setState((currentState) => ({
        ...currentState,
        hoveredPanelItem: item,
      }));
    },
    setViewMode(viewMode) {
      setState((currentState) => ({
        ...currentState,
        viewMode,
      }));
    },
    togglePerson(personId) {
      setState((currentState) => {
        const nextSelection = currentState.selectedPersons.includes(personId)
          ? currentState.selectedPersons.filter(
              (candidate) => candidate !== personId,
            )
          : [...currentState.selectedPersons, personId];

        return {
          ...currentState,
          selectedPersons: nextSelection,
        };
      });
    },
    toggleTag(tagPath) {
      setState((currentState) => {
        const nextSelection = currentState.selectedTags.includes(tagPath)
          ? currentState.selectedTags.filter((candidate) => candidate !== tagPath)
          : [...currentState.selectedTags, tagPath];

        return {
          ...currentState,
          selectedTags: nextSelection,
        };
      });
    },
    clearSelections() {
      setState((currentState) => ({
        ...currentState,
        selectedPersons: [],
        selectedTags: [],
      }));
    },
  };

  return (
    <UiStateContext.Provider value={value}>{children}</UiStateContext.Provider>
  );
}

export function useUiState() {
  const context = useContext(UiStateContext);

  if (context === null) {
    throw new Error("useUiState must be used within UiStateProvider.");
  }

  return context;
}
