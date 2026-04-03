import {
  manageDataTransport,
  type ApiPersonGroupsCatalogResponse,
} from "./manageDataTransport";

export type PersonGroupProjection = {
  id: string;
  name: string;
  memberCount: number;
  colorIndex: number | null;
};

function mapPersonGroup(
  personGroup: ApiPersonGroupsCatalogResponse["person_groups"][number],
): PersonGroupProjection {
  return {
    id: String(personGroup.id),
    name: personGroup.name,
    memberCount: personGroup.member_count,
    colorIndex: personGroup.ui.color_index,
  };
}

export const personGroupsApi = {
  async getCatalog(): Promise<PersonGroupProjection[]> {
    const response = await manageDataTransport.getPersonGroupsCatalog();
    return response.person_groups.map(mapPersonGroup);
  },
};
