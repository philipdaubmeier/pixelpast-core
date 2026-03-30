"""Helpers for public canonical asset short ids."""

from __future__ import annotations

import hashlib
import secrets

ASSET_SHORT_ID_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
ASSET_SHORT_ID_LENGTH = 8
_ASSET_SHORT_ID_SPACE_SIZE = len(ASSET_SHORT_ID_ALPHABET) ** ASSET_SHORT_ID_LENGTH


def build_asset_short_id_candidate(*, seed: str, attempt: int = 0) -> str:
    """Derive one deterministic fixed-length Base58 short id candidate."""

    if attempt < 0:
        raise ValueError("attempt must be non-negative")

    payload = f"{seed}:{attempt}".encode("utf-8")
    digest = hashlib.sha256(payload).digest()
    return _encode_base58_fixed(
        int.from_bytes(digest, byteorder="big") % _ASSET_SHORT_ID_SPACE_SIZE
    )


def generate_random_asset_short_id() -> str:
    """Generate one random fixed-length Base58 short id."""

    return _encode_base58_fixed(secrets.randbelow(_ASSET_SHORT_ID_SPACE_SIZE))


def _encode_base58_fixed(value: int) -> str:
    characters: list[str] = []
    base = len(ASSET_SHORT_ID_ALPHABET)
    remaining = value

    for _ in range(ASSET_SHORT_ID_LENGTH):
        remaining, remainder = divmod(remaining, base)
        characters.append(ASSET_SHORT_ID_ALPHABET[remainder])

    characters.reverse()
    return "".join(characters)

