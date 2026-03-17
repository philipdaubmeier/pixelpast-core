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
  type GridView,
  type HoveredPanelItem,
  type MainView,
  type PixelPastUiState,
} from "./ui-state";
import { readPersistentUiState, writePersistentUiState } from "./urlState";

type UiStateContextValue = {
  state: PixelPastUiState;
  setHoveredDate: (date: string | null) => void;
  setHoveredPanelItem: (item: HoveredPanelItem | null) => void;
  setMainView: (mainView: MainView) => void;
  setGridView: (gridView: GridView) => void;
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
      mainView: state.mainView,
      gridView: state.gridView,
      selectedPersons: state.selectedPersons,
      selectedTags: state.selectedTags,
    });
    const nextUrl = `${window.location.pathname}${nextSearch}${window.location.hash}`;

    window.history.replaceState(null, "", nextUrl);
  }, [state.gridView, state.mainView, state.selectedPersons, state.selectedTags]);

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

  const setMainView = useCallback((mainView: MainView) => {
    setState((currentState) => {
      if (currentState.mainView === mainView) {
        return currentState;
      }

      return {
        ...currentState,
        mainView,
      };
    });
  }, []);

  const setGridView = useCallback((gridView: GridView) => {
    setState((currentState) => {
      if (currentState.gridView === gridView) {
        return currentState;
      }

      return {
        ...currentState,
        gridView,
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
    setMainView,
    setGridView,
    togglePerson,
    toggleTag,
    clearSelections,
  }), [
    clearSelections,
    setGridView,
    setHoveredDate,
    setHoveredPanelItem,
    setMainView,
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
