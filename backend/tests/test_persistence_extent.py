"""A recurring hotspot is an area with a magnitude, not a pin.

The map reduced every chain to its latest centroid, so a hotspot holding 493
incidents across ten years drew identically to one holding 8 in a single year.
These cover the extent hull and the member count that fix that.
"""
import unittest

from shapely.geometry import shape

from app.services.persistence_service import _build_chains, chain_extent


class ChainExtentTests(unittest.TestCase):
    def test_extent_covers_every_member_point(self):
        points = [(7.10, 124.70), (7.12, 124.72), (7.11, 124.75), (7.09, 124.71)]
        polygon = shape(chain_extent(points))
        self.assertEqual(polygon.geom_type, "Polygon")
        for lat, lon in points:
            with self.subTest(point=(lat, lon)):
                self.assertTrue(
                    polygon.covers(shape({"type": "Point", "coordinates": [lon, lat]})),
                    "the hull must contain the incidents it was built from",
                )

    def test_coincident_points_still_produce_a_drawable_area(self):
        polygon = shape(chain_extent([(7.10, 124.70)] * 5))
        self.assertEqual(polygon.geom_type, "Polygon")
        self.assertGreater(polygon.area, 0)

    def test_no_points_yields_no_extent(self):
        self.assertIsNone(chain_extent([]))

    def test_chain_accumulates_points_and_ids_across_periods(self):
        """A chain spanning several years must carry every year's members, so
        its extent and count describe the whole chain rather than its last
        period alone."""
        tight = [(7.100, 124.700), (7.101, 124.701), (7.102, 124.702), (7.103, 124.703)]
        drifted = [(7.104, 124.704), (7.105, 124.705), (7.106, 124.706), (7.107, 124.707)]
        chains = _build_chains(
            points_by_year={2020: tight, 2021: drifted},
            ids_by_year={2020: [1, 2, 3, 4], 2021: [5, 6, 7, 8]},
            all_years=[2020, 2021],
            eps_km=1.0,
            min_samples=4,
            match_distance_km=1.5,
        )
        self.assertEqual(len(chains), 1, "both years should match into one chain")
        chain = chains[0]
        self.assertEqual(sorted(chain["incident_ids"]), [1, 2, 3, 4, 5, 6, 7, 8])
        self.assertEqual(len(chain["points"]), 8)

        polygon = shape(chain_extent(chain["points"]))
        for lat, lon in tight + drifted:
            self.assertTrue(polygon.covers(shape({"type": "Point", "coordinates": [lon, lat]})))


if __name__ == "__main__":
    unittest.main()
