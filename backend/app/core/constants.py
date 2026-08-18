"""Backwards-compatible aliases for the canonical vocabulary.

The authoritative definitions now live in `app.core.taxonomy`, which also
carries the alias tables and normalizers. This module is kept as a thin
re-export so existing imports keep working; prefer importing from
`app.core.taxonomy` in new code.
"""

from app.core.taxonomy import (
    CANONICAL_MUNICIPALITIES as PPALMA_MUNICIPALITIES,
    INDEX_CRIME_TYPES as CRIME_TYPES,
)

__all__ = ["PPALMA_MUNICIPALITIES", "CRIME_TYPES"]
