from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchored to backend/.env rather than a bare ".env", which pydantic-settings
# resolves against the *current working directory*. With the relative form, a
# script or server started from the repo root silently found no .env at all and
# fell back to the localhost defaults below — pointing the app at a different
# database than the one it uses when started from backend/, with no warning.
ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """Environment-driven configuration.

    Several fields accept more than one environment-variable name. The first
    choice is the name used in the current specification; the later ones are
    the names used by earlier revisions of this project, kept so an existing
    local `.env` keeps working after the rename.
    """

    model_config = SettingsConfigDict(env_file=ENV_FILE, extra="ignore", case_sensitive=False)

    # Database — same field works for local PostgreSQL/PostGIS or a Supabase Postgres URL.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ppalma_crime"

    # --- Auth ---
    jwt_secret_key: str = Field(
        default="dev-only-change-me",
        validation_alias=AliasChoices("JWT_SECRET_KEY", "JWT_SECRET"),
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(
        default=60 * 12,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_EXPIRE_MINUTES"),
    )

    # --- Data source ---
    # Labels imported datasets. The study now runs on the released PNP dataset;
    # the synthetic demonstration data has been removed.
    data_source: str = "official"

    # --- DBSCAN defaults ---
    # Deliberately configurable, not hardcoded: the values that make sense depend
    # on the official dataset's true spatial density, unknown until it is released.
    dbscan_eps_km: float = 1.0
    dbscan_min_samples: int = 4
    default_period_type: str = "yearly"  # yearly | quarterly | monthly

    # --- Cross-period cluster matching ---
    # A chain's persistence_score is periods_present / total_periods_analyzed.
    # At or above `persistence_score_threshold` it is persistent — "active" when
    # present in the latest analyzed period, "historical" when not. Below the
    # threshold it is "intermittent" (2+ periods) or "temporary" (exactly 1).
    persistence_match_distance_km: float = 1.5
    min_spatial_overlap_percent: float = 0.0
    persistence_min_periods: int = 2
    persistence_score_threshold: float = 0.5
    active_latest_period_required: bool = True

    # --- Evaluation weights (specification section 21) ---
    # A weighting scheme for combining two different kinds of measurement.
    # These are NOT a margin of error and must never be described as one.
    weight_algorithmic: float = 0.90
    weight_functional: float = 0.10

    # --- Upload limits ---
    max_upload_size_mb: float = 100.0

    # --- CORS ---
    frontend_origin: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()
