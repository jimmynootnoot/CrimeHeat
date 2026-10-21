import json
import unittest
from pathlib import Path

from app.core.taxonomy import normalize_municipality
from app.services.locality import barangay_centroid, nearest_barangay


ROOT = Path(__file__).resolve().parents[2]


class LocalityTests(unittest.TestCase):
    def test_every_ppalma_barangay_has_a_reference_centroid(self):
        with (ROOT / "data" / "boundaries" / "ppalma_barangays.json").open(
            encoding="utf-8-sig"
        ) as source:
            municipalities = json.load(source)

        missing = []
        for source_municipality, barangays in municipalities.items():
            municipality, _ = normalize_municipality(source_municipality)
            for barangay in barangays:
                if barangay_centroid(municipality or source_municipality, barangay) is None:
                    missing.append((municipality, barangay))

        self.assertEqual(missing, [])

    def test_poblacion_7_focus_matches_the_reference_location(self):
        focus = barangay_centroid("Midsayap", "Barangay Poblacion 7")
        self.assertIsNotNone(focus)
        self.assertAlmostEqual(focus[0], 7.183222, places=6)
        self.assertAlmostEqual(focus[1], 124.529614, places=6)
        self.assertEqual(nearest_barangay("Midsayap", *focus), "Barangay Poblacion 7")

    def test_lookup_is_qualified_by_municipality(self):
        midsayap = barangay_centroid("Midsayap", "Barangay Poblacion 1")
        pigcawayan = barangay_centroid("Pigcawayan", "Poblacion I")
        self.assertIsNotNone(midsayap)
        self.assertIsNotNone(pigcawayan)
        self.assertNotEqual(midsayap, pigcawayan)

    def test_dualing_focus_uses_aleosan_reference(self):
        focus = barangay_centroid("Aleosan", "Dualing")
        self.assertEqual(focus, (7.148669, 124.565148))


if __name__ == "__main__":
    unittest.main()
