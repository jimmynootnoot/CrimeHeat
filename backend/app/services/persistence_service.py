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

from shapely.geometry import MultiPoint, mapping as shapely_mapping
from sqlalchemy import extract
from sqlalchemy.orm import Session

from app.models.incident import Incident
from app.models.municipality import Municipality
from app.models.persistence import PersistenceRecord

EARTH_RADIUS_KM = 6371.0088
# ~100m at this latitude: keeps a single-point extent drawable.
DEGENERATE_HULL_BUFFER_DEG = 0.001

# Level of significance for the H01 municipality comparison (study methodology).
SIGNIFICANCE_LEVEL = 0.05


def _haversine_km(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def _cluster_year(
    points: list[tuple[float, float]],
    eps_km: float,
    min_samples: int,
    ids: Optional[list[int]] = None,
):
    """DBSCAN one period's points.

    `ids` is an optional parallel list of incident ids. When supplied, each
    returned cluster carries the ids of its member incidents, which is what
    lets the municipality comparison count how many eligible incidents fall
    inside a persistent cluster (SOP 3) rather than estimating it.
    """
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
        member_ids = (
            [i for i, lbl in zip(ids, labels) if lbl == label] if ids is not None else []
        )
        clusters.append({
            "lat": lat, "lon": lon, "count": len(members),
            "member_ids": member_ids, "points": members,
        })
    return clusters


# The two categories the study treats as "persistent": both sit at or above
# `persistence_score_threshold`; they differ only in whether the chain is still
# present in the most recent analyzed period.
PERSISTENT_CATEGORIES = ("active_persistent", "historical_persistent")


def _build_chains(
    points_by_year: dict[int, list[tuple[float, float]]],
    ids_by_year: dict[int, list[int]],
    all_years: list[int],
    eps_km: float,
    min_samples: int,
    match_distance_km: float,
) -> list[dict]:
    """Greedy nearest-centroid matching of per-year clusters into chains.

    Shared by the persistence view (SOP 2) and the municipality comparison
    (SOP 3) so the two can never report different chains for the same data.
    """
    chains: list[dict] = []
    for year in all_years:
        points = points_by_year.get(year, [])
        if not points:
            continue
        year_clusters = _cluster_year(points, eps_km, min_samples, ids_by_year.get(year))

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
                best_chain["incident_ids"].extend(cluster["member_ids"])
                best_chain["points"].extend(cluster["points"])
            else:
                chains.append(
                    {
                        "lat": cluster["lat"],
                        "lon": cluster["lon"],
                        "years": [year],
                        "incident_ids": list(cluster["member_ids"]),
                        # Every member point across every period, so the chain
                        # can be drawn as the area it actually covers instead of
                        # as a pin at its latest centroid.
                        "points": list(cluster["points"]),
                    }
                )
    return chains


def chain_extent(points: list[tuple[float, float]]) -> dict | None:
    """Convex hull of a chain's member incidents, as GeoJSON.

    A recurring hotspot is an area, not a coordinate. Where the members are
    collinear or coincident the hull degenerates to a line or point, so it is
    buffered by a small fixed distance purely to stay drawable — that still
    represents the true extent (all incidents at ~one location).
    """
    if not points:
        return None
    hull = MultiPoint([(lon, lat) for lat, lon in points]).convex_hull
    if hull.geom_type in ("Point", "LineString"):
        hull = hull.buffer(DEGENERATE_HULL_BUFFER_DEG)
    return shapely_mapping(hull)


def classify_chain(
    years_present: list[int], total_periods_analyzed: int, latest_year: int, score_threshold: float
) -> tuple[str, float, bool]:
    """Return (category, persistence_score, present_in_latest_period)."""
    score = len(years_present) / total_periods_analyzed
    present_in_latest = years_present[-1] == latest_year
    if score >= score_threshold:
        category = "active_persistent" if present_in_latest else "historical_persistent"
    elif len(years_present) >= 2:
        category = "intermittent"
    else:
        category = "temporary"
    return category, score, present_in_latest


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

    # Fetch every candidate incident in a single round trip and group by
    # (municipality, year) in Python, rather than issuing one query per
    # municipality per year — that N+1 pattern is what made this endpoint
    # take 20+ seconds against a remote DB (6 munis x 10 years = 60 round
    # trips at ~300-400ms latency each).
    muni_ids = [muni.id for muni in municipalities]
    incidents_query = db.query(Incident).filter(Incident.municipality_id.in_(muni_ids))
    if barangay:
        incidents_query = incidents_query.filter(Incident.barangay == barangay)
    if crime_type:
        incidents_query = incidents_query.filter(Incident.crime_type == crime_type)

    points_by_muni_year: dict[tuple[int, int], list[tuple[float, float]]] = {}
    ids_by_muni_year: dict[tuple[int, int], list[int]] = {}
    for incident in incidents_query.all():
        key = (incident.municipality_id, incident.incident_date.year)
        points_by_muni_year.setdefault(key, []).append((incident.latitude, incident.longitude))
        ids_by_muni_year.setdefault(key, []).append(incident.id)

    records: list[PersistenceRecord] = []

    for muni in municipalities:
        chains = _build_chains(
            {y: points_by_muni_year.get((muni.id, y), []) for y in all_years},
            {y: ids_by_muni_year.get((muni.id, y), []) for y in all_years},
            all_years,
            eps_km,
            min_samples,
            match_distance_km,
        )

        for chain in chains:
            years_present = sorted(set(chain["years"]))
            category, score, present_in_latest = classify_chain(
                years_present, total_periods_analyzed, latest_year, score_threshold
            )

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
                    incident_count=len(chain["incident_ids"]),
                    extent_geojson=chain_extent(chain["points"]),
                )
            )

    return records


def compare_municipalities(
    db: Session,
    eps_km: float,
    min_samples: int,
    match_distance_km: float,
    score_threshold: float,
    crime_type: Optional[str] = None,
) -> dict:
    """SOP 3 — compare the PPALMA municipalities on their persistent clusters.

    Reports, per municipality: the number of persistent clusters, the mean and
    highest persistence score, and the proportion of eligible incidents that
    fall inside a persistent cluster. Incident membership is taken from the
    actual DBSCAN cluster members that make up each persistent chain, not
    estimated from centroid proximity.

    H01 is tested with a Kruskal-Wallis H test over the chain-level
    persistence scores. The test needs at least two municipalities with at
    least one chain each, and cannot run when every observation is tied; when
    those conditions are not met the comparison is returned descriptively with
    the reason stated, as the methodology requires.
    """
    municipalities = db.query(Municipality).order_by(Municipality.name).all()

    all_years = sorted(
        {int(y[0]) for y in db.query(extract("year", Incident.incident_date)).distinct().all()}
    )
    if not all_years:
        return {
            "municipalities": [],
            "metadata": _comparison_metadata(eps_km, min_samples, match_distance_km, score_threshold, 0),
            "hypothesis_test": _kruskal_unavailable("No incident data is available to analyze."),
        }

    latest_year = all_years[-1]
    total_periods_analyzed = len(all_years)

    incidents_query = db.query(Incident)
    if crime_type:
        incidents_query = incidents_query.filter(Incident.crime_type == crime_type)

    points_by_muni_year: dict[tuple[int, int], list[tuple[float, float]]] = {}
    ids_by_muni_year: dict[tuple[int, int], list[int]] = {}
    totals_by_muni: dict[int, int] = {}
    for incident in incidents_query.all():
        key = (incident.municipality_id, incident.incident_date.year)
        points_by_muni_year.setdefault(key, []).append((incident.latitude, incident.longitude))
        ids_by_muni_year.setdefault(key, []).append(incident.id)
        totals_by_muni[incident.municipality_id] = totals_by_muni.get(incident.municipality_id, 0) + 1

    rows = []
    scores_by_muni: list[list[float]] = []

    for muni in municipalities:
        chains = _build_chains(
            {y: points_by_muni_year.get((muni.id, y), []) for y in all_years},
            {y: ids_by_muni_year.get((muni.id, y), []) for y in all_years},
            all_years,
            eps_km,
            min_samples,
            match_distance_km,
        )

        chain_scores: list[float] = []
        persistent_incident_ids: set[int] = set()
        persistent_count = 0

        for chain in chains:
            years_present = sorted(set(chain["years"]))
            category, score, _present = classify_chain(
                years_present, total_periods_analyzed, latest_year, score_threshold
            )
            chain_scores.append(score)
            if category in PERSISTENT_CATEGORIES:
                persistent_count += 1
                persistent_incident_ids.update(chain["incident_ids"])

        total_incidents = totals_by_muni.get(muni.id, 0)
        rows.append(
            {
                "municipality": muni.name,
                "total_incidents": total_incidents,
                "cluster_chains": len(chains),
                "persistent_clusters": persistent_count,
                # Mean/highest are over every chain, so a municipality with
                # many weak chains is not flattered by averaging only its
                # persistent ones.
                "average_persistence_score_percent": (
                    round(sum(chain_scores) / len(chain_scores) * 100, 2) if chain_scores else None
                ),
                "highest_persistence_score_percent": (
                    round(max(chain_scores) * 100, 2) if chain_scores else None
                ),
                "incidents_in_persistent_clusters": len(persistent_incident_ids),
                "persistent_cluster_incident_proportion_percent": (
                    round(len(persistent_incident_ids) / total_incidents * 100, 2)
                    if total_incidents
                    else None
                ),
            }
        )
        if chain_scores:
            scores_by_muni.append(chain_scores)

    return {
        "municipalities": rows,
        "metadata": _comparison_metadata(
            eps_km, min_samples, match_distance_km, score_threshold, total_periods_analyzed
        ),
        "hypothesis_test": _kruskal_wallis(scores_by_muni),
    }


def _comparison_metadata(
    eps_km: float, min_samples: int, match_distance_km: float, score_threshold: float, periods: int
) -> dict:
    return {
        "eps_km": eps_km,
        "min_samples": min_samples,
        "match_distance_km": match_distance_km,
        "persistence_score_threshold": score_threshold,
        "total_periods_analyzed": periods,
        "persistent_categories": list(PERSISTENT_CATEGORIES),
        "proportion_formula": (
            "(Eligible incidents assigned to persistent clusters / Total eligible incidents) x 100"
        ),
    }


def _kruskal_unavailable(reason: str) -> dict:
    return {
        "test": "Kruskal-Wallis H",
        "applicable": False,
        "reason": reason,
        "alpha": SIGNIFICANCE_LEVEL,
        "h_statistic": None,
        "p_value": None,
        "degrees_of_freedom": None,
        "decision": "Not tested — municipality comparison reported descriptively.",
    }


def _kruskal_wallis(groups: list[list[float]]) -> dict:
    """H01: no significant difference among municipalities in persistence score."""
    groups = [g for g in groups if g]
    if len(groups) < 2:
        return _kruskal_unavailable(
            "Fewer than two municipalities have cluster-level persistence scores to compare."
        )
    if len({round(v, 10) for group in groups for v in group}) < 2:
        return _kruskal_unavailable(
            "All persistence scores are identical, so the ranks contain no variation to test."
        )

    from scipy import stats

    h_statistic, p_value = stats.kruskal(*groups)
    rejected = bool(p_value < SIGNIFICANCE_LEVEL)
    return {
        "test": "Kruskal-Wallis H",
        "applicable": True,
        "reason": None,
        "alpha": SIGNIFICANCE_LEVEL,
        "groups_compared": len(groups),
        "observations": sum(len(g) for g in groups),
        "h_statistic": round(float(h_statistic), 4),
        "p_value": round(float(p_value), 6),
        "degrees_of_freedom": len(groups) - 1,
        "null_hypothesis": (
            "H01: There is no significant difference among the PPALMA municipalities "
            "in terms of the persistence scores of the detected major crime clusters."
        ),
        "decision": (
            "Reject the null hypothesis (p < 0.05): the municipalities differ significantly."
            if rejected
            else "Fail to reject the null hypothesis (p >= 0.05): insufficient evidence of a difference."
        ),
        "null_hypothesis_rejected": rejected,
    }
