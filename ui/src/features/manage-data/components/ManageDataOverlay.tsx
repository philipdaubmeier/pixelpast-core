import { startTransition, useEffect, useMemo, useState } from "react";
import { manageDataClient } from "../client";
import type {
  ManageDataSectionDescriptor,
  ManageDataSectionId,
  PersonCatalogDraftRow,
  PersonGroupCatalogDraftRow,
  PersonGroupMembershipDraft,
  PersonGroupMembershipDraftMember,
} from "../types";
import {
  CatalogEmptyState,
  CatalogErrorState,
  CatalogLoadingState,
  CatalogRow,
  CatalogSectionFrame,
  CatalogTable,
  InlineTextField,
  ReadonlyCell,
} from "./CatalogEditorPrimitives";

const MANAGE_SECTIONS: ManageDataSectionDescriptor[] = [
  {
    id: "persons",
    label: "Persons",
    description: "Canonical people records, aliases, and timeline-facing paths.",
  },
  {
    id: "person_groups",
    label: "Person Groups",
    description:
      "Named group catalogs that later sections can extend with membership editing.",
  },
];

type SectionLoadState = "loading" | "ready" | "error";
type SectionSaveState = "idle" | "saving" | "error";
type MembershipLoadState = "idle" | "loading" | "ready" | "error";

type SectionRuntimeRows = PersonCatalogDraftRow[] | PersonGroupCatalogDraftRow[];

type MembershipRuntimeState = {
  status: MembershipLoadState;
  error: string | null;
  saveError: string | null;
  snapshot: PersonGroupMembershipDraft | null;
  draft: PersonGroupMembershipDraft | null;
  personOptions: PersonCatalogDraftRow[];
  searchQuery: string;
};

type SectionRuntimeState = {
  activeSectionId: ManageDataSectionId;
  status: SectionLoadState;
  saveState: SectionSaveState;
  searchQuery: string;
  error: string | null;
  saveError: string | null;
  snapshot: SectionRuntimeRows | null;
  draft: SectionRuntimeRows | null;
  deletedPersonGroupIds: number[];
  activePersonGroupMembershipRowId: string | null;
  membership: MembershipRuntimeState;
};

type PendingGuardAction =
  | { kind: "close" }
  | { kind: "switch"; nextSectionId: ManageDataSectionId }
  | { kind: "membership_back" }
  | null;

type PendingDeletePersonGroupAction = {
  rowId: string;
  name: string;
} | null;

const initialSectionState: SectionRuntimeState = {
  activeSectionId: "persons",
  status: "loading",
  saveState: "idle",
  searchQuery: "",
  error: null,
  saveError: null,
  snapshot: null,
  draft: null,
  deletedPersonGroupIds: [],
  activePersonGroupMembershipRowId: null,
  membership: {
    status: "idle",
    error: null,
    saveError: null,
    snapshot: null,
    draft: null,
    personOptions: [],
    searchQuery: "",
  },
};

function cloneSectionRows(rows: SectionRuntimeRows) {
  return JSON.parse(JSON.stringify(rows)) as typeof rows;
}

function getDraftFingerprint(rows: SectionRuntimeRows | null): string {
  return JSON.stringify(rows ?? []);
}

function createTemporaryId(prefix: string): string {
  return `${prefix}-${Math.random().toString(36).slice(2, 10)}`;
}

function toPersistedIdentifier(rowId: string): number | undefined {
  const parsedId = Number(rowId);
  return Number.isInteger(parsedId) && parsedId > 0 ? parsedId : undefined;
}

function getMembershipFingerprint(
  membership: PersonGroupMembershipDraft | null,
): string {
  return JSON.stringify(membership ?? null);
}

async function loadSectionData(
  sectionId: ManageDataSectionId,
): Promise<SectionRuntimeRows> {
  if (sectionId === "persons") {
    return manageDataClient.loadPersonsCatalog();
  }

  return manageDataClient.loadPersonGroupsCatalog();
}

function PersonGroupMembershipSection(props: {
  membership: PersonGroupMembershipDraft;
  searchQuery: string;
  saveError: string | null;
  personOptions: PersonCatalogDraftRow[];
  dirty: boolean;
  onSearchChange: (value: string) => void;
  onAddMember: (personId: string) => void;
  onRemoveMember: (personId: string) => void;
  onClose: () => void;
}) {
  const availableSuggestions = useMemo(() => {
    const normalizedQuery = props.searchQuery.trim().toLowerCase();
    const memberIds = new Set(props.membership.members.map((member) => member.id));

    return props.personOptions
      .filter((person) => !memberIds.has(person.id))
      .filter((person) => {
        if (normalizedQuery === "") {
          return true;
        }

        return [person.name, person.aliases.join(", "), person.path]
          .join(" ")
          .toLowerCase()
          .includes(normalizedQuery);
      })
      .slice(0, 8);
  }, [props.membership.members, props.personOptions, props.searchQuery]);

  const firstSuggestion = availableSuggestions[0] ?? null;

  return (
    <section className="flex h-full min-h-0 flex-col gap-4">
      <header className="panel-surface-strong flex flex-col gap-4 px-5 py-4 lg:px-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="panel-title">Manage Data</p>
            <h1 className="mt-2 text-2xl font-semibold text-slate-950">
              Person Group Membership
            </h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              Review and replace the persisted membership set for{" "}
              <span className="font-semibold text-slate-900">
                {props.membership.groupName || "Untitled group"}
              </span>
              . This subview keeps one group in focus with one explicit member
              draft.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <span
              className={[
                "rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
                props.dirty
                  ? "bg-amber-100 text-amber-800"
                  : "bg-emerald-100 text-emerald-800",
              ].join(" ")}
            >
              {props.dirty ? "Draft changed" : "In sync"}
            </span>
            <button
              type="button"
              onClick={props.onClose}
              className="rounded-full border border-[color:var(--pp-border)] bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-white"
            >
              Back to catalog
            </button>
          </div>
        </div>
        <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]">
          <label className="flex items-center gap-2 rounded-[24px] border border-[color:var(--pp-border)] bg-white/80 px-4 py-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.8)]">
            <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">
              Add member
            </span>
            <input
              type="search"
              value={props.searchQuery}
              onChange={(event) => props.onSearchChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && firstSuggestion !== null) {
                  event.preventDefault();
                  props.onAddMember(firstSuggestion.id);
                }
              }}
              placeholder="Search persisted persons by name, alias, or path"
              className="w-full border-none bg-transparent text-sm text-slate-800 outline-none placeholder:text-slate-400"
            />
          </label>
          <div className="rounded-[24px] border border-[color:rgba(98,80,46,0.14)] bg-[color:rgba(255,255,255,0.45)] px-4 py-3 text-sm text-slate-600">
            {props.membership.memberCount} persisted members at last reload
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {availableSuggestions.length === 0 ? (
            <span className="rounded-full border border-dashed border-[color:rgba(98,80,46,0.16)] px-3 py-1.5 text-xs text-slate-500">
              {props.searchQuery.trim() === ""
                ? "Type to search persisted persons."
                : "No matching persisted persons available."}
            </span>
          ) : (
            availableSuggestions.map((person) => (
              <button
                key={person.id}
                type="button"
                onClick={() => props.onAddMember(person.id)}
                className="rounded-full border border-[color:rgba(15,23,42,0.12)] bg-white px-3 py-1.5 text-left text-sm text-slate-800 transition hover:bg-slate-50"
              >
                {person.name}
                {person.path ? ` - ${person.path}` : ""}
              </button>
            ))
          )}
        </div>
        {props.saveError ? (
          <p className="text-sm text-rose-700">{props.saveError}</p>
        ) : null}
      </header>
      <div className="panel-surface min-h-0 flex-1 overflow-hidden">
        <div className="border-b border-[color:var(--pp-border)] px-5 py-3">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
            Current draft member list
          </p>
        </div>
        <div className="thin-scrollbar min-h-0 overflow-auto px-5 py-4">
          {props.membership.members.length === 0 ? (
            <CatalogEmptyState
              title="No members in this draft"
              description="Use the persisted-person picker above to assemble the authoritative membership set before saving."
            />
          ) : (
            <div className="flex flex-col gap-3">
              {props.membership.members.map((member) => (
                <div
                  key={member.id}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-[color:rgba(98,80,46,0.14)] bg-white/70 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-semibold text-slate-900">
                      {member.name}
                    </p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">
                      {[member.path, member.aliases.join(", ")]
                        .filter((value) => value.trim() !== "")
                        .join(" • ") || "No path or aliases"}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => props.onRemoveMember(member.id)}
                    className="rounded-full border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-800 transition hover:bg-rose-100"
                  >
                    Remove member
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  );
}

async function saveSectionData(
  sectionId: ManageDataSectionId,
  rows: SectionRuntimeRows,
  deletedPersonGroupIds: number[] = [],
): Promise<SectionRuntimeRows> {
  if (sectionId === "persons") {
    return manageDataClient.savePersonsCatalog(rows as PersonCatalogDraftRow[]);
  }

  return manageDataClient.savePersonGroupsCatalog(
    rows as PersonGroupCatalogDraftRow[],
    deletedPersonGroupIds,
  );
}

function PersonsSection(props: {
  rows: PersonCatalogDraftRow[];
  searchQuery: string;
  dirty: boolean;
  onSearchChange: (value: string) => void;
  onAdd: () => void;
  onChangeRow: (
    rowId: string,
    field: "name" | "aliases" | "path",
    value: string,
  ) => void;
}) {
  const filteredRows = useMemo(() => {
    const normalizedQuery = props.searchQuery.trim().toLowerCase();

    if (normalizedQuery === "") {
      return props.rows;
    }

    return props.rows.filter((row) =>
      [row.name, row.aliases.join(", "), row.path].some((value) =>
        value.toLowerCase().includes(normalizedQuery),
      ),
    );
  }, [props.rows, props.searchQuery]);

  return (
    <CatalogSectionFrame
      eyebrow="Manage Data"
      title="Persons"
      description="This draft-first editor establishes the shared person catalog runtime without calling the API on every keystroke."
      searchValue={props.searchQuery}
      searchPlaceholder="Search name, aliases, or path"
      onSearchChange={props.onSearchChange}
      addLabel="+ Add person"
      onAdd={props.onAdd}
      statusBadge={
        <span
          className={[
            "rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
            props.dirty
              ? "bg-amber-100 text-amber-800"
              : "bg-emerald-100 text-emerald-800",
          ].join(" ")}
        >
          {props.dirty ? "Draft changed" : "In sync"}
        </span>
      }
    >
      <CatalogTable columns={["Display Name", "Aliases", "Path", "Notes"]}>
        {filteredRows.length === 0 ? (
          <CatalogEmptyState
            title="No matching people"
            description="Adjust the quick search or add a new draft row to continue shaping the catalog."
          />
        ) : (
          filteredRows.map((row) => (
            <CatalogRow key={row.id}>
              <InlineTextField
                value={row.name}
                placeholder="Display name"
                onChange={(value) => props.onChangeRow(row.id, "name", value)}
              />
              <InlineTextField
                value={row.aliases.join(", ")}
                placeholder="Comma-separated aliases"
                onChange={(value) => props.onChangeRow(row.id, "aliases", value)}
              />
              <InlineTextField
                value={row.path}
                placeholder="catalog/path"
                onChange={(value) => props.onChangeRow(row.id, "path", value)}
              />
              <ReadonlyCell>Deletion intentionally unavailable in v1.</ReadonlyCell>
            </CatalogRow>
          ))
        )}
      </CatalogTable>
    </CatalogSectionFrame>
  );
}

function PersonGroupsSection(props: {
  rows: PersonGroupCatalogDraftRow[];
  searchQuery: string;
  dirty: boolean;
  onSearchChange: (value: string) => void;
  onAdd: () => void;
  onChangeRow: (rowId: string, field: "name", value: string) => void;
  onDeleteRow: (rowId: string) => void;
  onOpenMembershipEditor: (rowId: string) => void;
}) {
  const filteredRows = useMemo(() => {
    const normalizedQuery = props.searchQuery.trim().toLowerCase();

    if (normalizedQuery === "") {
      return props.rows;
    }

    return props.rows.filter((row) =>
      [row.name, String(row.memberCount)].some((value) =>
        value.toLowerCase().includes(normalizedQuery),
      ),
    );
  }, [props.rows, props.searchQuery]);

  return (
    <CatalogSectionFrame
      eyebrow="Manage Data"
      title="Person Groups"
      description="Create, rename, and stage deletions for canonical groups while keeping member counts read-only and membership editing in a dedicated subview."
      searchValue={props.searchQuery}
      searchPlaceholder="Search group name"
      onSearchChange={props.onSearchChange}
      addLabel="+ Add group"
      onAdd={props.onAdd}
      statusBadge={
        <span
          className={[
            "rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
            props.dirty
              ? "bg-amber-100 text-amber-800"
              : "bg-emerald-100 text-emerald-800",
          ].join(" ")}
        >
          {props.dirty ? "Draft changed" : "In sync"}
        </span>
      }
    >
      <CatalogTable columns={["Group Name", "Members", "Membership", "Delete"]}>
        {filteredRows.length === 0 ? (
          <CatalogEmptyState
            title="No matching groups"
            description="Adjust the quick search or add a new draft row to continue shaping the group catalog."
          />
        ) : (
          filteredRows.map((row) => (
            <CatalogRow key={row.id}>
              <InlineTextField
                value={row.name}
                placeholder="Group name"
                onChange={(value) => props.onChangeRow(row.id, "name", value)}
              />
              <ReadonlyCell>{row.memberCount} persisted members</ReadonlyCell>
              <div className="flex min-h-[2.75rem] items-center">
                <button
                  type="button"
                  onClick={() => props.onOpenMembershipEditor(row.id)}
                  disabled={toPersistedIdentifier(row.id) === undefined || props.dirty}
                  className="rounded-full border border-[color:rgba(15,23,42,0.12)] bg-white px-3 py-2 text-sm font-medium text-slate-800 transition hover:bg-slate-50"
                >
                  Manage members
                </button>
              </div>
              <div className="flex min-h-[2.75rem] items-center">
                <button
                  type="button"
                  onClick={() => props.onDeleteRow(row.id)}
                  className="rounded-full border border-rose-200 bg-rose-50 px-3 py-2 text-sm font-medium text-rose-800 transition hover:bg-rose-100"
                >
                  Delete group
                </button>
              </div>
            </CatalogRow>
          ))
        )}
      </CatalogTable>
    </CatalogSectionFrame>
  );
}

export function ManageDataOverlay(props: {
  isOpen: boolean;
  onClose: () => void;
}) {
  const [sectionState, setSectionState] =
    useState<SectionRuntimeState>(initialSectionState);
  const [pendingGuardAction, setPendingGuardAction] =
    useState<PendingGuardAction>(null);
  const [pendingDeletePersonGroupAction, setPendingDeletePersonGroupAction] =
    useState<PendingDeletePersonGroupAction>(null);

  const membershipDirty =
    sectionState.activePersonGroupMembershipRowId !== null &&
    getMembershipFingerprint(sectionState.membership.snapshot) !==
      getMembershipFingerprint(sectionState.membership.draft);
  const isDirty =
    sectionState.activePersonGroupMembershipRowId !== null
      ? membershipDirty
      : sectionState.status === "ready" &&
        (getDraftFingerprint(sectionState.snapshot) !==
          getDraftFingerprint(sectionState.draft) ||
          sectionState.deletedPersonGroupIds.length > 0);

  useEffect(() => {
    if (!props.isOpen) {
      return;
    }

    void activateSection("persons");
  }, [props.isOpen]);

  async function loadMembershipEditor(groupId: number) {
    startTransition(() => {
      setSectionState((currentState) => ({
        ...currentState,
        membership: {
          ...currentState.membership,
          status: "loading",
          error: null,
          saveError: null,
          snapshot: null,
          draft: null,
          searchQuery: "",
        },
      }));
    });

    try {
      const [membership, personOptions] = await Promise.all([
        manageDataClient.loadPersonGroupMembership(groupId),
        manageDataClient.loadPersonsCatalog(),
      ]);
      startTransition(() => {
        setSectionState((currentState) => {
          if (
            currentState.activeSectionId !== "person_groups" ||
            currentState.activePersonGroupMembershipRowId !== String(groupId)
          ) {
            return currentState;
          }

          return {
            ...currentState,
            membership: {
              status: "ready",
              error: null,
              saveError: null,
              snapshot: JSON.parse(JSON.stringify(membership)),
              draft: JSON.parse(JSON.stringify(membership)),
              personOptions,
              searchQuery: "",
            },
          };
        });
      });
    } catch (error) {
      startTransition(() => {
        setSectionState((currentState) => ({
          ...currentState,
          membership: {
            ...currentState.membership,
            status: "error",
            error:
              error instanceof Error
                ? error.message
                : "The membership editor could not be loaded.",
            saveError: null,
            snapshot: null,
            draft: null,
            searchQuery: "",
          },
        }));
      });
    }
  }

  useEffect(() => {
    if (
      !props.isOpen ||
      sectionState.activeSectionId !== "person_groups" ||
      sectionState.activePersonGroupMembershipRowId === null
    ) {
      return;
    }

    const groupId = toPersistedIdentifier(
      sectionState.activePersonGroupMembershipRowId,
    );
    if (groupId === undefined) {
      return;
    }

    void loadMembershipEditor(groupId);
  }, [
    props.isOpen,
    sectionState.activePersonGroupMembershipRowId,
    sectionState.activeSectionId,
  ]);

  useEffect(() => {
    if (!props.isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (pendingDeletePersonGroupAction !== null) {
          setPendingDeletePersonGroupAction(null);
          return;
        }
        if (isDirty) {
          setPendingGuardAction({ kind: "close" });
          return;
        }

        props.onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDirty, pendingDeletePersonGroupAction, props.isOpen, props.onClose]);

  async function activateSection(sectionId: ManageDataSectionId) {
    setPendingDeletePersonGroupAction(null);

    startTransition(() => {
      setSectionState((currentState) => ({
        activeSectionId: sectionId,
        status: "loading",
        saveState: "idle",
        searchQuery:
          currentState.activeSectionId === sectionId ? currentState.searchQuery : "",
        error: null,
        saveError: null,
        snapshot: null,
        draft: null,
        deletedPersonGroupIds: [],
        activePersonGroupMembershipRowId: null,
        membership: initialSectionState.membership,
      }));
    });

    try {
      const loadedRows = await loadSectionData(sectionId);
      startTransition(() => {
        setSectionState({
          activeSectionId: sectionId,
          status: "ready",
          saveState: "idle",
          searchQuery: "",
          error: null,
          saveError: null,
          snapshot: cloneSectionRows(loadedRows),
          draft: cloneSectionRows(loadedRows),
          deletedPersonGroupIds: [],
          activePersonGroupMembershipRowId: null,
          membership: initialSectionState.membership,
        });
      });
    } catch (error) {
      startTransition(() => {
        setSectionState({
          activeSectionId: sectionId,
          status: "error",
          saveState: "idle",
          searchQuery: "",
          error:
            error instanceof Error
              ? error.message
              : "The section could not be loaded.",
          saveError: null,
          snapshot: null,
          draft: null,
          deletedPersonGroupIds: [],
          activePersonGroupMembershipRowId: null,
          membership: initialSectionState.membership,
        });
      });
    }
  }

  function requestSwitch(nextSectionId: ManageDataSectionId) {
    if (nextSectionId === sectionState.activeSectionId) {
      return;
    }

    if (isDirty) {
      setPendingGuardAction({ kind: "switch", nextSectionId });
      return;
    }

    void activateSection(nextSectionId);
  }

  function requestClose() {
    if (isDirty) {
      setPendingGuardAction({ kind: "close" });
      return;
    }

    props.onClose();
  }

  function discardCurrentDraft() {
    if (sectionState.activePersonGroupMembershipRowId !== null) {
      if (sectionState.membership.snapshot === null) {
        return;
      }

      setSectionState((currentState) => ({
        ...currentState,
        membership: {
          ...currentState.membership,
          draft: JSON.parse(
            JSON.stringify(currentState.membership.snapshot),
          ) as PersonGroupMembershipDraft,
          saveError: null,
          searchQuery: "",
        },
      }));
      return;
    }

    if (sectionState.status !== "ready" || sectionState.snapshot === null) {
      return;
    }

    const snapshotRows = cloneSectionRows(sectionState.snapshot);
    setPendingDeletePersonGroupAction(null);

    setSectionState((currentState) => ({
      ...currentState,
      draft: snapshotRows,
      saveError: null,
      deletedPersonGroupIds: [],
      activePersonGroupMembershipRowId: null,
    }));
  }

  async function saveCurrentDraft(): Promise<boolean> {
    if (sectionState.activePersonGroupMembershipRowId !== null) {
      const groupId = toPersistedIdentifier(
        sectionState.activePersonGroupMembershipRowId,
      );
      if (groupId === undefined || sectionState.membership.draft === null) {
        return false;
      }

      const membershipDraft = JSON.parse(
        JSON.stringify(sectionState.membership.draft),
      ) as PersonGroupMembershipDraft;

      startTransition(() => {
        setSectionState((currentState) => ({
          ...currentState,
          saveState: "saving",
          membership: {
            ...currentState.membership,
            saveError: null,
          },
        }));
      });

      try {
        const [, reloadedGroups, reloadedMembership] = await Promise.all([
          manageDataClient.savePersonGroupMembership(groupId, membershipDraft),
          manageDataClient.loadPersonGroupsCatalog(),
          manageDataClient.loadPersonGroupMembership(groupId),
        ]);

        startTransition(() => {
          setSectionState((currentState) => ({
            ...currentState,
            saveState: "idle",
            snapshot: cloneSectionRows(reloadedGroups),
            draft: cloneSectionRows(reloadedGroups),
            deletedPersonGroupIds: [],
            membership: {
              ...currentState.membership,
              status: "ready",
              error: null,
              saveError: null,
              snapshot: JSON.parse(JSON.stringify(reloadedMembership)),
              draft: JSON.parse(JSON.stringify(reloadedMembership)),
              searchQuery: "",
            },
          }));
        });
        setPendingDeletePersonGroupAction(null);
        return true;
      } catch (error) {
        startTransition(() => {
          setSectionState((currentState) => ({
            ...currentState,
            saveState: "error",
            membership: {
              ...currentState.membership,
              saveError:
                error instanceof Error
                  ? error.message
                  : "Unable to save membership draft.",
            },
          }));
        });
        return false;
      }
    }

    if (sectionState.status !== "ready" || sectionState.draft === null) {
      return false;
    }

    const activeSectionId = sectionState.activeSectionId;
    const draftRows = cloneSectionRows(sectionState.draft);

    startTransition(() => {
      setSectionState((currentState) => ({
        ...currentState,
        saveState: "saving",
        saveError: null,
      }));
    });

    try {
      if (activeSectionId === "persons") {
        await saveSectionData(activeSectionId, draftRows);
      } else {
        await saveSectionData(
          activeSectionId,
          draftRows,
          sectionState.deletedPersonGroupIds,
        );
      }
      const reloadedRows = await loadSectionData(activeSectionId);

      startTransition(() => {
        setSectionState((currentState) => ({
          ...currentState,
          saveState: "idle",
          snapshot: cloneSectionRows(reloadedRows),
          draft: cloneSectionRows(reloadedRows),
          saveError: null,
          deletedPersonGroupIds: [],
          activePersonGroupMembershipRowId: null,
          membership: initialSectionState.membership,
        }));
      });
      setPendingDeletePersonGroupAction(null);
      return true;
    } catch (error) {
      startTransition(() => {
        setSectionState((currentState) => ({
          ...currentState,
          saveState: "error",
          saveError:
            error instanceof Error ? error.message : "Unable to save section draft.",
        }));
      });
      return false;
    }
  }

  async function handleSaveAndClose() {
    const saved = await saveCurrentDraft();

    if (saved) {
      props.onClose();
    }
  }

  async function handleGuardSave() {
    const saved = await saveCurrentDraft();

    if (!saved) {
      return;
    }

    const pendingAction = pendingGuardAction;
    setPendingGuardAction(null);

    if (pendingAction?.kind === "switch") {
      void activateSection(pendingAction.nextSectionId);
      return;
    }

    if (pendingAction?.kind === "membership_back") {
      closePersonGroupMembershipEditor(true);
      return;
    }

    props.onClose();
  }

  function handleGuardDiscard() {
    const pendingAction = pendingGuardAction;
    setPendingGuardAction(null);
    discardCurrentDraft();

    if (pendingAction?.kind === "switch") {
      void activateSection(pendingAction.nextSectionId);
      return;
    }

    if (pendingAction?.kind === "membership_back") {
      closePersonGroupMembershipEditor(true);
      return;
    }

    props.onClose();
  }

  function updateSearchQuery(value: string) {
    setSectionState((currentState) => ({
      ...currentState,
      searchQuery: value,
    }));
  }

  function addDraftRow() {
    if (sectionState.status !== "ready" || sectionState.draft === null) {
      return;
    }

    if (sectionState.activeSectionId === "persons") {
      setSectionState((currentState) => ({
        ...currentState,
        draft: [
          ...(currentState.draft as PersonCatalogDraftRow[]),
          {
            id: createTemporaryId("person"),
            name: "",
            aliases: [],
            path: "",
          },
        ],
      }));
      return;
    }

    setSectionState((currentState) => ({
      ...currentState,
      draft: [
        ...(currentState.draft as PersonGroupCatalogDraftRow[]),
        {
          id: createTemporaryId("group"),
          name: "",
          memberCount: 0,
        },
      ],
    }));
  }

  function updatePersonDraftRow(
    rowId: string,
    field: "name" | "aliases" | "path",
    value: string,
  ) {
    setSectionState((currentState) => {
      if (
        currentState.activeSectionId !== "persons" ||
        currentState.draft === null
      ) {
        return currentState;
      }

      const draftRows = currentState.draft as PersonCatalogDraftRow[];

      return {
        ...currentState,
        draft: draftRows.map((row) =>
          row.id === rowId
            ? {
                ...row,
                [field]:
                  field === "aliases"
                    ? value
                        .split(",")
                        .map((entry) => entry.trim())
                        .filter((entry) => entry !== "")
                    : value,
              }
            : row,
        ),
      };
    });
  }

  function updatePersonGroupDraftRow(
    rowId: string,
    field: "name",
    value: string,
  ) {
    setSectionState((currentState) => {
      if (
        currentState.activeSectionId !== "person_groups" ||
        currentState.draft === null
      ) {
        return currentState;
      }

      const draftRows = currentState.draft as PersonGroupCatalogDraftRow[];

      return {
        ...currentState,
        draft: draftRows.map((row) =>
          row.id === rowId ? { ...row, [field]: value } : row,
        ),
      };
    });
  }

  function requestDeletePersonGroup(rowId: string) {
    if (
      sectionState.activeSectionId !== "person_groups" ||
      sectionState.draft === null
    ) {
      return;
    }

    const row = (sectionState.draft as PersonGroupCatalogDraftRow[]).find(
      (draftRow) => draftRow.id === rowId,
    );
    if (row === undefined) {
      return;
    }

    setPendingDeletePersonGroupAction({
      rowId,
      name: row.name,
    });
  }

  function confirmDeletePersonGroup() {
    const pendingDelete = pendingDeletePersonGroupAction;
    if (pendingDelete === null) {
      return;
    }

    setSectionState((currentState) => {
      if (
        currentState.activeSectionId !== "person_groups" ||
        currentState.draft === null
      ) {
        return currentState;
      }

      const persistedId = toPersistedIdentifier(pendingDelete.rowId);
      return {
        ...currentState,
        draft: (currentState.draft as PersonGroupCatalogDraftRow[]).filter(
          (row) => row.id !== pendingDelete.rowId,
        ),
        deletedPersonGroupIds:
          persistedId === undefined
            ? currentState.deletedPersonGroupIds
            : [...new Set([...currentState.deletedPersonGroupIds, persistedId])],
        activePersonGroupMembershipRowId:
          currentState.activePersonGroupMembershipRowId === pendingDelete.rowId
            ? null
            : currentState.activePersonGroupMembershipRowId,
      };
    });

    setPendingDeletePersonGroupAction(null);
  }

  function openPersonGroupMembershipEditor(rowId: string) {
    if (isDirty) {
      setSectionState((currentState) => ({
        ...currentState,
        saveError: "Apply or discard the person-group catalog draft before editing members.",
      }));
      return;
    }

    setSectionState((currentState) => {
      if (currentState.activeSectionId !== "person_groups") {
        return currentState;
      }

      return {
        ...currentState,
        saveError: null,
        activePersonGroupMembershipRowId: rowId,
      };
    });
  }

  function closePersonGroupMembershipEditor(force = false) {
    if (!force && isDirty) {
      setPendingGuardAction({ kind: "membership_back" });
      return;
    }

    setSectionState((currentState) => ({
      ...currentState,
      activePersonGroupMembershipRowId: null,
      membership: initialSectionState.membership,
    }));
  }

  function updateMembershipSearchQuery(value: string) {
    setSectionState((currentState) => ({
      ...currentState,
      membership: {
        ...currentState.membership,
        searchQuery: value,
      },
    }));
  }

  function addMembershipMember(personId: string) {
    setSectionState((currentState) => {
      if (currentState.membership.draft === null) {
        return currentState;
      }

      const person = currentState.membership.personOptions.find(
        (option) => option.id === personId,
      );
      if (person === undefined) {
        return currentState;
      }

      if (
        currentState.membership.draft.members.some(
          (member) => member.id === person.id,
        )
      ) {
        return {
          ...currentState,
          membership: {
            ...currentState.membership,
            searchQuery: "",
          },
        };
      }

      const nextMember: PersonGroupMembershipDraftMember = {
        id: person.id,
        name: person.name,
        aliases: [...person.aliases],
        path: person.path,
      };

      return {
        ...currentState,
        membership: {
          ...currentState.membership,
          draft: {
            ...currentState.membership.draft,
            members: [...currentState.membership.draft.members, nextMember].sort(
              (left, right) => left.name.localeCompare(right.name),
            ),
          },
          searchQuery: "",
        },
      };
    });
  }

  function removeMembershipMember(personId: string) {
    setSectionState((currentState) => {
      if (currentState.membership.draft === null) {
        return currentState;
      }

      return {
        ...currentState,
        membership: {
          ...currentState.membership,
          draft: {
            ...currentState.membership.draft,
            members: currentState.membership.draft.members.filter(
              (member) => member.id !== personId,
            ),
          },
        },
      };
    });
  }

  if (!props.isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-40 bg-[color:rgba(245,236,223,0.78)] backdrop-blur-sm">
      <div className="absolute inset-3 overflow-hidden rounded-[32px] border border-[color:var(--pp-border)] bg-[linear-gradient(180deg,rgba(255,252,247,0.98),rgba(247,239,228,0.98))] shadow-[0_30px_120px_rgba(61,44,15,0.18)] lg:inset-4">
        <div className="grid h-full min-h-0 grid-cols-1 lg:grid-cols-[18rem_minmax(0,1fr)]">
          <aside className="border-b border-[color:var(--pp-border)] bg-[color:rgba(255,250,244,0.92)] px-5 py-5 lg:border-b-0 lg:border-r lg:px-6">
            <div className="flex items-start justify-between gap-4">
              <div>
                <p className="panel-title">Workspace</p>
                <h1 className="mt-2 text-2xl font-semibold text-slate-950">
                  Manage Data
                </h1>
                <p className="mt-2 text-sm leading-6 text-slate-600">
                  Temporary canonical catalog editing above the exploration view.
                </p>
              </div>
              <button
                type="button"
                onClick={requestClose}
                className="rounded-full border border-[color:var(--pp-border)] bg-white/75 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-white"
              >
                Close
              </button>
            </div>
            <nav aria-label="Manage data sections" className="mt-6 flex flex-col gap-2">
              {MANAGE_SECTIONS.map((section) => (
                <button
                  key={section.id}
                  type="button"
                  onClick={() => requestSwitch(section.id)}
                  aria-current={
                    sectionState.activeSectionId === section.id ? "page" : undefined
                  }
                  className={[
                    "rounded-[22px] border px-4 py-3 text-left transition",
                    sectionState.activeSectionId === section.id
                      ? "border-slate-900 bg-slate-900 text-white shadow-[0_18px_36px_rgba(15,23,42,0.14)]"
                      : "border-[color:var(--pp-border)] bg-white/60 text-slate-700 hover:bg-white",
                  ].join(" ")}
                >
                  <div className="text-sm font-semibold">{section.label}</div>
                  <div
                    className={[
                      "mt-1 text-xs leading-5",
                      sectionState.activeSectionId === section.id
                        ? "text-slate-200"
                        : "text-slate-500",
                    ].join(" ")}
                  >
                    {section.description}
                  </div>
                </button>
              ))}
            </nav>
          </aside>
          <section className="flex min-h-0 flex-col">
            <div className="min-h-0 flex-1 px-4 py-4 lg:px-5 lg:py-5">
              {sectionState.status === "loading" ? (
                <CatalogLoadingState
                  label={`Loading ${sectionState.activeSectionId === "persons" ? "persons" : "person groups"} section`}
                />
              ) : null}
              {sectionState.status === "error" ? (
                <CatalogErrorState
                  title="The section could not be loaded"
                  description={sectionState.error ?? "Manage data section load failed."}
                  onRetry={() => void activateSection(sectionState.activeSectionId)}
                />
              ) : null}
              {sectionState.status === "ready" &&
              sectionState.activeSectionId === "persons" &&
              sectionState.draft !== null ? (
                <PersonsSection
                  rows={sectionState.draft as PersonCatalogDraftRow[]}
                  searchQuery={sectionState.searchQuery}
                  dirty={isDirty}
                  onSearchChange={updateSearchQuery}
                  onAdd={addDraftRow}
                  onChangeRow={updatePersonDraftRow}
                />
              ) : null}
              {sectionState.status === "ready" &&
              sectionState.activeSectionId === "person_groups" &&
              sectionState.activePersonGroupMembershipRowId !== null ? (
                sectionState.membership.status === "loading" ? (
                  <CatalogLoadingState label="Loading person-group membership" />
                ) : sectionState.membership.status === "error" ? (
                  <CatalogErrorState
                    title="The membership editor could not be loaded"
                    description={
                      sectionState.membership.error ??
                      "Person-group membership load failed."
                    }
                    onRetry={() => {
                      const groupId = toPersistedIdentifier(
                        sectionState.activePersonGroupMembershipRowId ?? "",
                      );
                      if (groupId !== undefined) {
                        void loadMembershipEditor(groupId);
                      }
                    }}
                  />
                ) : sectionState.membership.draft !== null ? (
                  <PersonGroupMembershipSection
                    membership={sectionState.membership.draft}
                    searchQuery={sectionState.membership.searchQuery}
                    saveError={sectionState.membership.saveError}
                    personOptions={sectionState.membership.personOptions}
                    dirty={isDirty}
                    onSearchChange={updateMembershipSearchQuery}
                    onAddMember={addMembershipMember}
                    onRemoveMember={removeMembershipMember}
                    onClose={() => closePersonGroupMembershipEditor()}
                  />
                ) : null
              ) : sectionState.draft !== null ? (
                <PersonGroupsSection
                  rows={sectionState.draft as PersonGroupCatalogDraftRow[]}
                  searchQuery={sectionState.searchQuery}
                  dirty={isDirty}
                  onSearchChange={updateSearchQuery}
                  onAdd={addDraftRow}
                  onChangeRow={updatePersonGroupDraftRow}
                  onDeleteRow={requestDeletePersonGroup}
                  onOpenMembershipEditor={openPersonGroupMembershipEditor}
                />
              ) : null}
            </div>
            <footer className="border-t border-[color:var(--pp-border)] bg-[color:rgba(255,250,244,0.94)] px-4 py-4 lg:px-5">
              <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
                <div className="flex flex-wrap items-center gap-3">
                  <span
                    className={[
                      "rounded-full px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.18em]",
                      isDirty ? "bg-amber-100 text-amber-800" : "bg-emerald-100 text-emerald-800",
                    ].join(" ")}
                  >
                    {isDirty ? "Unsaved changes" : "No unsaved changes"}
                  </span>
                  {sectionState.saveState === "saving" ? (
                    <span className="text-sm text-slate-500">Saving section draft...</span>
                  ) : null}
                  {sectionState.saveError ? (
                    <span className="text-sm text-rose-700">{sectionState.saveError}</span>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={requestClose}
                    className="rounded-full border border-[color:var(--pp-border)] bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-white"
                  >
                    Close
                  </button>
                  <button
                    type="button"
                    onClick={discardCurrentDraft}
                    disabled={!isDirty || sectionState.status !== "ready"}
                    className="rounded-full border border-[color:var(--pp-border)] bg-white/80 px-4 py-2 text-sm font-medium text-slate-700 transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-white"
                  >
                    Discard
                  </button>
                  <button
                    type="button"
                    onClick={() => void saveCurrentDraft()}
                    disabled={
                      !isDirty ||
                      sectionState.status !== "ready" ||
                      sectionState.saveState === "saving"
                    }
                    className="rounded-full border border-slate-900 bg-white px-4 py-2 text-sm font-medium text-slate-900 transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-50"
                  >
                    Apply
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleSaveAndClose()}
                    disabled={
                      sectionState.status !== "ready" ||
                      sectionState.saveState === "saving"
                    }
                    className="rounded-full border border-slate-900 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-800"
                  >
                    Save &amp; Close
                  </button>
                </div>
              </div>
            </footer>
          </section>
        </div>
        {pendingGuardAction !== null ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[color:rgba(28,36,48,0.22)] p-4">
            <div className="panel-surface-strong w-full max-w-lg p-6">
              <p className="panel-title text-amber-700">Unsaved draft</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                Decide what to do with the current section
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                This workspace keeps exactly one active draft. Switching sections or
                closing the overlay requires an explicit stay, discard, or save
                decision.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setPendingGuardAction(null)}
                  className="rounded-full border border-[color:var(--pp-border)] bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  Stay here
                </button>
                <button
                  type="button"
                  onClick={handleGuardDiscard}
                  className="rounded-full border border-amber-200 bg-amber-50 px-4 py-2 text-sm font-medium text-amber-800 transition hover:bg-amber-100"
                >
                  Discard changes
                </button>
                <button
                  type="button"
                  onClick={() => void handleGuardSave()}
                  disabled={sectionState.saveState === "saving"}
                  className="rounded-full border border-slate-900 bg-slate-900 px-4 py-2 text-sm font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-50 hover:bg-slate-800"
                >
                  Save changes
                </button>
              </div>
            </div>
          </div>
        ) : null}
        {pendingDeletePersonGroupAction !== null ? (
          <div className="absolute inset-0 flex items-center justify-center bg-[color:rgba(28,36,48,0.22)] p-4">
            <div className="panel-surface-strong w-full max-w-lg p-6">
              <p className="panel-title text-rose-700">Delete group</p>
              <h2 className="mt-2 text-2xl font-semibold text-slate-950">
                Confirm removal from the local draft
              </h2>
              <p className="mt-3 text-sm leading-6 text-slate-600">
                Delete{" "}
                <span className="font-semibold text-slate-900">
                  {pendingDeletePersonGroupAction.name || "this group"}
                </span>{" "}
                from the current draft? The persisted row and its membership links
                will be removed only after you apply or save the section.
              </p>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => setPendingDeletePersonGroupAction(null)}
                  className="rounded-full border border-[color:var(--pp-border)] bg-white px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-50"
                >
                  Keep group
                </button>
                <button
                  type="button"
                  onClick={confirmDeletePersonGroup}
                  className="rounded-full border border-rose-200 bg-rose-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-700"
                >
                  Confirm delete
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
