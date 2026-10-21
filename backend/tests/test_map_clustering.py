"""Map contract regressions using real SQL filtering and DBSCAN on synthetic fixtures."""
from datetime import date
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import Date, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.api.routes import incidents as incident_routes
from app.api.routes.clusters import get_clusters
from app.services import clustering


class FixtureBase(DeclarativeBase):
    pass


class FixtureIncident(FixtureBase):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    municipality: Mapped[str] = mapped_column(String)
    barangay: Mapped[str] = mapped_column(String)
    crime_type: Mapped[str] = mapped_column(String)
    incident_date: Mapped[date] = mapped_column(Date)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)


class MapClusteringTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        FixtureBase.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.addCleanup(patch.stopall)
        patch.object(clustering, "Incident", FixtureIncident).start()
        patch.object(incident_routes, "Incident", FixtureIncident).start()
        # Queries execute against SQLite. Only analysis persistence is mocked:
        # production model tables require PostGIS, irrelevant to this contract.
        self.db = Mock()
        self.db.query.side_effect = self.session.query
        self.next_id = 0
        self.db.add.side_effect = self.assign_analysis_id

    def assign_analysis_id(self, row):
        self.next_id += 1
        row.id = self.next_id

    def add_incidents(self, offsets, municipality="Pikit", barangay="Alpha", crime_type="Theft", year=2024):
        for offset in offsets:
            self.session.add(FixtureIncident(
                municipality=municipality, barangay=barangay, crime_type=crime_type,
                incident_date=date(year, 5, 1), latitude=7.0, longitude=124.0 + offset,
            ))
        self.session.commit()

    def analyze(self, **filters):
        return clustering.run_dbscan(self.db, eps_km=1.0, min_samples=4, **filters)

    def test_core_border_and_noise_members_link_to_their_own_envelopes(self):
        self.add_incidents([0, .001, .002, .003, .011, .05, .10, .101, .102, .103])
        result = self.analyze()
        extents = {f["properties"]["cluster_id"]: f for f in result["features"] if f["geometry"]["type"] == "Polygon"}
        members = [f for f in result["features"] if f["geometry"]["type"] == "Point"]
        self.assertEqual(len(extents), 2)
        self.assertEqual(len(members), 10)
        self.assertEqual(result["metadata"]["incidents_analyzed"], 10)
        self.assertEqual(result["metadata"]["core_point_count"], 8)
        self.assertEqual(result["metadata"]["border_point_count"], 1)
        self.assertEqual(result["metadata"]["noise_point_count"], 1)
        self.assertEqual(result["metadata"]["noise_ratio"], .1)
        for cluster_id, extent in extents.items():
            linked = [f["properties"] for f in members if f["properties"]["cluster_id"] == cluster_id]
            self.assertEqual(len(linked), extent["properties"]["point_count"])
            for status in ("core", "border"):
                self.assertEqual(sum(p["status"] == status for p in linked), extent["properties"][f"{status}_point_count"])
        for feature in members:
            props = feature["properties"]
            self.assertEqual(props["feature_kind"], "member")
            if props["status"] == "noise":
                self.assertIsNone(props["cluster_id"])
            else:
                self.assertIn(props["cluster_id"], extents)

    def test_fewer_than_min_samples_are_all_noise(self):
        self.add_incidents([0, .001])
        result = self.analyze()
        self.assertEqual(result["metadata"]["incidents_analyzed"], 2)
        self.assertEqual(result["metadata"]["cluster_count"], 0)
        self.assertEqual(result["metadata"]["noise_ratio"], 1)
        self.assertEqual([f["properties"]["status"] for f in result["features"]], ["noise", "noise"])

    def test_empty_scope_has_no_ratio_or_features(self):
        result = self.analyze()
        self.assertEqual(result["features"], [])
        self.assertEqual(result["metadata"]["incidents_analyzed"], 0)
        self.assertIsNone(result["metadata"]["noise_ratio"])

    def test_barangay_restricts_analysis_before_clustering(self):
        self.add_incidents([0, .001], barangay="Alpha")
        self.add_incidents([.002, .003], barangay="Beta")
        self.assertEqual(self.analyze()["metadata"]["cluster_count"], 1)
        result = self.analyze(barangay="Alpha")
        self.assertEqual(result["metadata"]["incidents_analyzed"], 2)
        self.assertEqual(result["metadata"]["cluster_count"], 0)
        self.assertEqual(result["metadata"]["noise_ratio"], 1)

    def test_boundary_counts_and_cluster_analysis_use_same_incident_scope(self):
        self.add_incidents([0, .001, .002, .003])
        self.add_incidents([.01], barangay="Beta")
        self.add_incidents([.02], year=2023)
        self.add_incidents([.03], crime_type="Robbery")
        self.add_incidents([.04], municipality="Midsayap")
        filters = dict(municipality="Pikit", barangay="Alpha", crime_type="Theft", year=2024)
        counts = incident_routes.incident_summary(db=self.db, **filters)
        self.assertEqual(counts["municipality_breakdown"], {"Pikit": 4})
        self.assertEqual(counts["total_incidents"], 4)
        self.assertEqual(counts["bounds"], [124.0, 7.0, 124.003, 7.0])
        self.assertEqual(self.analyze(**filters)["metadata"]["incidents_analyzed"], 4)
        self.assertEqual(incident_routes.incident_summary(db=self.db, year=2023)["total_incidents"], 1)
        self.assertEqual(incident_routes.incident_summary(db=self.db)["total_incidents"], 8)
        self.assertEqual(incident_routes.incident_summary(db=self.db, barangay="Missing")["municipality_breakdown"], {})
        self.assertIsNone(incident_routes.incident_summary(db=self.db, barangay="Missing")["bounds"])

    def test_cluster_route_forwards_barangay(self):
        self.add_incidents([0, .001], barangay="Alpha")
        self.add_incidents([.002, .003], barangay="Beta")
        result = get_clusters(barangay="Alpha", eps_km=1.0, min_samples=4, db=self.db)
        self.assertEqual(result["metadata"]["incidents_analyzed"], 2)
        self.assertEqual(result["metadata"]["cluster_count"], 0)


if __name__ == "__main__":
    unittest.main()
