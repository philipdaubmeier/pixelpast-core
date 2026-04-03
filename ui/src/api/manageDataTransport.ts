export type ApiPersonsCatalogResponse = {
  persons: Array<{
    id: number;
    name: string;
    aliases: string[];
    path: string | null;
  }>;
};

export type ApiSavePersonsCatalogRequest = {
  persons: Array<{
    id?: number;
    name: string;
    aliases: string[];
    path?: string | null;
  }>;
  delete_ids: number[];
};

export type ApiPersonGroupsCatalogResponse = {
  person_groups: Array<{
    id: number;
    name: string;
    member_count: number;
  }>;
};

export type ApiSavePersonGroupsCatalogRequest = {
  person_groups: Array<{
    id?: number;
    name: string;
  }>;
  delete_ids: number[];
};

export type ApiPersonGroupMembershipResponse = {
  person_group: {
    id: number;
    name: string;
    member_count: number;
    album_aggregate_rules: {
      ignored_person_ids: number[];
    };
  };
  members: Array<{
    id: number;
    name: string;
    aliases: string[];
    path: string | null;
  }>;
};

export type ApiSavePersonGroupMembershipRequest = {
  person_ids: number[];
  album_aggregate_rules: {
    ignored_person_ids: number[];
  };
};

function normalizeConfiguredApiBaseUrl(value: string): string {
  const trimmedValue = value.replace(/\/$/, "");

  if (trimmedValue === "") {
    return "";
  }

  return trimmedValue.endsWith("/api") ? trimmedValue : `${trimmedValue}/api`;
}

const apiBaseUrl = normalizeConfiguredApiBaseUrl(
  import.meta.env.VITE_PIXELPAST_API_BASE_URL ?? "",
);

function buildApiUrl(path: string): string {
  if (apiBaseUrl !== "") {
    return `${apiBaseUrl}${path}`;
  }

  return `/api${path}`;
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload = (await response.json()) as { detail?: unknown };
    if (typeof payload.detail === "string" && payload.detail.trim() !== "") {
      return payload.detail;
    }
  } catch {
    return `Manage data API request failed with status ${response.status}`;
  }

  return `Manage data API request failed with status ${response.status}`;
}

async function requestJson<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(buildApiUrl(path), {
    ...init,
    headers,
  });

  if (!response.ok) {
    throw new Error(await readErrorMessage(response));
  }

  return (await response.json()) as T;
}

export const manageDataTransport = {
  getPersonsCatalog(): Promise<ApiPersonsCatalogResponse> {
    return requestJson<ApiPersonsCatalogResponse>("/manage-data/persons");
  },

  savePersonsCatalog(
    request: ApiSavePersonsCatalogRequest,
  ): Promise<ApiPersonsCatalogResponse> {
    return requestJson<ApiPersonsCatalogResponse>("/manage-data/persons", {
      method: "PUT",
      body: JSON.stringify(request),
    });
  },

  getPersonGroupsCatalog(): Promise<ApiPersonGroupsCatalogResponse> {
    return requestJson<ApiPersonGroupsCatalogResponse>(
      "/manage-data/person-groups",
    );
  },

  savePersonGroupsCatalog(
    request: ApiSavePersonGroupsCatalogRequest,
  ): Promise<ApiPersonGroupsCatalogResponse> {
    return requestJson<ApiPersonGroupsCatalogResponse>(
      "/manage-data/person-groups",
      {
        method: "PUT",
        body: JSON.stringify(request),
      },
    );
  },

  getPersonGroupMembership(
    groupId: number,
  ): Promise<ApiPersonGroupMembershipResponse> {
    return requestJson<ApiPersonGroupMembershipResponse>(
      `/manage-data/person-groups/${groupId}/members`,
    );
  },

  savePersonGroupMembership(
    groupId: number,
    request: ApiSavePersonGroupMembershipRequest,
  ): Promise<ApiPersonGroupMembershipResponse> {
    return requestJson<ApiPersonGroupMembershipResponse>(
      `/manage-data/person-groups/${groupId}/members`,
      {
        method: "PUT",
        body: JSON.stringify(request),
      },
    );
  },
};
