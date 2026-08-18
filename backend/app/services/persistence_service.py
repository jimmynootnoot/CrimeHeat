"""Spatio-temporal cluster matching across periods (years).

For each municipality, DBSCAN is run independently per year to find that
year's spatial clusters, then cluster centroids are greedily matched across
years by proximity (within `match_distance_km`) into chains — a chain is our
model of "the same real-world hotspot recurring over time." Thresholds are
configurable (see app.core.config) since the values that will make sense for
the final classification depend on the official PNP dataset's real temporal
span and density.

persistence_score = periods_present / total_periods_analyzed (0..1), where
total_periods_analyzed is the number of distinct years with any data in the
current filter scope — not just the years the chain itself appeared in.

Categories (score compared against `persistence_score_threshold`):
- "temporary": appears in exactly 1 period.
- "intermittent": appears in 2+ periods, score below threshold.
- "historical_persistent": score >= threshold, but NOT present in the latest
  analyzed period — i.e. it recurred strongly for a while and then stopped.
  This is intentionally distinct from "temporary": a chain that was present
  in 4 of 5 years and vanished is a materially different signal than one
  that appeared once.
- "active_persistent": score >= threshold AND present in the latest period —
  the strongest "still an active hotspot" signal.

Known limitation: chain matching is centroid-distance only (greedy nearest
match within `match_distance_km` of the chain's *most recent* centroid). It
does not account for cluster shape/overlap, so two spatially adjacent but
distinct hotspots that happen to be within `match_distance_km` of each other
across different years could be merged into one chain, and a hotspot that
drifts more than `match_distance_km` between consecutive periods will be
split into two chains. A more precise future version would match on convex-
hull polygon overlap (IoU) rather than centroid distance — deferred until
the official PNP dataset's real spatial density is known, since tuning a
polygon-overlap threshold needs real data to calibrate against.

This is a descriptive summary of where historical, already-reported
incidents recurred — it is not a forecast of future crime.
"""
import math
from typing import Optional

from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.municipality import Municipality
from app.models.persistence import PersistenceRecord

EARTH_RADIUS_KM = 6371.0088


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _cluster_year(points: list[tuple[float, float]], eps_km: float, min_samples: int):
    import numpy as np
    from sklearn.cluster import DBSCAN

    if len(points) < min_samples:
        return []
    coords_rad = np.radians(points)
    eps_rad = eps_km / EARTH_RADIUS_KM
    labels = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine").fit_predict(coords_rad)

    clusters = []
    for label in sorted(set(labels) - {-1}):
        members = [pt for pt, lbl in zip(points, labels) if lbl == label]
        lat = sum(p[0] for p in members) / len(members)
        lon = sum(p[1] for p in members) / len(members)
        clusters.append({"lat": lat, "lon": lon, "count": len(members)})
    return clusters


def recompute_persistence(
    db: Session,
    eps_km: float,
    min_samples: int,
    match_distance_km: float,
    score_threshold: float,
    municipality: Optional[str] = None,
    barangay: Optional[str] = None,
    crime_type: Optional[str] = None,
) -> list[PersistenceRecord]:
    municipalities_query = db.query(Municipality)
    if municipality:
        municipalities_query = municipalities_query.filter(Municipality.name == municipality)
    municipalities = municipalities_query.all()

    all_years = sorted(
        {
            int(y[0])
            for y in db.query(extract("year", Incident.incident_date)).distinct().all()
        }
    )
    if not all_years:
        return []
    latest_year = all_years[-1]
    total_periods_analyzed = len(all_years)

    records: list[PersistenceRecord] = []

    for muni in municipalities:
        base_query = db.query(Incident).filter(Incident.municipality_id == muni.id)
        if barangay:
            base_query = base_query.filter(Incident.barangay == barangay)
        if crime_type:
            base_query = base_query.filter(Incident.crime_type == crime_type)

        # chains: list of dicts {lat, lon, years: [int], barangay}
        chains: list[dict] = []

        for year in all_years:
            year_incidents = base_query.filter(extract("year", Incident.incident_date) == year).all()
            if not year_incidents:
                continue
            points = [(i.latitude, i.longitude) for i in year_incidents]
            year_clusters = _cluster_year(points, eps_km, min_samples)

            for cluster in year_clusters:
                best_chain = None
                best_dist = match_distance_km
                for chain in chains:
                    dist = _haversine_km(chain["lat"], chain["lon"], cluster["lat"], cluster["lon"])
                    if dist <= best_dist:
                        best_dist = dist
                        best_chain = chain

                if best_chain is not None:
                    best_chain["lat"] = cluster["lat"]
                    best_chain["lon"] = cluster["lon"]
                    best_chain["years"].append(year)
                else:
                    chains.append({"lat": cluster["lat"], "lon": cluster["lon"], "years": [year]})

        for chain in chains:
            years_present = sorted(set(chain["years"]))
            score = len(years_present) / total_periods_analyzed
            present_in_latest = years_present[-1] == latest_year

            if score >= score_threshold:
                category = "active_persistent" if present_in_latest else "historical_persistent"
            elif len(years_present) >= 2:
                category = "intermittent"
            else:
                category = "temporary"

            records.append(
                PersistenceRecord(
                    municipality=muni.name,
                    barangay=barangay,
                    crime_type=crime_type,
                    category=category,
                    periods_present=years_present,
                    persistence_score=round(score, 4),
                    total_periods_analyzed=total_periods_analyzed,
                    centroid_lat=chain["lat"],
                    centroid_lon=chain["lon"],
                )
            )

    return records
