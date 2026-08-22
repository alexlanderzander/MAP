import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from osm import normalize_osm, wgs84_to_utm33

BBOX = (391000.0, 5820000.0, 392000.0, 5821000.0)


class OsmFallbackTests(unittest.TestCase):
    def test_wgs84_to_utm33_hackescher_markt(self):
        e, n = wgs84_to_utm33(13.4022, 52.5226)
        self.assertAlmostEqual(e, 391595.69, delta=0.25)
        self.assertAlmostEqual(n, 5820365.54, delta=0.25)

    def test_normalize_small_osm_payload(self):
        payload = {"elements": [
            {
                "type": "way", "id": 10,
                "tags": {"building": "apartments", "building:levels": "5", "roof:shape": "gabled"},
                "geometry": [
                    {"lon": 13.4000, "lat": 52.5230}, {"lon": 13.4003, "lat": 52.5230},
                    {"lon": 13.4003, "lat": 52.5232}, {"lon": 13.4000, "lat": 52.5232},
                    {"lon": 13.4000, "lat": 52.5230},
                ],
            },
            {
                "type": "way", "id": 11,
                "tags": {"highway": "residential", "lanes": "2"},
                "geometry": [
                    {"lon": 13.3970, "lat": 52.5230}, {"lon": 13.4050, "lat": 52.5230},
                ],
            },
            {
                "type": "node", "id": 12, "lon": 13.4010, "lat": 52.5232,
                "tags": {"natural": "tree", "height": "11.5", "species": "Tilia cordata"},
            },
        ]}
        layers = normalize_osm(payload, BBOX)
        self.assertEqual(len(layers["buildings"]["features"]), 1)
        building = layers["buildings"]["features"][0]
        self.assertEqual(building["properties"]["class"], "residential")
        self.assertEqual(building["properties"]["roof_type"], "gabled")
        self.assertAlmostEqual(building["properties"]["height"], 16.8)
        self.assertGreaterEqual(len(layers["roads"]["features"]), 1)
        self.assertEqual(len(layers["trees"]["features"]), 1)


if __name__ == "__main__":
    unittest.main()
