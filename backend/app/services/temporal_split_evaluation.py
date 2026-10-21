"""External algorithmic evaluation via a temporal train/test split.

The PNP data-sharing request behind this dataset covers incident-level fields
only (crime type, date, municipality, barangay, location, coordinates) — it
does not include a separately certified list of confirmed hotspots. Without
that, comparing DBSCAN's output to a reference has nowhere to get a reference
from, other than the same incidents the algorithm already sees, which would be
circular.

This module avoids that by holding out time instead of asking for a second
dataset: clusters are detected using only incidents strictly before a cutoff
date (the training window), and the reference label for each spatial unit is
whether an incident actually, independently occurred there on or after the
cutoff (the test window). The algorithm never sees the test-window incidents
when producing its predictions, so the comparison is a genuine, non-circular
external validation — the same "predictive accuracy" logic used to validate
hotspot policing in the literature — built entirely from data already covered
by the PNP request. It is not a substitute for an independently certified
hotspot list; it is what real-data validation looks like when the licensed
input is incident records only.

Runs over the uploaded PNP incidents (`source='official'`); any other stored
provenance value can be scored the same way by passing it as `source`.
"""
import math
from collections import Counter
from datetime import date
from typing import Optional

import numpy as np
from sklearn.cluster import DBSCAN
from sqlalchemy.orm import Session

from app.models.incident import Incident

EARTH_RADIUS_KM = 6371.0088
KM_PER_DEGREE_LATITUDE = 111.32


def _grid_unit_id(
    latitude: float, longitude: float, min_lat: float, min_lon: float,
    cell_lat_deg: float, cell_lon_deg: float,
) -> str:
    row = int((latitude - min_lat) // cell_lat_deg)
    col = int((longitude - min_lon) // cell_lon_deg)
    return f"r{row}c{col}"


def run_temporal_split_evaluation(
    db: Session,
    cutoff_date: date,
    source: str,
    municipality: Optional[str] = None,
    crime_type: Optional[str] = None,
    eps_km: float = 1.0,
    min_samples: int = 4,
    cell_km: float = 1.0,
) -> dict:
    query = db.query(Incident).filter(Incident.source == source)
    if municipality:
        query = query.filter(Incident.municipality == municipality)
    if crime_type:
        query = query.filter(Incident.crime_type == crime_type)
    incidents = query.order_by(Incident.incident_date).all()

    train = [i for i in incidents if i.incident_date < cutoff_date]
    test = [i for i in incidents if i.incident_date >= cutoff_date]
    if not train:
        raise ValueError("No incidents fall before the cutoff date; choose a later cutoff.")
    if not test:
        raise ValueError("No incidents fall on or after the cutoff date; choose an earlier cutoff.")

    # One grid, built over both windows together, so a unit means the same
    # place whether it is being scored as a prediction or as a reference.
    all_incidents = train + test
    lats = [i.latitude for i in all_incidents]
    lons = [i.longitude for i in all_incidents]
    min_lat, min_lon = min(lats), min(lons)
    mean_lat = sum(lats) / len(lats)
    cell_lat_deg = cell_km / KM_PER_DEGREE_LATITUDE
    cell_lon_deg = cell_km / (KM_PER_DEGREE_LATITUDE * math.cos(math.radians(mean_lat)))

    def unit_id(incident: Incident) -> str:
        return _grid_unit_id(incident.latitude, incident.longitude, min_lat, min_lon, cell_lat_deg, cell_lon_deg)

    # --- Predicted: DBSCAN sees the training window only ---
    coords_rad = np.radians([[i.latitude, i.longitude] for i in train])
    eps_rad = eps_km / EARTH_RADIUS_KM
    labels = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine").fit(coords_rad).labels_
    predicted_units = {unit_id(incident) for incident, label in zip(train, labels) if label != -1}

    # --- Reference: did a real incident actually occur here afterward? ---
    reference_units = {unit_id(incident) for incident in test}

    active_units = sorted({unit_id(incident) for incident in all_incidents})
    counts: Counter = Counter()
    rows = []
    for unit in active_units:
        predicted = unit in predicted_units
        reference = unit in reference_units
        rows.append((unit, predicted, reference))
        counts[(predicted, reference)] += 1

    tp, fp, fn, tn = (counts[key] for key in [(True, True), (True, False), (False, True), (False, False)])
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * tp / (2 * tp + fp + fn) if 2 * tp + fp + fn else 0.0

    predictions_csv = "unit_id,predicted_label\n" + "".join(
        f"{unit},{int(predicted)}\n" for unit, predicted, _ in rows
    )
    reference_csv = "unit_id,reference_label\n" + "".join(
        f"{unit},{int(reference)}\n" for unit, _, reference in rows
    )

    return {
        "cutoff_date": cutoff_date.isoformat(),
        "dataset_source": source,
        "train_period": {
            "start": train[0].incident_date.isoformat(),
            "end": train[-1].incident_date.isoformat(),
            "incident_count": len(train),
        },
        "test_period": {
            "start": test[0].incident_date.isoformat(),
            "end": test[-1].incident_date.isoformat(),
            "incident_count": len(test),
        },
        "eps_km": eps_km,
        "min_samples": min_samples,
        "cell_km": cell_km,
        "train_cluster_count": len(set(labels) - {-1}),
        "train_noise_count": int(sum(1 for label in labels if label == -1)),
        "active_unit_count": len(active_units),
        "predicted_hotspot_unit_count": len(predicted_units),
        "reference_hotspot_unit_count": len(reference_units),
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "true_negatives": tn,
        "precision_percent": precision * 100,
        "recall_percent": recall * 100,
        "f1_score_percent": f1 * 100,
        "predictions_csv": predictions_csv,
        "reference_csv": reference_csv,
        "methodology": (
            f"Temporal hold-out split: clusters were detected using only incidents before "
            f"{cutoff_date.isoformat()} (training window). The reference label for each "
            f"{cell_km:g} km grid cell records whether an incident actually occurred there on "
            f"or after that date (test window), independently of the clustering step. "
            "No externally supplied ground truth was used."
        ),
    }
