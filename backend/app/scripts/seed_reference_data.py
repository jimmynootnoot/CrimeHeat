"""Seed reference tables: roles, barangays, configurable settings, and the
demonstration reference hotspots.

Run with: python -m app.scripts.seed_reference_data

Idempotent — safe to re-run. Existing rows are updated in place rather than
duplicated, and a setting whose value an administrator has already changed is
left alone (only its label/description/default are refreshed).
"""
import json
from pathlib import Path

from geoalchemy2.shape import from_shape
from shapely.geometry import shape

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.barangay import Barangay
from app.models.municipality import Municipality
from app.models.reference_hotspot import ReferenceHotspot
from app.models.role import Role
from app.models.system import SystemSetting
from app.core.taxonomy import normalize_municipality

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
BARANGAYS_PATH = DATA_DIR / "boundaries" / "ppalma_barangays.json"
HOTSPOTS_PATH = DATA_DIR / "synthetic" / "synthetic_reference_hotspots.geojson"

ROLES = [
    (
        "admin",
        "Full access: user management, dataset management, analytical parameters, "
        "analysis runs, system logs, reports, and evaluation.",
    ),
    (
        "analyst",
        "Upload and validate datasets, run DBSCAN and persistence analysis, apply "
        "filters, view results, and export reports. Cannot manage users or delete data.",
    ),
    (
        "viewer",
        "Read-only: view approved maps, summaries, cluster details, and generated "
        "reports. Cannot upload, modify, or delete anything.",
    ),
]


def _setting_definitions() -> list[dict]:
    s = get_settings()
    return [
        # --- DBSCAN ---
        dict(
            key="dbscan_eps_km",
            value=str(s.dbscan_eps_km),
            value_type="float",
            category="dbscan",
            label="Epsilon (eps) in kilometres",
            description=(
                "DBSCAN neighbourhood radius. Two incidents within this great-circle "
                "distance are density-reachable. Expressed in km because the analysis "
                "uses the haversine metric, not raw coordinate degrees."
            ),
        ),
        dict(
            key="dbscan_min_samples",
            value=str(s.dbscan_min_samples),
            value_type="int",
            category="dbscan",
            label="Minimum samples",
            description=(
                "Minimum number of incidents within eps (including the point itself) "
                "for a point to be a core point. Points that are neither core nor "
                "within eps of a core point are labeled noise."
            ),
        ),
        dict(
            key="default_period_type",
            value="yearly",
            value_type="string",
            category="dbscan",
            label="Default temporal interval",
            description="Period granularity for analysis: yearly, quarterly, or monthly.",
        ),
        # --- Persistence matching ---
        dict(
            key="persistence_match_distance_km",
            value=str(s.persistence_match_distance_km),
            value_type="float",
            category="persistence",
            label="Cluster-matching distance (km)",
            description=(
                "Maximum centroid separation for two period-specific clusters to be "
                "treated as the same recurring hotspot chain."
            ),
        ),
        dict(
            key="min_spatial_overlap_percent",
            value=str(s.min_spatial_overlap_percent),
            value_type="float",
            category="persistence",
            label="Minimum spatial overlap (%)",
            description=(
                "Minimum overlap between two clusters' approximate extents for a match. "
                "Set to 0 to match on centroid distance alone."
            ),
        ),
        dict(
            key="persistence_min_periods",
            value=str(s.persistence_min_periods),
            value_type="int",
            category="persistence",
            label="Minimum periods for persistence",
            description=(
                "Fewest periods a chain must appear in before it can be classified as "
                "persistent rather than temporary or intermittent."
            ),
        ),
        dict(
            key="persistence_score_threshold",
            value=str(s.persistence_score_threshold),
            value_type="float",
            category="persistence",
            label="Persistence score threshold",
            description=(
                "persistence_score = periods present / total periods analyzed. At or "
                "above this value a chain is persistent. Study-defined and configurable, "
                "not a universal scientific standard."
            ),
        ),
        dict(
            key="active_latest_period_required",
            value="true",
            value_type="bool",
            category="persistence",
            label="Require latest period for 'active'",
            description=(
                "When enabled, a persistent chain absent from the most recent analyzed "
                "period is classified historical persistent rather than active persistent."
            ),
        ),
        # --- Evaluation weights ---
        dict(
            key="weight_algorithmic",
            value="0.90",
            value_type="float",
            category="evaluation",
            label="Algorithmic performance weight",
            description=(
                "Weight applied to the algorithmic score in the overall effectiveness "
                "calculation. This is a weighting scheme, NOT a margin of error."
            ),
        ),
        dict(
            key="weight_functional",
            value="0.10",
            value_type="float",
            category="evaluation",
            label="Functional testing weight",
            description="Weight applied to the functional testing pass rate.",
        ),
        dict(
            key="evaluation_grid_cell_km",
            value="1.0",
            value_type="float",
            category="evaluation",
            label="Evaluation grid cell size (km)",
            description=(
                "Edge length of the square cells the study area is divided into when "
                "comparing detected clusters against reference hotspot labels."
            ),
        ),
        # --- Map / upload / report ---
        dict(
            key="map_default_view",
            value="persistence",
            value_type="string",
            category="map",
            label="Default map view",
            description="Which map view opens first: incident, cluster, or persistence.",
        ),
        dict(
            key="max_upload_size_mb",
            value=str(s.max_upload_size_mb),
            value_type="float",
            category="upload",
            label="Maximum upload size (MB)",
            description="Files larger than this are rejected before parsing.",
        ),
        dict(
            key="organization_name",
            value="PPALMA Crime Pattern Analysis Study",
            value_type="string",
            category="report",
            label="Organization name",
            description="Shown in generated report headers.",
        ),
        dict(
            key="report_header",
            value="PPALMA Persistent Crime Pattern Analysis Tool",
            value_type="string",
            category="report",
            label="Report header",
            description="Title line printed at the top of generated reports.",
        ),
    ]


def run() -> None:
    db = SessionLocal()
    try:
        # --- Roles ---
        for name, description in ROLES:
            role = db.query(Role).filter(Role.name == name).first()
            if role:
                role.description = description
            else:
                db.add(Role(name=name, description=description))
        db.commit()
        print(f"Seeded {len(ROLES)} roles.")

        # --- Settings ---
        created = updated = 0
        for definition in _setting_definitions():
            existing = db.query(SystemSetting).filter(SystemSetting.key == definition["key"]).first()
            if existing:
                # Preserve an administrator's chosen value; refresh metadata only.
                existing.label = definition["label"]
                existing.description = definition["description"]
                existing.category = definition["category"]
                existing.value_type = definition["value_type"]
                existing.default_value = definition["value"]
                updated += 1
            else:
                db.add(SystemSetting(**definition, default_value=definition["value"]))
                created += 1
        db.commit()
        print(f"Settings: {created} created, {updated} refreshed.")

        # --- Barangays ---
        municipalities = {m.name: m.id for m in db.query(Municipality).all()}
        if not municipalities:
            print("  (skipping barangays — run seed_municipalities first)")
        else:
            with open(BARANGAYS_PATH, encoding="utf-8-sig") as f:
                raw = json.load(f)
            db.query(Barangay).delete()
            total = 0
            for key, names in raw.items():
                muni_name, _ = normalize_municipality(key)
                muni_id = municipalities.get(muni_name)
                if muni_id is None:
                    continue
                for name in sorted(set(names)):
                    db.add(Barangay(municipality_id=muni_id, municipality=muni_name, name=name))
                    total += 1
            db.commit()
            print(f"Seeded {total} barangays.")

        # --- Demonstration reference hotspots ---
        if not HOTSPOTS_PATH.exists():
            print("  (skipping reference hotspots — run app.services.synthetic_data first)")
        else:
            with open(HOTSPOTS_PATH, encoding="utf-8") as f:
                collection = json.load(f)
            db.query(ReferenceHotspot).filter(
                ReferenceHotspot.label_source == "synthetic_demo"
            ).delete()
            for feature in collection.get("features", []):
                props = feature.get("properties", {})
                geom = shape(feature["geometry"])
                db.add(
                    ReferenceHotspot(
                        name=props.get("name", "Unnamed reference site"),
                        municipality=props.get("municipality", ""),
                        label_source="synthetic_demo",
                        notes=props.get("notes"),
                        geom=from_shape(geom, srid=4326),
                    )
                )
            db.commit()
            count = db.query(ReferenceHotspot).count()
            print(f"Seeded {count} demonstration reference hotspots.")
            print(
                "  NOTE: these are demo-only ground truth. Any F1-score derived from them "
                "is a demonstration of the evaluation pipeline, not PNP validation."
            )
    finally:
        db.close()


if __name__ == "__main__":
    run()
