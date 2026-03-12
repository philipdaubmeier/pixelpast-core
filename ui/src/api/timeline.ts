import { mockDayContexts, mockHeatmapDays, mockViewModes } from "../mocks/timeline";
import type {
  DayContextProjection,
  HeatmapDayProjection,
  ViewModeOption,
} from "../projections/timeline";

export const timelineApi = {
  async listHeatmapDays(): Promise<HeatmapDayProjection[]> {
    return Promise.resolve(mockHeatmapDays);
  },
  async listViewModes(): Promise<ViewModeOption[]> {
    return Promise.resolve(mockViewModes);
  },
  async getDayContext(date: string | null): Promise<DayContextProjection | null> {
    if (date === null) {
      return Promise.resolve(null);
    }

    return Promise.resolve(mockDayContexts[date] ?? null);
  },
};
