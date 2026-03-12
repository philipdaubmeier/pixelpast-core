export type ViewMode =
  | "activity"
  | "travel"
  | "sports"
  | "party_probability";

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
  viewMode: ViewMode;
  selectedPersons: string[];
  selectedTags: string[];
  selectedGeoFilter: GeoFilter | null;
  selectedDateRange: DateRange | null;
};

export type PersistentUiState = Pick<
  PixelPastUiState,
  "viewMode" | "selectedPersons" | "selectedTags"
>;

export const supportedViewModes: ViewMode[] = [
  "activity",
  "travel",
  "sports",
  "party_probability",
];

export const defaultUiState: PixelPastUiState = {
  hoveredDate: null,
  hoveredPanelItem: null,
  viewMode: "activity",
  selectedPersons: [],
  selectedTags: [],
  selectedGeoFilter: null,
  selectedDateRange: null,
};
