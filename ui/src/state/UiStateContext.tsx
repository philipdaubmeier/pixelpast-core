import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useEffect,
  useMemo,
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

  const setHoveredDate = useCallback((date: string | null) => {
    setState((currentState) => {
      if (currentState.hoveredDate === date) {
        return currentState;
      }

      return {
        ...currentState,
        hoveredDate: date,
      };
    });
  }, []);

  const setHoveredPanelItem = useCallback((item: HoveredPanelItem | null) => {
    setState((currentState) => ({
      ...currentState,
      hoveredPanelItem: item,
    }));
  }, []);

  const setViewMode = useCallback((viewMode: ViewMode) => {
    setState((currentState) => {
      if (currentState.viewMode === viewMode) {
        return currentState;
      }

      return {
        ...currentState,
        viewMode,
      };
    });
  }, []);

  const togglePerson = useCallback((personId: string) => {
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
  }, []);

  const toggleTag = useCallback((tagPath: string) => {
    setState((currentState) => {
      const nextSelection = currentState.selectedTags.includes(tagPath)
        ? currentState.selectedTags.filter((candidate) => candidate !== tagPath)
        : [...currentState.selectedTags, tagPath];

      return {
        ...currentState,
        selectedTags: nextSelection,
      };
    });
  }, []);

  const clearSelections = useCallback(() => {
    setState((currentState) => {
      if (
        currentState.selectedPersons.length === 0 &&
        currentState.selectedTags.length === 0
      ) {
        return currentState;
      }

      return {
        ...currentState,
        selectedPersons: [],
        selectedTags: [],
      };
    });
  }, []);

  const value = useMemo<UiStateContextValue>(() => ({
    state,
    setHoveredDate,
    setHoveredPanelItem,
    setViewMode,
    togglePerson,
    toggleTag,
    clearSelections,
  }), [
    clearSelections,
    setHoveredDate,
    setHoveredPanelItem,
    setViewMode,
    state,
    togglePerson,
    toggleTag,
  ]);

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
