"""Thin Google Places client boundary for derived place snapshot resolution."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from urllib import error, parse, request


@dataclass(slots=True, frozen=True)
class GooglePlaceSnapshot:
    """Selected place fields persisted by the derive pipeline."""

    external_id: str
    display_name: str | None
    formatted_address: str | None
    latitude: float | None
    longitude: float | None


@dataclass(slots=True, frozen=True)
class GooglePlacesRequest:
    """One provider request issued by the Google Places client."""

    url: str
    headers: dict[str, str]


@dataclass(slots=True, frozen=True)
class GooglePlacesResponse:
    """Minimal HTTP response contract used by the Google Places client."""

    status_code: int
    body: str


class GooglePlacesClientError(RuntimeError):
    """Base error raised by the Google Places provider boundary."""


class GooglePlacesClientHttpError(GooglePlacesClientError):
    """Raised when Google Places returns a non-success HTTP response."""

    def __init__(self, *, status_code: int, body: str) -> None:
        message_suffix = _format_http_error_body(body)
        super().__init__(
            f"Google Places request failed with HTTP {status_code}.{message_suffix}"
        )
        self.status_code = status_code
        self.body = body


class GooglePlacesClientResponseError(GooglePlacesClientError):
    """Raised when a Google Places response cannot be mapped safely."""


class GooglePlacesClient:
    """Resolve one Google place id into the minimal derived snapshot shape."""

    _FIELD_MASK = "id,displayName,formattedAddress,location"

    def __init__(
        self,
        *,
        api_key: str,
        language_code: str | None = None,
        region_code: str | None = None,
        timeout_seconds: float = 30.0,
        transport: Callable[[GooglePlacesRequest], GooglePlacesResponse] | None = None,
    ) -> None:
        normalized_api_key = api_key.strip()
        if not normalized_api_key:
            raise ValueError("Google Places API key must not be empty.")

        self._api_key = normalized_api_key
        self._language_code = _normalize_optional_code(language_code)
        self._region_code = _normalize_optional_code(region_code)
        self._timeout_seconds = timeout_seconds
        self._transport = transport or self._send_request

    def fetch_place(self, *, place_id: str) -> GooglePlaceSnapshot:
        """Fetch one Google place and map it onto the derived snapshot fields."""

        external_id = _normalize_place_id(place_id)
        resource_name = (
            external_id
            if external_id.startswith("places/")
            else f"places/{external_id}"
        )
        query_params: dict[str, str] = {}
        if self._language_code is not None:
            query_params["languageCode"] = self._language_code
        if self._region_code is not None:
            query_params["regionCode"] = self._region_code

        url = f"https://places.googleapis.com/v1/{resource_name}"
        if query_params:
            url = f"{url}?{parse.urlencode(query_params)}"

        response = self._transport(
            GooglePlacesRequest(
                url=url,
                headers={
                    "Accept": "application/json",
                    "X-Goog-Api-Key": self._api_key,
                    "X-Goog-FieldMask": self._FIELD_MASK,
                },
            )
        )
        if response.status_code != 200:
            raise GooglePlacesClientHttpError(
                status_code=response.status_code,
                body=response.body,
            )

        try:
            payload = json.loads(response.body)
        except json.JSONDecodeError as error:
            raise GooglePlacesClientResponseError(
                "Google Places response is not valid JSON."
            ) from error
        if not isinstance(payload, dict):
            raise GooglePlacesClientResponseError(
                "Google Places response must be a JSON object."
            )

        location = payload.get("location")
        latitude, longitude = _parse_location(location)
        display_name = _parse_display_name(payload.get("displayName"))
        formatted_address = _parse_optional_string(payload.get("formattedAddress"))
        return GooglePlaceSnapshot(
            external_id=external_id,
            display_name=display_name,
            formatted_address=formatted_address,
            latitude=latitude,
            longitude=longitude,
        )

    def _send_request(self, request_data: GooglePlacesRequest) -> GooglePlacesResponse:
        http_request = request.Request(
            request_data.url,
            headers=request_data.headers,
            method="GET",
        )
        try:
            with request.urlopen(
                http_request,
                timeout=self._timeout_seconds,
            ) as response:
                status_code = getattr(response, "status", response.getcode())
                body = response.read().decode("utf-8")
                return GooglePlacesResponse(status_code=status_code, body=body)
        except error.HTTPError as http_error:
            body = http_error.read().decode("utf-8", errors="replace")
            return GooglePlacesResponse(status_code=http_error.code, body=body)
        except error.URLError as network_error:
            raise GooglePlacesClientError(
                f"Google Places request failed: {network_error.reason}"
            ) from network_error


def _normalize_optional_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_place_id(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError("Google place id must not be empty.")
    return normalized


def _parse_display_name(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise GooglePlacesClientResponseError(
            "Google Places displayName must be an object when present."
        )
    return _parse_optional_string(value.get("text"))


def _parse_optional_string(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise GooglePlacesClientResponseError(
            "Google Places response field must be a string when present."
        )
    normalized = value.strip()
    return normalized or None


def _parse_location(value: object) -> tuple[float | None, float | None]:
    if value is None:
        return (None, None)
    if not isinstance(value, dict):
        raise GooglePlacesClientResponseError(
            "Google Places location must be an object when present."
        )
    return (
        _parse_optional_number(value.get("latitude")),
        _parse_optional_number(value.get("longitude")),
    )


def _parse_optional_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise GooglePlacesClientResponseError(
            "Google Places numeric field must contain a number when present."
        )
    return float(value)


def _format_http_error_body(body: str) -> str:
    normalized_body = body.strip()
    if not normalized_body:
        return ""

    try:
        payload = json.loads(normalized_body)
    except json.JSONDecodeError:
        return f" Response body: {_truncate_error_text(normalized_body)}"

    if isinstance(payload, dict):
        error_payload = payload.get("error")
        if isinstance(error_payload, dict):
            message = error_payload.get("message")
            if isinstance(message, str) and message.strip():
                return f" Response body: {_truncate_error_text(message.strip())}"

    return f" Response body: {_truncate_error_text(normalized_body)}"


def _truncate_error_text(value: str, *, max_length: int = 300) -> str:
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3]}..."
