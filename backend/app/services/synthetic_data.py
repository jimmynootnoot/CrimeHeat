"""Reproducible synthetic demonstration dataset.

The official PNP dataset is not yet available. This module generates a clearly
fictional stand-in with the same structure, so the analysis pipeline can be
built and demonstrated without misrepresenting anything as real.

Every record carries source='synthetic'. Nothing produced here may be cited as
a PNP finding.

WHY IT IS NOT UNIFORM RANDOM NOISE
----------------------------------
A uniformly random point cloud has no spatial structure, so DBSCAN would find
nothing and the persistence analysis would have nothing to classify. To
exercise (and visibly demonstrate) every branch of the analysis, the generator
plants hotspot *sites* with deliberate temporal behaviour:

  active_persistent      present in most periods INCLUDING the final one
  historical_persistent  recurs strongly early, then stops before the final period
  intermittent           reappears in a few scattered, non-consecutive periods
  temporary              appears in exactly one period

Scattered background incidents are layered underneath so a realistic share of
points fall outside any cluster and are labeled noise by DBSCAN.

These planted sites double as the demonstration ground truth: the
`reference_hotspots` GeoJSON written by this module marks where recurring
concentrations were deliberately placed. That is what makes a demo-only
precision/recall/F1 meaningful — and it is *only* meaningful because we know
the answer by construction. With official data no such ground truth exists
unless an authorized reference classification is supplied.

Reproducibility: all randomness derives from a single fixed seed.
"""
import csv
import json
import math
import random
from datetime import date, time, timedelta
from pathlib import Path

import geopandas as gpd
from shapely.geometry import Point, mapping as shapely_mapping

from app.core.taxonomy import (
    CRIMES_AGAINST_PERSONS,
    INDEX_CRIME_TYPES,
    normalize_municipality,
)

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
BOUNDARY_PATH = DATA_DIR / "boundaries" / "ppalma_municipalities.geojson"
BARANGAYS_PATH = DATA_DIR / "boundaries" / "ppalma_barangays.json"
OUTPUT_CSV = DATA_DIR / "synthetic" / "synthetic_incidents.csv"
OUTPUT_HOTSPOTS = DATA_DIR / "synthetic" / "synthetic_reference_hotspots.geojson"

SEED = 42
YEARS = list(range(2016, 2026))  # 2016-2025 inclusive, per specification
FINAL_YEAR = YEARS[-1]

# Degrees per kilometre at roughly 7 degrees N. Latitude and longitude scales
# are within ~1% of each other here, so a single factor is accurate enough for
# placing synthetic points (the analysis itself uses true haversine distance).
KM_PER_DEGREE = 110.5

LOCATION_DESCRIPTORS = [
    "Near the public market",
    "Along the national highway",
    "Near the barangay hall",
    "Residential area",
    "Near the elementary school",
    "Near the town plaza",
    "Along a farm-to-market road",
    "Near a rice mill",
    "Roadside, near a sari-sari store",
    "Near the river crossing",
    "Near the transport terminal",
    "Along an irrigation canal road",
]

# Relative incident volume per municipality, so totals are not artificially flat.
MUNICIPALITY_WEIGHT = {
    "Midsayap": 1.35,
    "Pikit": 1.15,
    "Pigcawayan": 1.05,
    "Libungan": 0.90,
    "Alamada": 0.85,
    "Aleosan": 0.70,
}

# Background (non-hotspot) crime mix. Property crimes dominate, matching the
# general shape of index-crime reporting; still entirely fictional.
BACKGROUND_CRIME_WEIGHTS = {
    "Theft": 26,
    "Physical Injury": 20,
    "Robbery": 16,
    "Carnapping": 10,
    "Cattle Rustling": 9,
    "Rape": 7,
    "Homicide": 7,
    "Murder": 5,
}

# Site archetypes: (label, dominant crime, incidents per active period range)
SITE_PLAN = [
    ("active_persistent", 9, 14),
    ("historical_persistent", 8, 13),
    ("intermittent", 6, 10),
    ("temporary", 6, 10),
]


def km_to_deg(km: float) -> float:
    return km / KM_PER_DEGREE


def _load_boundaries() -> gpd.GeoDataFrame:
    return gpd.read_file(BOUNDARY_PATH)


def _load_barangays() -> dict[str, list[str]]:
    with open(BARANGAYS_PATH, encoding="utf-8-sig") as f:
        raw = json.load(f)
    # Keys come from the boundary source and may use the alternate spelling.
    canonical: dict[str, list[str]] = {}
    for key, names in raw.items():
        name, _ = normalize_municipality(key)
        canonical[name or key] = names
    return canonical


def _random_point_in_polygon(polygon, rng: random.Random) -> Point:
    minx, miny, maxx, maxy = polygon.bounds
    for _ in range(2000):
        candidate = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if polygon.contains(candidate):
            return candidate
    return polygon.representative_point()


def _place_anchor(polygon, rng: random.Random, radius_deg: float, taken: list[Point], min_sep_deg: float):
    """Find a site anchor that sits fully inside the municipality and is far
    enough from existing anchors that DBSCAN will not merge two planted sites
    into one cluster."""
    best = None
    for _ in range(600):
        candidate = _random_point_in_polygon(polygon, rng)
        if not polygon.contains(candidate.buffer(radius_deg)):
            continue
        if any(candidate.distance(other) < min_sep_deg for other in taken):
            continue
        return candidate
    # Relax the separation rule rather than fail; still require containment.
    for _ in range(600):
        candidate = _random_point_in_polygon(polygon, rng)
        if polygon.contains(candidate.buffer(radius_deg)):
            best = candidate
            break
    return best or _random_point_in_polygon(polygon, rng)


def _active_years(archetype: str, rng: random.Random) -> list[int]:
    """Which periods this site produces incidents in."""
    if archetype == "active_persistent":
        # Most periods, always including the final one.
        count = rng.randint(7, 9)
        years = set(rng.sample(YEARS[:-1], count - 1))
        years.add(FINAL_YEAR)
        return sorted(years)

    if archetype == "historical_persistent":
        # Strong early run that stops well before the final period.
        stop = rng.choice([2020, 2021, 2022])
        window = [y for y in YEARS if y <= stop]
        count = max(4, min(len(window), rng.randint(5, 7)))
        return sorted(rng.sample(window, count))

    if archetype == "intermittent":
        # A few scattered periods, deliberately non-consecutive where possible.
        count = rng.randint(2, 3)
        return sorted(rng.sample(YEARS[:-1], count))

    # temporary
    return [rng.choice(YEARS)]


def _point_near(anchor: Point, radius_deg: float, polygon, rng: random.Random) -> Point:
    """Gaussian scatter around a site anchor, kept inside the municipality."""
    sigma = radius_deg / 2.0
    for _ in range(80):
        candidate = Point(
            anchor.x + rng.gauss(0, sigma),
            anchor.y + rng.gauss(0, sigma),
        )
        if polygon.contains(candidate):
            return candidate
    return anchor


def _random_date_in_year(rng: random.Random, year: int) -> date:
    start = date(year, 1, 1)
    return start + timedelta(days=rng.randint(0, (date(year, 12, 31) - start).days))


def _random_time(rng: random.Random) -> time:
    # Mild evening skew so temporal charts are not perfectly flat.
    hour = rng.choice(list(range(24)) + [18, 19, 20, 21, 22, 20, 21])
    return time(hour=hour, minute=rng.randint(0, 59))


def _weighted_crime(rng: random.Random) -> str:
    types = list(BACKGROUND_CRIME_WEIGHTS)
    weights = [BACKGROUND_CRIME_WEIGHTS[t] for t in types]
    return rng.choices(types, weights=weights, k=1)[0]


def generate(seed: int = SEED, noise_incidents: int = 900) -> tuple[list[dict], list[dict]]:
    """Return (incident_records, reference_hotspot_features).

    Deterministic for a given seed.
    """
    rng = random.Random(seed)
    gdf = _load_boundaries()
    barangays_by_muni = _load_barangays()

    municipalities = []
    for _, row in gdf.iterrows():
        name, _std = normalize_municipality(row["adm3_en"])
        municipalities.append((name, row.geometry))
    municipalities.sort(key=lambda m: m[0])  # stable order -> reproducible IDs

    records: list[dict] = []
    hotspot_features: list[dict] = []

    # --- Planted hotspot sites -------------------------------------------
    for muni_name, polygon in municipalities:
        weight = MUNICIPALITY_WEIGHT.get(muni_name, 1.0)
        barangays = barangays_by_muni.get(muni_name, ["Poblacion"])
        anchors_taken: list[Point] = []
        site_index = 0

        for archetype, lo, hi in SITE_PLAN:
            site_index += 1
            radius_km = rng.uniform(0.35, 0.6)
            radius_deg = km_to_deg(radius_km)
            anchor = _place_anchor(
                polygon, rng, radius_deg, anchors_taken, min_sep_deg=km_to_deg(4.0)
            )
            anchors_taken.append(anchor)

            dominant_crime = rng.choice(INDEX_CRIME_TYPES)
            years_active = _active_years(archetype, rng)
            site_barangay = rng.choice(barangays)

            for year in years_active:
                n = max(4, int(round(rng.randint(lo, hi) * weight)))
                for _ in range(n):
                    point = _point_near(anchor, radius_deg, polygon, rng)
                    # 70% of a site's incidents are its dominant crime type.
                    crime = dominant_crime if rng.random() < 0.70 else _weighted_crime(rng)
                    records.append(
                        _make_record(
                            rng,
                            muni_name,
                            site_barangay if rng.random() < 0.8 else rng.choice(barangays),
                            crime,
                            year,
                            point,
                            coordinate_source="reported",
                            coordinate_precision="exact",
                        )
                    )

            # Only genuinely recurring sites become reference hotspots. A
            # single-period site is not a hotspot by this study's definition,
            # so labeling it as ground truth would corrupt the evaluation.
            if archetype in ("active_persistent", "historical_persistent"):
                hotspot_features.append(
                    {
                        "type": "Feature",
                        "geometry": shapely_mapping(anchor.buffer(km_to_deg(1.0))),
                        "properties": {
                            "name": f"{muni_name} reference site {site_index}",
                            "municipality": muni_name,
                            "archetype": archetype,
                            "label_source": "synthetic_demo",
                            "years_active": years_active,
                            "dominant_crime_type": dominant_crime,
                            "notes": (
                                "Demonstration-only ground truth. Marks where the synthetic "
                                "generator deliberately planted a recurring concentration. "
                                "Not a PNP-validated hotspot."
                            ),
                        },
                    }
                )

    # --- Scattered background incidents ----------------------------------
    total_weight = sum(MUNICIPALITY_WEIGHT.get(n, 1.0) for n, _ in municipalities)
    for muni_name, polygon in municipalities:
        weight = MUNICIPALITY_WEIGHT.get(muni_name, 1.0)
        share = int(round(noise_incidents * weight / total_weight))
        barangays = barangays_by_muni.get(muni_name, ["Poblacion"])
        for _ in range(share):
            point = _random_point_in_polygon(polygon, rng)
            # Year-over-year drift so annual totals vary rather than being flat.
            year = rng.choices(YEARS, weights=[8, 9, 10, 11, 12, 9, 11, 12, 13, 12], k=1)[0]
            records.append(
                _make_record(
                    rng,
                    muni_name,
                    rng.choice(barangays),
                    _weighted_crime(rng),
                    year,
                    point,
                    coordinate_source=rng.choices(
                        ["reported", "geocoded", "barangay_centroid"], weights=[70, 22, 8], k=1
                    )[0],
                    coordinate_precision=rng.choices(
                        ["exact", "approximate", "barangay_level"], weights=[70, 22, 8], k=1
                    )[0],
                )
            )

    # Stable ordering by date, then assign sequential anonymous IDs.
    records.sort(key=lambda r: (r["incident_date"], r["municipality"], r["_ord"]))
    for i, rec in enumerate(records, start=1):
        rec["incident_id"] = f"SYN-{i:05d}"
        del rec["_ord"]

    return records, hotspot_features


def _make_record(
    rng: random.Random,
    municipality: str,
    barangay: str,
    crime_type: str,
    year: int,
    point: Point,
    coordinate_source: str,
    coordinate_precision: str,
) -> dict:
    return {
        "incident_id": "",  # assigned after sorting
        "crime_type": crime_type,
        "incident_date": _random_date_in_year(rng, year).isoformat(),
        "incident_time": _random_time(rng).strftime("%H:%M"),
        "municipality": municipality,
        "barangay": barangay,
        "general_location": rng.choice(LOCATION_DESCRIPTORS),
        "latitude": round(point.y, 6),
        "longitude": round(point.x, 6),
        "crime_classification": (
            "Crime Against Person" if crime_type in CRIMES_AGAINST_PERSONS else "Crime Against Property"
        ),
        "index_nonindex_flag": "index",
        "coordinate_source": coordinate_source,
        "coordinate_precision": coordinate_precision,
        "case_status_generalized": rng.choices(
            ["under_investigation", "filed_in_court", "solved", "cleared"],
            weights=[40, 25, 20, 15],
            k=1,
        )[0],
        "source": "synthetic",
        "_ord": rng.random(),
    }


def write_csv(records: list[dict]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(records[0].keys()))
        writer.writeheader()
        writer.writerows(records)


def write_reference_hotspots(features: list[dict]) -> None:
    OUTPUT_HOTSPOTS.parent.mkdir(parents=True, exist_ok=True)
    collection = {
        "type": "FeatureCollection",
        "metadata": {
            "label_source": "synthetic_demo",
            "seed": SEED,
            "warning": (
                "DEMONSTRATION ONLY. These polygons are the known ground truth of the "
                "synthetic generator, not validated PNP hotspots. Any precision, recall, "
                "or F1-score computed against them is a demonstration of the evaluation "
                "pipeline, not evidence about real crime patterns."
            ),
        },
        "features": features,
    }
    with open(OUTPUT_HOTSPOTS, "w", encoding="utf-8") as f:
        json.dump(collection, f, indent=2)


if __name__ == "__main__":
    rows, hotspots = generate()
    write_csv(rows)
    write_reference_hotspots(hotspots)

    years = sorted({r["incident_date"][:4] for r in rows})
    munis = sorted({r["municipality"] for r in rows})
    print(f"Generated {len(rows)} synthetic incidents -> {OUTPUT_CSV}")
    print(f"  years:          {years[0]}-{years[-1]} ({len(years)} periods)")
    print(f"  municipalities: {', '.join(munis)}")
    print(f"  crime types:    {len({r['crime_type'] for r in rows})} of {len(INDEX_CRIME_TYPES)} index crimes")
    print(f"Wrote {len(hotspots)} demo reference hotspots -> {OUTPUT_HOTSPOTS}")
