export type ManageDataSectionId = "persons" | "person_groups";

export type PersonCatalogDraftRow = {
  id: string;
  name: string;
  aliases: string[];
  path: string;
};

export type PersonGroupCatalogDraftRow = {
  id: string;
  name: string;
  memberCount: number;
};

export type ManageDataSectionDescriptor = {
  id: ManageDataSectionId;
  label: string;
  description: string;
};
