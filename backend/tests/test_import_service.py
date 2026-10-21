"""Importer auto-organizing: the cleanup an operator would otherwise do by hand
(barangay spellings, missing coordinates, missing reference numbers, ambiguous
date order) must happen in the system and be reported, never applied silently."""
import unittest

from app.core.taxonomy import CANONICAL_MUNICIPALITIES
from app.services.import_service import suggest_mapping, validate_rows

MUNICIPALITIES = set(CANONICAL_MUNICIPALITIES)

# Balabak, Pikit — the official centroid the importer places rows at.
BALABAK = (7.122049, 124.718856)

FULL_MAPPING = {
    "incident_id": "id",
    "crime_type": "offense",
    "incident_date": "date",
    "municipality": "town",
    "barangay": "brgy",
    "latitude": "lat",
    "longitude": "lon",
}


def row(**overrides):
    base = {
        "id": "BLT-001",
        "offense": "Theft",
        "date": "2024-03-05",
        "town": "Pikit",
        "brgy": "Balabak",
        "lat": 7.122,
        "lon": 124.718,
    }
    base.update(overrides)
    return base


def run(rows, mapping=None, id_prefix="AUTO"):
    return validate_rows(rows, mapping or FULL_MAPPING, MUNICIPALITIES, id_prefix=id_prefix)


class ImportOrganizingTests(unittest.TestCase):
    def test_barangay_spellings_resolve_to_the_official_name(self):
        for inbound in ["BRGY. BALABAK", "Brgy Balabak", "balabak", "Sitio Maligaya, Balabak"]:
            with self.subTest(inbound=inbound):
                valid, issues, standardizations = run([row(brgy=inbound)])
                self.assertEqual(len(valid), 1)
                self.assertEqual(valid[0]["barangay"], "Balabak")
                self.assertFalse([i for i in issues if i["severity"] == "rejected"])
                if inbound != "Balabak":
                    self.assertTrue(
                        [s for s in standardizations if s["field"] == "barangay"],
                        "the rename must be reported, not applied silently",
                    )

    def test_missing_coordinates_fall_back_to_the_barangay_centroid(self):
        valid, issues, _ = run([row(lat=None, lon=None)])
        self.assertEqual(len(valid), 1)
        self.assertAlmostEqual(valid[0]["latitude"], BALABAK[0], places=5)
        self.assertAlmostEqual(valid[0]["longitude"], BALABAK[1], places=5)
        self.assertEqual(valid[0]["coordinate_source"], "barangay_centroid")
        self.assertEqual(valid[0]["coordinate_precision"], "barangay_level")
        self.assertFalse([i for i in issues if i["severity"] == "rejected"])
        self.assertTrue([i for i in issues if i["severity"] == "warning"])

    def test_unreadable_coordinates_also_fall_back_rather_than_drop_the_row(self):
        valid, _, _ = run([row(lat="n/a", lon="")])
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["coordinate_precision"], "barangay_level")

    def test_out_of_study_area_coordinate_is_replaced_not_rejected(self):
        valid, issues, _ = run([row(lat=14.5995, lon=120.9842)])  # Manila, not PPALMA
        self.assertEqual(len(valid), 1)
        self.assertAlmostEqual(valid[0]["latitude"], BALABAK[0], places=5)
        self.assertEqual(valid[0]["coordinate_source"], "barangay_centroid")
        self.assertTrue([i for i in issues if "outside the PPALMA study area" in i["message"]])

    def test_transposed_coordinate_falls_back_to_the_centroid(self):
        valid, issues, _ = run([row(lat=124.718, lon=7.122)])
        self.assertEqual(len(valid), 1)
        self.assertAlmostEqual(valid[0]["latitude"], BALABAK[0], places=5)
        self.assertEqual(valid[0]["coordinate_source"], "barangay_centroid")
        self.assertTrue([i for i in issues if i["field"] == "latitude"])

    def test_missing_barangay_is_recovered_from_the_coordinate(self):
        valid, _, standardizations = run([row(brgy=None)])
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["barangay"], "Balabak")
        self.assertTrue([s for s in standardizations if s["field"] == "barangay"])

    def test_unmatched_barangay_is_warned_then_recovered_from_the_coordinate(self):
        valid, issues, _ = run([row(brgy="Nonexistent Place")])
        self.assertEqual(len(valid), 1)
        self.assertEqual(valid[0]["barangay"], "Balabak")
        self.assertTrue([i for i in issues if i["field"] == "barangay" and i["severity"] == "warning"])

    def test_row_with_no_usable_location_is_rejected(self):
        valid, issues, _ = run([row(brgy="Nonexistent Place", lat=None, lon=None)])
        self.assertEqual(valid, [])
        self.assertTrue([i for i in issues if i["severity"] == "rejected"])

    def test_missing_incident_id_is_generated_deterministically(self):
        first, _, standardizations = run([row(id=None)], id_prefix="B7")
        second, _, _ = run([row(id=None)], id_prefix="B7")
        self.assertEqual(first[0]["incident_id"], "B7-000001")
        self.assertEqual(second[0]["incident_id"], first[0]["incident_id"])
        self.assertTrue([s for s in standardizations if s["field"] == "incident_id"])

    def test_day_first_dates_are_detected_from_the_column(self):
        # 25/12 proves the column is D/M/Y, so the ambiguous 05/03 is 5 March.
        valid, _, _ = run([row(id="A", date="25/12/2024"), row(id="B", date="05/03/2024")])
        self.assertEqual([v["incident_date"] for v in valid], ["2024-12-25", "2024-03-05"])

    def test_month_first_dates_stay_month_first(self):
        # 12/25 proves M/D/Y, so the ambiguous 03/05 is 5 March, not 3 May.
        valid, _, _ = run([row(id="A", date="12/25/2024"), row(id="B", date="03/05/2024")])
        self.assertEqual([v["incident_date"] for v in valid], ["2024-12-25", "2024-03-05"])

    def test_unprovable_date_order_is_flagged_not_silently_guessed(self):
        valid, issues, _ = run([row(date="05/03/2024")])
        self.assertEqual(len(valid), 1)
        flagged = [i for i in issues if i["field"] == "incident_date"]
        self.assertTrue(flagged, "an ambiguous date with no proof must be flagged")
        self.assertEqual(flagged[0]["severity"], "warning")

    def test_proven_date_order_is_not_flagged(self):
        _, issues, _ = run([row(id="A", date="25/12/2024"), row(id="B", date="05/03/2024")])
        self.assertEqual([i for i in issues if i["field"] == "incident_date"], [])

    def test_reported_coordinates_are_labeled_as_such(self):
        valid, _, _ = run([row()])
        self.assertEqual(valid[0]["coordinate_source"], "reported")
        self.assertEqual(valid[0]["coordinate_precision"], "exact")

    def test_municipality_and_crime_type_are_standardized(self):
        valid, _, standardizations = run([row(town="PIGKAWAYAN", brgy="Balogo", offense="Physical Injuries")])
        self.assertEqual(valid[0]["municipality"], "Pigcawayan")
        self.assertEqual(valid[0]["crime_type"], "Physical Injury")
        changed = {s["field"] for s in standardizations}
        self.assertEqual({"municipality", "crime_type"}, changed & {"municipality", "crime_type"})

    def test_non_index_crime_is_still_rejected(self):
        valid, issues, _ = run([row(offense="Estafa")])
        self.assertEqual(valid, [])
        self.assertTrue([i for i in issues if i["field"] == "crime_type" and i["severity"] == "rejected"])

    def test_blotter_headers_are_auto_mapped(self):
        mapping = suggest_mapping([
            "Blotter Entry No", "Nature of Offense", "Date Committed",
            "Time Committed", "City/Municipality", "Brgy", "Place of Incident",
        ])
        self.assertEqual(mapping["incident_id"], "Blotter Entry No")
        self.assertEqual(mapping["crime_type"], "Nature of Offense")
        self.assertEqual(mapping["incident_date"], "Date Committed")
        self.assertEqual(mapping["incident_time"], "Time Committed")
        self.assertEqual(mapping["municipality"], "City/Municipality")
        self.assertEqual(mapping["barangay"], "Brgy")
        self.assertEqual(mapping["general_location"], "Place of Incident")


if __name__ == "__main__":
    unittest.main()
