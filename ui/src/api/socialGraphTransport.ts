export type ApiSocialGraphResponse = {
  persons: Array<{
    id: number;
    name: string;
    occurrence_count: number;
  }>;
  links: Array<{
    person_ids: [number, number];
    weight: number;
  }>;
};

export type ApiSocialGraphRequest = {
  start?: string;
  end?: string;
  personIds: string[];
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

function buildQueryString(
  params: Record<string, string | Array<string> | undefined>,
): string {
  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(params)) {
    if (value === undefined) {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        searchParams.append(key, item);
      }

      continue;
    }

    searchParams.set(key, value);
  }

  const serialized = searchParams.toString();
  return serialized === "" ? "" : `?${serialized}`;
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(buildApiUrl(path));

  if (!response.ok) {
    throw new Error(
      `Social graph API request failed with status ${response.status}`,
    );
  }

  return (await response.json()) as T;
}

export const socialGraphTransport = {
  getSocialGraph(
    request: ApiSocialGraphRequest,
  ): Promise<ApiSocialGraphResponse> {
    return requestJson<ApiSocialGraphResponse>(
      `/social/graph${buildQueryString({
        start: request.start,
        end: request.end,
        person_ids: request.personIds,
      })}`,
    );
  },
};
