"""Canonical vocabulary for municipalities and crime classifications.

This is the single source of truth shared by the CSV/Excel importer, the
validation layer, and the analytical services. Keeping one module authoritative
is what makes accepting a new PNP export a mapping exercise rather than a code
change.

Two separate concerns live here:

1. **Canonical form** — the exact string the system stores and displays.
2. **Aliases** — inbound spellings the importer accepts and standardizes.

Per the study specification the displayed municipality spelling is
"Pigcawayan". The PSGC-sourced boundary file publishes it as "Pigkawayan", and
PNP records may use either, so "Pigkawayan" is accepted as an alias and
standardized on import. The boundary GeoJSON itself is left untouched so its
provenance stays verifiable and re-downloadable — canonicalization happens on
read, not by editing sourced data.

Any standardization applied to a row must be surfaced in the import report
(never silently applied), per specification section 8.
"""

import re

# --- Municipalities -------------------------------------------------------

CANONICAL_MUNICIPALITIES: list[str] = [
    "Alamada",
    "Aleosan",
    "Libungan",
    "Midsayap",
    "Pigcawayan",
    "Pikit",
]

# Normalized (lowercase, stripped) inbound spelling -> canonical form.
# Includes the PSGC boundary-file spelling and common PNP/manual-entry variants.
MUNICIPALITY_ALIASES: dict[str, str] = {
    "alamada": "Alamada",
    "aleosan": "Aleosan",
    "libungan": "Libungan",
    "midsayap": "Midsayap",
    "pigcawayan": "Pigcawayan",
    "pigkawayan": "Pigcawayan",  # PSGC boundary-file + common alternate spelling
    "pikit": "Pikit",
}

# --- Crime classifications ------------------------------------------------

# The eight index crimes defined for this study (specification section 6).
INDEX_CRIME_TYPES: list[str] = [
    "Murder",
    "Homicide",
    "Physical Injury",
    "Rape",
    "Robbery",
    "Theft",
    "Carnapping",
    "Cattle Rustling",
]

# Crimes against persons vs. crimes against property — used for grouped
# reporting. Kept here so the split is documented rather than re-derived.
CRIMES_AGAINST_PERSONS = {"Murder", "Homicide", "Physical Injury", "Rape"}
CRIMES_AGAINST_PROPERTY = {"Robbery", "Theft", "Carnapping", "Cattle Rustling"}

# Normalized inbound spelling -> canonical form. Covers pluralization,
# hyphenation, and the wording variants that commonly appear in blotter exports.
CRIME_TYPE_ALIASES: dict[str, str] = {
    "murder": "Murder",
    "homicide": "Homicide",
    "physical injury": "Physical Injury",
    "physical injuries": "Physical Injury",
    "serious physical injury": "Physical Injury",
    "serious physical injuries": "Physical Injury",
    "less serious physical injuries": "Physical Injury",
    "slight physical injuries": "Physical Injury",
    "rape": "Rape",
    "robbery": "Robbery",
    "theft": "Theft",
    "qualified theft": "Theft",
    "carnapping": "Carnapping",
    "car napping": "Carnapping",
    "car-napping": "Carnapping",
    "motornapping": "Carnapping",
    "cattle rustling": "Cattle Rustling",
    "cattle-rustling": "Cattle Rustling",
    "cattle russling": "Cattle Rustling",
    "rustling": "Cattle Rustling",
}

# --- Data source values ---------------------------------------------------

ALLOWED_SOURCES: list[str] = [
    "official",
    "geocoded",
    "generalized",
    "manually_verified",
]

# --- Normalizers ----------------------------------------------------------


def _key(value: object) -> str:
    """Collapse an inbound value to its alias-lookup key."""
    return " ".join(str(value).strip().lower().split())


def normalize_municipality(value: object) -> tuple[str | None, bool]:
    """Return (canonical_name, was_standardized).

    `was_standardized` is True when the inbound value differed from the
    canonical form (e.g. "PIGKAWAYAN" -> "Pigcawayan"), so the caller can
    report the change instead of applying it silently. Returns (None, False)
    when the value matches no known municipality.
    """
    if value is None:
        return None, False
    canonical = MUNICIPALITY_ALIASES.get(_key(value))
    if canonical is None:
        return None, False
    return canonical, str(value).strip() != canonical


# PNP blotter exports name an offense by its statute, not by the short study
# label: "THEFT  - RPC Art. 308", "ANTI-RAPE LAW OF 1997 - RA 8353", "NEW
# ANTI-CARNAPPING ACT OF 2016 - MC - RA 10883 (repealed RA 6539)". The citation
# is stripped and the remaining offense phrase matched.
_CITATION = re.compile(
    r"\s*[-–—]\s*(?:RPC|RA|PD|BP|MC|EO|COMMONWEALTH|ART\.?|ARTICLE)\b.*$",
    re.IGNORECASE,
)

# Phrases that disqualify a record before any keyword match. A quasi-offense
# under RPC Art. 365 is a negligence case (a traffic collision), not the
# intentional index crime whose name it contains, and PNP index-crime
# reporting counts it separately. Matching "HOMICIDE" inside "RECKLESS
# IMPRUDENCE RESULTING TO HOMICIDE" would inflate the homicide series.
_NOT_INDEX_CRIMES = (
    "RECKLESS IMPRUDENCE",
    "ACTS OF LASCIVIOUSNESS",
    "ATTEMPTED RAPE BY SEXUAL ASSAULT",
)

# Offense phrase -> canonical index crime. The phrase appearing EARLIEST in the
# offense name wins, because the special complex crimes are named for their
# principal offense first: "Robbery with Homicide" (RPC Art. 294) is a robbery
# and "Rape with Homicide" (Art. 266-B) is a rape. Ranking by list order instead
# would file both under Homicide and understate both series.
_INDEX_CRIME_PHRASES: list[tuple[str, str]] = [
    ("CATTLE RUSTLING", "Cattle Rustling"),
    ("CARNAPPING", "Carnapping"),
    ("MURDER", "Murder"),
    ("HOMICIDE", "Homicide"),
    ("RAPE", "Rape"),
    ("ROBBERY", "Robbery"),
    ("THEFT", "Theft"),
    ("PHYSICAL INJUR", "Physical Injury"),
    ("MALTREATMENT", "Physical Injury"),
]


def normalize_crime_type(value: object) -> tuple[str | None, bool]:
    """Return (canonical_crime_type, was_standardized).

    Returns (None, False) for values outside the eight index crimes — the
    importer rejects those rather than silently bucketing them into an
    "Other" category, which would distort the index-crime analysis.
    """
    if value is None:
        return None, False

    canonical = CRIME_TYPE_ALIASES.get(_key(value))
    if canonical is not None:
        return canonical, str(value).strip() != canonical

    text = " ".join(str(value).strip().upper().split())
    if any(phrase in text for phrase in _NOT_INDEX_CRIMES):
        return None, False

    offense = _CITATION.sub("", text).strip()
    canonical = CRIME_TYPE_ALIASES.get(_key(offense))
    if canonical is not None:
        return canonical, True

    hits = [(offense.index(p), crime) for p, crime in _INDEX_CRIME_PHRASES if p in offense]
    if hits:
        return min(hits)[1], True
    return None, False


def normalize_source(value: object) -> str | None:
    """Return the canonical dataset-source value, or None if unrecognized."""
    if value is None:
        return None
    key = _key(value).replace(" ", "_")
    return key if key in ALLOWED_SOURCES else None
