"""Municipality-qualified barangay centroid lookups for map focus and demo data."""

import json
import math
import re
from functools import lru_cache
from pathlib import Path

from app.core.taxonomy import normalize_municipality


CENTROIDS_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "boundaries"
    / "ppalma_barangay_centroids.json"
)


# Generic prefixes that carry no identity — "Brgy. Balabak" is Balabak. They
# are stripped as whole tokens only, never as substrings, so a real barangay
# name that happens to contain one of these letter runs is left intact.
_GENERIC_TOKENS = {"barangay", "brgy", "bgy", "brg", "bry", "bo", "sitio", "purok"}


# PSGC spells some barangays with Roman numerals ("Poblacion I", "Midpapan II")
# while blotter entries commonly use Arabic ("Poblacion 1"). Both forms collapse
# to the same key so either spelling resolves.
_NUMERALS = {"i": "1", "ii": "2", "iii": "3", "iv": "4", "v": "5",
             "vi": "6", "vii": "7", "viii": "8", "ix": "9", "x": "10"}


def _tokens(value: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", value.casefold()) if t]


def _barangay_key(value: str) -> str:
    return "".join(
        _NUMERALS.get(t, t) for t in _tokens(value) if t not in _GENERIC_TOKENS
    )


@lru_cache(maxsize=1)
def _centroids() -> dict[str, dict[str, dict[str, float | str]]]:
    with CENTROIDS_PATH.open(encoding="utf-8") as source:
        payload = json.load(source)
    return payload["municipalities"]


@lru_cache(maxsize=32)
def _official_names(municipality: str) -> dict[str, str]:
    """Normalized key -> official PSGC barangay name, for one municipality.

    Cached because a bulk import resolves one barangay per row: rebuilding this
    index per call turned a large PNP export into millions of redundant key
    computations. There are only six municipalities, so the cache is trivial.
    """
    canonical, _ = normalize_municipality(municipality)
    rows = _centroids().get(canonical or municipality, {})
    return {_barangay_key(name): name for name in rows}


def canonical_barangay(municipality: str, barangay: str) -> str | None:
    """Resolve an inbound barangay spelling to its official PSGC name.

    Handles the spellings blotter exports actually contain — "BRGY. BALABAK",
    "Brgy Balabak", "balabak" — and, when the cell carries extra locality
    detail ("Sitio Maligaya, Balabak"), falls back to the longest run of
    whole tokens that names a real barangay in this municipality. Returns None
    when nothing matches, so the caller can decide rather than guess.
    """
    official = _official_names(municipality)
    if not official:
        return None

    direct = official.get(_barangay_key(barangay))
    if direct:
        return direct

    tokens = [t for t in _tokens(barangay) if t not in _GENERIC_TOKENS]
    for size in range(len(tokens), 0, -1):
        for start in range(len(tokens) - size + 1):
            match = official.get("".join(tokens[start : start + size]))
            if match:
                return match
    return None


def barangay_centroid(municipality: str, barangay: str) -> tuple[float, float] | None:
    """Return ``(latitude, longitude)`` for one barangay within one municipality."""
    canonical, _ = normalize_municipality(municipality)
    rows = _centroids().get(canonical or municipality, {})
    name = canonical_barangay(municipality, barangay)
    if name is None:
        return None
    coordinate = rows[name]
    return float(coordinate["latitude"]), float(coordinate["longitude"])


def nearest_barangay(municipality: str, latitude: float, longitude: float) -> str | None:
    """Return the nearest same-municipality barangay centroid to a coordinate."""
    canonical, _ = normalize_municipality(municipality)
    rows = _centroids().get(canonical or municipality, {})
    if not rows:
        return None

    longitude_scale = math.cos(math.radians(latitude))
    return min(
        rows,
        key=lambda name: (
            (latitude - float(rows[name]["latitude"])) ** 2
            + ((longitude - float(rows[name]["longitude"])) * longitude_scale) ** 2
        ),
    )
