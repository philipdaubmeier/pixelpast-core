export type MainView = "day_grid" | "photo_album" | "social_graph";
export type GridView = string;

export type HoveredPanelItem =
  | { kind: "person"; id: string }
  | { kind: "tag"; path: string }
  | { kind: "map_point"; id: string };

export type DateRange = {
  from: string;
  to: string;
};

export type GeoFilter =
  | {
      kind: "radius";
      latitude: number;
      longitude: number;
      radiusMeters: number;
    }
  | {
      kind: "bbox";
      minLatitude: number;
      maxLatitude: number;
      minLongitude: number;
      maxLongitude: number;
    };

export type PixelPastUiState = {
  hoveredDate: string | null;
  hoveredPanelItem: HoveredPanelItem | null;
  mainView: MainView;
  gridView: GridView;
  selectedPersons: string[];
  selectedTags: string[];
  selectedGeoFilter: GeoFilter | null;
  selectedDateRange: DateRange | null;
};

export type PersistentUiState = Pick<
  PixelPastUiState,
  "mainView" | "gridView" | "selectedPersons" | "selectedTags"
>;

export const defaultUiState: PixelPastUiState = {
  hoveredDate: null,
  hoveredPanelItem: null,
  mainView: "day_grid",
  gridView: "activity",
  selectedPersons: [],
  selectedTags: [],
  selectedGeoFilter: null,
  selectedDateRange: null,
};
