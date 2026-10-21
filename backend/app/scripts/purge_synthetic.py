"""Remove every synthetic demonstration record from the database.

Run with: python -m app.scripts.purge_synthetic

Deletes incidents tagged source='synthetic', the synthetic dataset rows, and
the synthetic_demo reference hotspots, leaving official PNP records untouched.
Analysis artifacts (DBSCAN runs, clusters, persistence chains) computed from the
synthetic set are also cleared, because a chain built from deleted incidents
would otherwise keep showing on the map with nothing behind it.

Idempotent — running it again after the data is gone reports zero removed.
"""
from app.db.session import SessionLocal
from app.models.cluster import Cluster, DBSCANRun
from app.models.dataset import Dataset
from app.models.incident import Incident
from app.models.persistence import PersistenceRecord
from app.models.reference_hotspot import ReferenceHotspot


def run() -> None:
    db = SessionLocal()
    try:
        incidents = db.query(Incident).filter(Incident.source == "synthetic").delete()
        hotspots = (
            db.query(ReferenceHotspot)
            .filter(ReferenceHotspot.label_source == "synthetic_demo")
            .delete()
        )

        # Cluster/persistence rows carry no source column: they are derived from
        # whatever incidents existed at run time, so once synthetic incidents are
        # gone the safe state is no stale analysis at all. Re-run the analysis
        # against the official data from the map.
        persistence = db.query(PersistenceRecord).delete()
        clusters = db.query(Cluster).delete()
        runs = db.query(DBSCANRun).delete()

        datasets = db.query(Dataset).filter(Dataset.source == "synthetic").delete()

        db.commit()
        print(f"Removed {incidents} synthetic incidents.")
        print(f"Removed {hotspots} synthetic_demo reference hotspots.")
        print(f"Cleared {runs} DBSCAN runs, {clusters} clusters, {persistence} persistence records.")
        print(f"Removed {datasets} synthetic dataset records.")
        remaining = db.query(Incident).count()
        official = db.query(Incident).filter(Incident.source == "official").count()
        print(f"Incidents remaining: {remaining} ({official} tagged 'official').")
    finally:
        db.close()


if __name__ == "__main__":
    run()
