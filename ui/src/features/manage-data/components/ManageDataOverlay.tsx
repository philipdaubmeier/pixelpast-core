import { startTransition, useEffect, useMemo, useState } from "react";
import { manageDataClient } from "../client";
import type {
  ManageDataSectionDescriptor,
  ManageDataSectionId,
  PersonCatalogDraftRow,
  PersonGroupCatalogDraftRow,
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
    description: "Named group catalogs that later sections can extend with membership editing.",
  },
];

type SectionLoadState = "loading" | "ready" | "error";
type SectionSaveState = "idle" | "saving" | "error";

type SectionRuntimeRows = PersonCatalogDraftRow[] | PersonGroupCatalogDraftRow[];

type SectionRuntimeState = {
  activeSectionId: ManageDataSectionId;
  status: SectionLoadState;
  saveState: SectionSaveState;
  searchQuery: string;
  error: string | null;
  saveError: string | null;
  snapshot: SectionRuntimeRows | null;
  draft: SectionRuntimeRows | null;
};

type PendingGuardAction =
  | { kind: "close" }
  | { kind: "switch"; nextSectionId: ManageDataSectionId }
  | null;

const initialSectionState: SectionRuntimeState = {
  activeSectionId: "persons",
  status: "loading",
  saveState: "idle",
  searchQuery: "",
  error: null,
  saveError: null,
  snapshot: null,
  draft: null,
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

async function loadSectionData(
  sectionId: ManageDataSectionId,
): Promise<SectionRuntimeRows> {
  if (sectionId === "persons") {
    return manageDataClient.loadPersonsCatalog();
  }

  return manageDataClient.loadPersonGroupsCatalog();
}

async function saveSectionData(
  sectionId: ManageDataSectionId,
  rows: SectionRuntimeRows,
): Promise<SectionRuntimeRows> {
  if (sectionId === "persons") {
    return manageDataClient.savePersonsCatalog(rows as PersonCatalogDraftRow[]);
  }

  return manageDataClient.savePersonGroupsCatalog(
    rows as PersonGroupCatalogDraftRow[],
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
  onChangeRow: (rowId: string, field: "name" | "path", value: string) => void;
}) {
  const filteredRows = useMemo(() => {
    const normalizedQuery = props.searchQuery.trim().toLowerCase();

    if (normalizedQuery === "") {
      return props.rows;
    }

    return props.rows.filter((row) =>
      [row.name, row.path, String(row.memberCount)].some((value) =>
        value.toLowerCase().includes(normalizedQuery),
      ),
    );
  }, [props.rows, props.searchQuery]);

  return (
    <CatalogSectionFrame
      eyebrow="Manage Data"
      title="Person Groups"
      description="The group catalog uses the same overlay shell and section draft lifecycle, ready for later membership-specific editing."
      searchValue={props.searchQuery}
      searchPlaceholder="Search group name or path"
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
      <CatalogTable columns={["Group Name", "Path", "Members", "Notes"]}>
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
              <InlineTextField
                value={row.path}
                placeholder="groups/path"
                onChange={(value) => props.onChangeRow(row.id, "path", value)}
              />
              <ReadonlyCell>{row.memberCount} persisted members</ReadonlyCell>
              <ReadonlyCell>Membership editing lands in a later subtask.</ReadonlyCell>
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

  const isDirty =
    sectionState.status === "ready" &&
    getDraftFingerprint(sectionState.snapshot) !==
      getDraftFingerprint(sectionState.draft);

  useEffect(() => {
    if (!props.isOpen) {
      return;
    }

    void activateSection("persons");
  }, [props.isOpen]);

  useEffect(() => {
    if (!props.isOpen) {
      return;
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (isDirty) {
          setPendingGuardAction({ kind: "close" });
          return;
        }

        props.onClose();
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isDirty, props.isOpen, props.onClose]);

  async function activateSection(sectionId: ManageDataSectionId) {
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
    if (sectionState.status !== "ready" || sectionState.snapshot === null) {
      return;
    }

    const snapshotRows = cloneSectionRows(sectionState.snapshot);

    setSectionState((currentState) => ({
      ...currentState,
      draft: snapshotRows,
      saveError: null,
    }));
  }

  async function saveCurrentDraft(): Promise<boolean> {
    if (sectionState.status !== "ready" || sectionState.draft === null) {
      return false;
    }

    startTransition(() => {
      setSectionState((currentState) => ({
        ...currentState,
        saveState: "saving",
        saveError: null,
      }));
    });

    try {
      const persistedDraft = await saveSectionData(
        sectionState.activeSectionId,
        sectionState.draft,
      );

      startTransition(() => {
        setSectionState((currentState) => ({
          ...currentState,
          saveState: "idle",
          snapshot: cloneSectionRows(persistedDraft),
          draft: cloneSectionRows(persistedDraft),
          saveError: null,
        }));
      });
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
          path: "",
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
    field: "name" | "path",
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
              sectionState.draft !== null ? (
                <PersonGroupsSection
                  rows={sectionState.draft as PersonGroupCatalogDraftRow[]}
                  searchQuery={sectionState.searchQuery}
                  dirty={isDirty}
                  onSearchChange={updateSearchQuery}
                  onAdd={addDraftRow}
                  onChangeRow={updatePersonGroupDraftRow}
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
      </div>
    </div>
  );
}
