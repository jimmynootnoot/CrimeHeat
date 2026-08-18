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
) -> dict:
    query = db.query(Incident)
    if municipality:
        query = query.filter(Incident.municipality == municipality)
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

    if len(incidents) >= min_samples:
        coords_rad = np.radians([[i.latitude, i.longitude] for i in incidents])
        eps_rad = eps_km / EARTH_RADIUS_KM
        labels = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine").fit_predict(coords_rad)

        cluster_ids = sorted(set(labels) - {-1})
        for label in cluster_ids:
            members = [inc for inc, lbl in zip(incidents, labels) if lbl == label]
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
            db.flush()

            features.append(
                {
                    "type": "Feature",
                    "geometry": cluster_row.hull_geojson,
                    "properties": {
                        "cluster_id": cluster_row.id,
                        "run_id": run.id,
                        "year": year,
                        "crime_type": crime_type,
                        "point_count": len(members),
                        "status": "core",
                        "centroid": [centroid_lon, centroid_lat],
                        "municipality": cluster_row.municipality,
                        "dominant_crime_type": dominant_crime_type,
                        "barangays": barangays,
                    },
                }
            )

        noise_members = [inc for inc, lbl in zip(incidents, labels) if lbl == -1]
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
                    },
                }
            )

    db.commit()

    return {
        "type": "FeatureCollection",
        "metadata": {"eps_km": eps_km, "min_samples": min_samples},
        "features": features,
    }
