"""Temporal train/test split: real-data external validation without a
separately supplied reference dataset. Uses the same SQLite-fixture pattern
as test_map_clustering.py so DBSCAN runs against real SQL filtering."""
from datetime import date
import unittest
from unittest.mock import Mock, patch

from sqlalchemy import Date, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.services import temporal_split_evaluation as tse


class FixtureBase(DeclarativeBase):
    pass


class FixtureIncident(FixtureBase):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    municipality: Mapped[str] = mapped_column(String)
    crime_type: Mapped[str] = mapped_column(String)
    incident_date: Mapped[date] = mapped_column(Date)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    source: Mapped[str] = mapped_column(String)


class TemporalSplitEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        FixtureBase.metadata.create_all(self.engine)
        self.session = Session(self.engine)
        self.addCleanup(self.engine.dispose)
        self.addCleanup(self.session.close)
        self.addCleanup(patch.stopall)
        patch.object(tse, "Incident", FixtureIncident).start()
        self.db = Mock()
        self.db.query.side_effect = self.session.query

    def add(self, lon_base, lon_offsets, day, municipality="Pikit", crime_type="Theft", source="official"):
        for offset in lon_offsets:
            self.session.add(FixtureIncident(
                municipality=municipality, crime_type=crime_type, incident_date=day,
                latitude=7.0, longitude=lon_base + offset, source=source,
            ))
        self.session.commit()

    def run_eval(self, **kwargs):
        return tse.run_temporal_split_evaluation(
            self.db, cutoff_date=date(2024, 6, 1), source="official", **kwargs
        )

    def test_recurring_hotspot_is_a_true_positive_and_cooled_one_is_a_false_positive(self):
        # Cell A: clustered pre-cutoff, and incidents recur post-cutoff -> TP.
        self.add(124.00, [0, .0005, .001, .0015], date(2024, 1, 5))
        self.add(124.00, [.0002], date(2024, 7, 1))
        # Cell B: clustered pre-cutoff, but nothing happens there again -> FP.
        self.add(124.10, [0, .0005, .001, .0015], date(2024, 1, 5))
        # Cell C: quiet pre-cutoff (noise, not clustered), but an incident
        # appears post-cutoff -> a real hotspot the algorithm could not have
        # flagged in advance -> FN.
        self.add(124.20, [0], date(2024, 1, 5))
        self.add(124.20, [.0002], date(2024, 7, 1))
        # Cell D: one quiet pre-cutoff incident, nothing afterward -> TN.
        self.add(124.30, [0], date(2024, 1, 5))

        result = self.run_eval(eps_km=1.0, min_samples=4, cell_km=1.0)

        self.assertEqual(result["true_positives"], 1)
        self.assertEqual(result["false_positives"], 1)
        self.assertEqual(result["false_negatives"], 1)
        self.assertEqual(result["true_negatives"], 1)
        self.assertEqual(result["precision_percent"], 50.0)
        self.assertEqual(result["recall_percent"], 50.0)
        self.assertEqual(result["f1_score_percent"], 50.0)
        self.assertEqual(result["train_period"]["incident_count"], 10)
        self.assertEqual(result["test_period"]["incident_count"], 2)
        self.assertEqual(result["train_cluster_count"], 2)

        predicted_rows = {
            row.split(",")[0]: row.split(",")[1]
            for row in result["predictions_csv"].splitlines()[1:]
        }
        reference_rows = {
            row.split(",")[0]: row.split(",")[1]
            for row in result["reference_csv"].splitlines()[1:]
        }
        self.assertEqual(set(predicted_rows), set(reference_rows))
        self.assertEqual(sum(v == "1" for v in predicted_rows.values()), 2)
        self.assertEqual(sum(v == "1" for v in reference_rows.values()), 2)

    def test_sources_are_scored_independently(self):
        self.add(124.00, [0, .001, .002, .003], date(2024, 1, 5), source="official")
        self.add(124.00, [.0002], date(2024, 7, 1), source="official")
        self.add(124.50, [0, .001, .002, .003], date(2024, 1, 5), source="geocoded")

        official_result = self.run_eval()
        self.assertEqual(official_result["dataset_source"], "official")
        self.assertEqual(official_result["true_positives"], 1)
        # The official run must not have swept in the geocoded rows.
        self.assertEqual(official_result["train_period"]["incident_count"], 4)

        # Scoring the geocoded rows alone finds no test-window incidents, which
        # proves the two provenances are queried separately.
        with self.assertRaises(ValueError):
            tse.run_temporal_split_evaluation(self.db, date(2024, 6, 1), "geocoded")

    def test_rejects_cutoff_with_no_training_or_no_test_incidents(self):
        self.add(124.00, [0, .001], date(2024, 1, 5))
        with self.assertRaises(ValueError):
            self.run_eval()  # everything is pre-cutoff; no test window
        self.add(124.00, [.002], date(2024, 7, 1))
        with self.assertRaises(ValueError):
            tse.run_temporal_split_evaluation(self.db, date(2023, 1, 1), "official")  # nothing pre-cutoff

    def test_municipality_and_crime_type_filters_scope_both_windows(self):
        self.add(124.00, [0, .001, .002, .003], date(2024, 1, 5), municipality="Pikit", crime_type="Theft")
        self.add(124.00, [.0002], date(2024, 7, 1), municipality="Pikit", crime_type="Theft")
        self.add(124.00, [.0003], date(2024, 7, 1), municipality="Pikit", crime_type="Robbery")
        self.add(124.90, [0, .001], date(2024, 1, 5), municipality="Midsayap", crime_type="Theft")

        result = self.run_eval(municipality="Pikit", crime_type="Theft")
        self.assertEqual(result["train_period"]["incident_count"], 4)
        self.assertEqual(result["test_period"]["incident_count"], 1)


if __name__ == "__main__":
    unittest.main()
