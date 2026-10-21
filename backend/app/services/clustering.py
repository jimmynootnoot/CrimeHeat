"""DBSCAN spatial clustering over incident points.

Uses scikit-learn's DBSCAN with the haversine metric so eps is expressed in real
km rather than degrees. eps/min_samples are passed in (ultimately sourced from
app.core.config defaults, overridable per-request) rather than hardcoded, since
the values that make sense will only be known once the official PNP dataset and
its true spatial density are available.

Each cluster's *extent* is rendered as a real GeoJSON polygon (the convex hull
of its member points via Shapely), not a decorative fixed-radius circle. When a
cluster's points are collinear or coincident the hull degenerates to a
Point/LineString; in that case it's buffered by a small, fixed real-world
distance (~100m) purely so it remains visible as a polygon — this still
represents the true extent (all points at ~one location), it is not an
arbitrary decoration.

DBSCAN's three-way point classification is preserved and reported, not
collapsed into "clustered vs not":

- **core**   — has at least `min_samples` neighbours within `eps`.
- **border** — inside a cluster, but with fewer than `min_samples` neighbours;
  it joined via a core point rather than by being dense itself.
- **noise**  — satisfies neither condition and belongs to no cluster.

This module intentionally makes no predictive claims — a cluster here means
"a spatial concentration of historical, already-reported incidents," not a
forecast of where future crime will occur.
"""
from collections import Counter
from typing import Optional

import numpy as np
from shapely.geometry import MultiPoint, mapping as shapely_mapping
from sklearn.cluster import DBSCAN
from sqlalchemy.orm import Session

from app.models.cluster import Cluster, DBSCANRun
from app.models.incident import Incident

EARTH_RADIUS_KM = 6371.0088
DEGENERATE_HULL_BUFFER_DEG = 0.001  # ~100m at this latitude


# Thresholds for the density-based-clustering caveats the literature calls for:
# density-based results depend on eps/min_samples, so a run that is almost all
# noise, or that collapses into one giant cluster, is reported as a parameter
# warning rather than presented as a clean finding.
EXCESSIVE_NOISE_RATIO = 0.60
DOMINANT_CLUSTER_SHARE = 0.80


def _parameter_warnings(
    noise_ratio: Optional[float], largest_cluster_share: Optional[float], cluster_count: int
) -> list[str]:
    """Caveats about the current eps/min_samples, shown alongside the results."""
    warnings: list[str] = []
    if noise_ratio is not None and noise_ratio >= EXCESSIVE_NOISE_RATIO:
        warnings.append(
            f"{noise_ratio * 100:.0f}% of analyzed incidents were classified as noise. "
            "Epsilon may be too small or min-samples too high for this data's density."
        )
    if cluster_count == 1 and largest_cluster_share is not None and largest_cluster_share >= DOMINANT_CLUSTER_SHARE:
        warnings.append(
            "Nearly all clustered incidents fell into a single cluster. "
            "Epsilon may be too large to separate distinct concentrations."
        )
    if cluster_count == 0:
        warnings.append(
            "No clusters met the density condition under the current parameters."
        )
    return warnings


def _hull_geometry(members: list[Incident]) -> dict:
    points = MultiPoint([(m.longitude, m.latitude) for m in members])
    hull = points.convex_hull
    if hull.geom_type in ("Point", "LineString"):
        hull = hull.buffer(DEGENERATE_HULL_BUFFER_DEG)
    return shapely_mapping(hull)


def run_dbscan(
    db: Session,
    year: Optional[int] = None,
    crime_type: Optional[str] = None,
    municipality: Optional[str] = None,
    eps_km: float = 1.0,
    min_samples: int = 4,
    barangay: Optional[str] = None,
) -> dict:
    query = db.query(Incident)
    if municipality:
        query = query.filter(Incident.municipality == municipality)
    if barangay:
        query = query.filter(Incident.barangay == barangay)
    if crime_type:
        query = query.filter(Incident.crime_type == crime_type)
    if year:
        from sqlalchemy import extract

        query = query.filter(extract("year", Incident.incident_date) == year)

    incidents = query.all()

    run = DBSCANRun(
        year=year,
        crime_type=crime_type,
        municipality=municipality,
        eps_km=eps_km,
        min_samples=min_samples,
    )
    db.add(run)
    db.flush()

    features = []
    pending: list[tuple] = []
    total_core = 0
    total_border = 0
    total_noise = 0
    largest_cluster = 0

    if incidents:
        coords_rad = np.radians([[i.latitude, i.longitude] for i in incidents])
        eps_rad = eps_km / EARTH_RADIUS_KM
        # .fit() rather than .fit_predict() so core_sample_indices_ is available:
        # DBSCAN's three-way point classification (core / border / noise) is part
        # of what the study reports, and border points are only distinguishable
        # from core points via that attribute.
        model = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine").fit(coords_rad)
        labels = model.labels_
        core_indices = set(int(i) for i in model.core_sample_indices_)

        cluster_ids = sorted(set(labels) - {-1})
        for label in cluster_ids:
            members = [inc for inc, lbl in zip(incidents, labels) if lbl == label]
            member_core = sum(
                1 for idx, lbl in enumerate(labels) if lbl == label and idx in core_indices
            )
            member_border = len(members) - member_core
            centroid_lat = sum(m.latitude for m in members) / len(members)
            centroid_lon = sum(m.longitude for m in members) / len(members)
            dominant_crime_type = Counter(m.crime_type for m in members).most_common(1)[0][0]
            barangays = sorted({m.barangay for m in members})

            cluster_row = Cluster(
                run_id=run.id,
                cluster_label=int(label),
                year=year,
                crime_type=crime_type,
                municipality=municipality or members[0].municipality,
                point_count=len(members),
                centroid_lat=centroid_lat,
                centroid_lon=centroid_lon,
                hull_geojson=_hull_geometry(members),
            )
            db.add(cluster_row)
            pending.append(
                (
                    cluster_row,
                    len(members),
                    member_core,
                    member_border,
                    dominant_crime_type,
                    barangays,
                    centroid_lat,
                    centroid_lon,
                )
            )

        # One flush for every cluster row in this run, instead of one flush
        # (one DB round trip) per cluster — with a remote DB the per-cluster
        # version could add 15-30+ round trips to a single request.
        db.flush()
        cluster_rows_by_label = {row.cluster_label: row for row, *_ in pending}

        for (
            cluster_row,
            point_count,
            member_core,
            member_border,
            dominant_crime_type,
            barangays,
            centroid_lat,
            centroid_lon,
        ) in pending:
            features.append(
                {
                    "type": "Feature",
                    "geometry": cluster_row.hull_geojson,
                    "properties": {
                        "cluster_id": cluster_row.id,
                        "run_id": run.id,
                        "year": year,
                        "crime_type": crime_type,
                        "point_count": point_count,
                        # A cluster's extent polygon. Its member points are
                        # broken down into DBSCAN core vs border below.
                        "status": "core",
                        "feature_kind": "extent",
                        "core_point_count": member_core,
                        "border_point_count": member_border,
                        "centroid": [centroid_lon, centroid_lat],
                        "municipality": cluster_row.municipality,
                        "dominant_crime_type": dominant_crime_type,
                        "barangays": barangays,
                    },
                }
            )
            total_core += member_core
            total_border += member_border

        # Emit every clustered member, linked to its extent. Geometry kind
        # distinguishes core points from the legacy status='core' polygons.
        for idx, (member, label) in enumerate(zip(incidents, labels)):
            if label == -1:
                continue
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [member.longitude, member.latitude]},
                    "properties": {
                        "cluster_id": cluster_rows_by_label[int(label)].id,
                        "run_id": run.id,
                        "year": year,
                        "crime_type": crime_type,
                        "point_count": 1,
                        "status": "core" if idx in core_indices else "border",
                        "feature_kind": "member",
                    },
                }
            )

        noise_members = [inc for inc, lbl in zip(incidents, labels) if lbl == -1]
        total_noise = len(noise_members)
        for member in noise_members:
            features.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [member.longitude, member.latitude]},
                    "properties": {
                        "cluster_id": None,
                        "run_id": run.id,
                        "year": year,
                        "crime_type": crime_type,
                        "point_count": 1,
                        "status": "noise",
                        "feature_kind": "member",
                    },
                }
            )

        largest_cluster = max((p[1] for p in pending), default=0)

    db.commit()

    clustered = total_core + total_border
    analyzed = clustered + total_noise
    noise_ratio = round(total_noise / analyzed, 4) if analyzed else None
    dominant_share = round(largest_cluster / clustered, 4) if clustered else None

    return {
        "type": "FeatureCollection",
        "metadata": {
            "eps_km": eps_km,
            "min_samples": min_samples,
            "incidents_analyzed": analyzed,
            "cluster_count": len(pending) if incidents else 0,
            # DBSCAN's three-way point classification, reported explicitly.
            "core_point_count": total_core,
            "border_point_count": total_border,
            "clustered_point_count": clustered,
            "noise_point_count": total_noise,
            "noise_ratio": noise_ratio,
            "largest_cluster_share": dominant_share,
            "warnings": _parameter_warnings(noise_ratio, dominant_share, len(pending)),
        },
        "features": features,
    }
