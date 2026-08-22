import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from normalize import normalize_buildings, normalize_roads, normalize_trees

BBOX = (391000.0, 5820000.0, 392000.0, 5821000.0)


class NormalizeTests(unittest.TestCase):
    def test_alkis_storeys_become_height_and_class(self):
        fc = {"features": [{
            "id": "g1",
            "properties": {"aog": 5, "bezgfk": "Wohngebäude"},
            "geometry": {"type": "Polygon", "coordinates": [[
                [391100, 5820100], [391120, 5820100], [391120, 5820120],
                [391100, 5820120], [391100, 5820100],
            ]]},
        }]}
        out = normalize_buildings(fc, BBOX)["features"][0]
        self.assertAlmostEqual(out["properties"]["height"], 16.8)
        self.assertEqual(out["properties"]["class"], "residential")

    def test_outside_building_filtered(self):
        fc = {"features": [{
            "properties": {},
            "geometry": {"type": "Polygon", "coordinates": [[
                [390900, 5820100], [390920, 5820100], [390920, 5820120],
                [390900, 5820120], [390900, 5820100],
            ]]},
        }]}
        self.assertEqual(normalize_buildings(fc, BBOX)["features"], [])

    def test_long_road_is_clipped_and_split_on_500m_tiles(self):
        fc = {"features": [{
            "id": "r",
            "properties": {"okstra_klasse": "G"},
            "geometry": {"type": "LineString", "coordinates": [
                [390000, 5820500], [393000, 5820500],
            ]},
        }]}
        roads = normalize_roads(fc, BBOX)["features"]
        self.assertEqual(len(roads), 2)
        self.assertEqual(roads[0]["geometry"]["coordinates"][0], [391000.0, 5820500.0])
        self.assertEqual(roads[-1]["geometry"]["coordinates"][-1], [392000.0, 5820500.0])

    def test_tree_fields(self):
        fc = {"features": [{
            "id": "t",
            "properties": {"baumhoehe": "9,5", "kronedurch": 4, "art_dtsch": "Linde"},
            "geometry": {"type": "Point", "coordinates": [391500, 5820500]},
        }]}
        tree = normalize_trees(fc, BBOX)["features"][0]
        self.assertEqual(tree["properties"]["height"], 9.5)
        self.assertGreater(tree["properties"]["species_code"], 0)


if __name__ == "__main__":
    unittest.main()
