import type {
  PersonCatalogDraftRow,
  PersonGroupCatalogDraftRow,
} from "./types";

const LOAD_LATENCY_MS = 140;

let persistedPersonsCatalog: PersonCatalogDraftRow[] = [
  {
    id: "person-1",
    name: "Alex Morgan",
    aliases: ["Lex", "A. Morgan"],
    path: "family/alex-morgan",
  },
  {
    id: "person-2",
    name: "Samira Becker",
    aliases: ["Sam"],
    path: "friends/samira-becker",
  },
];

let persistedPersonGroupsCatalog: PersonGroupCatalogDraftRow[] = [
  {
    id: "group-1",
    name: "Immediate Family",
    path: "family/immediate",
    memberCount: 4,
  },
  {
    id: "group-2",
    name: "Berlin Friends",
    path: "friends/berlin",
    memberCount: 7,
  },
];

function clonePersonsCatalog(
  rows: PersonCatalogDraftRow[],
): PersonCatalogDraftRow[] {
  return rows.map((row) => ({
    ...row,
    aliases: [...row.aliases],
  }));
}

function clonePersonGroupsCatalog(
  rows: PersonGroupCatalogDraftRow[],
): PersonGroupCatalogDraftRow[] {
  return rows.map((row) => ({ ...row }));
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

export const manageDataClient = {
  async loadPersonsCatalog(): Promise<PersonCatalogDraftRow[]> {
    await delay(LOAD_LATENCY_MS);
    return clonePersonsCatalog(persistedPersonsCatalog);
  },

  async savePersonsCatalog(
    rows: PersonCatalogDraftRow[],
  ): Promise<PersonCatalogDraftRow[]> {
    await delay(LOAD_LATENCY_MS);
    persistedPersonsCatalog = clonePersonsCatalog(rows);
    return clonePersonsCatalog(persistedPersonsCatalog);
  },

  async loadPersonGroupsCatalog(): Promise<PersonGroupCatalogDraftRow[]> {
    await delay(LOAD_LATENCY_MS);
    return clonePersonGroupsCatalog(persistedPersonGroupsCatalog);
  },

  async savePersonGroupsCatalog(
    rows: PersonGroupCatalogDraftRow[],
  ): Promise<PersonGroupCatalogDraftRow[]> {
    await delay(LOAD_LATENCY_MS);
    persistedPersonGroupsCatalog = clonePersonGroupsCatalog(rows);
    return clonePersonGroupsCatalog(persistedPersonGroupsCatalog);
  },
};
