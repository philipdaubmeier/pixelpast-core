import {
  manageDataTransport,
  type ApiPersonGroupsCatalogResponse,
  type ApiPersonsCatalogResponse,
} from "../../api/manageDataTransport";
import type {
  PersonCatalogDraftRow,
  PersonGroupCatalogDraftRow,
} from "./types";

function toDraftPersonsCatalog(
  response: ApiPersonsCatalogResponse,
): PersonCatalogDraftRow[] {
  return response.persons.map((person) => ({
    id: String(person.id),
    name: person.name,
    aliases: [...person.aliases],
    path: person.path ?? "",
  }));
}

function toDraftPersonGroupsCatalog(
  response: ApiPersonGroupsCatalogResponse,
): PersonGroupCatalogDraftRow[] {
  return response.person_groups.map((group) => ({
    id: String(group.id),
    name: group.name,
    memberCount: group.member_count,
  }));
}

function toPersistedIdentifier(rowId: string): number | undefined {
  const parsedId = Number(rowId);
  return Number.isInteger(parsedId) && parsedId > 0 ? parsedId : undefined;
}

function toOptionalText(value: string): string | null {
  const trimmedValue = value.trim();
  return trimmedValue === "" ? null : trimmedValue;
}

export const manageDataClient = {
  async loadPersonsCatalog(): Promise<PersonCatalogDraftRow[]> {
    return toDraftPersonsCatalog(await manageDataTransport.getPersonsCatalog());
  },

  async savePersonsCatalog(
    rows: PersonCatalogDraftRow[],
  ): Promise<PersonCatalogDraftRow[]> {
    const response = await manageDataTransport.savePersonsCatalog({
      persons: rows.map((row) => ({
        id: toPersistedIdentifier(row.id),
        name: row.name,
        aliases: [...row.aliases],
        path: toOptionalText(row.path),
      })),
      delete_ids: [],
    });

    return toDraftPersonsCatalog(response);
  },

  async loadPersonGroupsCatalog(): Promise<PersonGroupCatalogDraftRow[]> {
    return toDraftPersonGroupsCatalog(
      await manageDataTransport.getPersonGroupsCatalog(),
    );
  },

  async savePersonGroupsCatalog(
    rows: PersonGroupCatalogDraftRow[],
  ): Promise<PersonGroupCatalogDraftRow[]> {
    const response = await manageDataTransport.savePersonGroupsCatalog({
      person_groups: rows.map((row) => ({
        id: toPersistedIdentifier(row.id),
        name: row.name,
      })),
      delete_ids: [],
    });

    return toDraftPersonGroupsCatalog(response);
  },
};
