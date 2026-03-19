import type { DateRange } from "../projections/timeline";
import type { SocialGraphProjection } from "../projections/socialGraph";
import { socialGraphTransport } from "./socialGraphTransport";

export type SocialGraphFilters = {
  selectedPersons: string[];
  maxPeoplePerAsset: number;
};

export const socialGraphApi = {
  async getSocialGraph(
    range: DateRange,
    filters: SocialGraphFilters,
  ): Promise<SocialGraphProjection> {
    const response = await socialGraphTransport.getSocialGraph({
      start: range.start,
      end: range.end,
      maxPeoplePerAsset: filters.maxPeoplePerAsset,
      personIds: filters.selectedPersons,
    });

    return {
      persons: response.persons.map((person) => ({
        id: String(person.id),
        name: person.name,
        occurrenceCount: person.occurrence_count,
      })),
      links: response.links.map((link) => ({
        personIds: [String(link.person_ids[0]), String(link.person_ids[1])],
        affinity: link.affinity,
        weight: link.weight,
      })),
    };
  },
};
