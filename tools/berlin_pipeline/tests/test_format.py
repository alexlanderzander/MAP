import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from format import Building, Road, Tile, Tree, decode_tile_gzip, encode_tile_gzip, tile_center, tile_index


class BwtFormatTests(unittest.TestCase):
    def test_roundtrip(self):
        tx, tz = tile_index(392100.0, 5820100.0, 500)
        ce, cn = tile_center(tx, tz, 500)
        tile = Tile(tx, tz, 500, ce, cn,
            buildings=[Building(1, [(392090, 5820090), (392110, 5820090), (392110, 5820110), (392090, 5820110)], 18.42)],
            roads=[Road(2, [(392050, 5820080), (392150, 5820120)], 7.5, 2, 6)],
            trees=[Tree(3, 392120, 5820100, 11.2, 5.4, 10)])
        decoded = decode_tile_gzip(encode_tile_gzip(tile))
        self.assertEqual(decoded.tile_x, tx)
        self.assertAlmostEqual(decoded.buildings[0].height_m, 18.42, places=2)
        self.assertAlmostEqual(decoded.roads[0].width_m, 7.5, places=2)
        self.assertAlmostEqual(decoded.trees[0].height_m, 11.2, places=2)

    def test_compact_representation_is_far_smaller_than_mesh_storage(self):
        tx, tz = tile_index(392000, 5820000, 500)
        ce, cn = tile_center(tx, tz, 500)
        buildings = []
        for i in range(150):
            x = ce - 200 + (i % 15) * 25
            z = cn - 200 + (i // 15) * 35
            buildings.append(Building(i, [(x,z), (x+18,z), (x+18,z+24), (x,z+24)], 15 + (i % 5) * 3))
        packed = encode_tile_gzip(Tile(tx, tz, 500, ce, cn, buildings=buildings))
        conservative_mesh_bytes = len(buildings) * (24 * 32 + 36 * 4)
        self.assertLess(len(packed), conservative_mesh_bytes * 0.05)

    def test_out_of_range_feature_is_rejected(self):
        tile = Tile(0, 0, 500, 250, 250, buildings=[Building(1, [(1000,1000), (1001,1000), (1001,1001)], 10)])
        with self.assertRaises(ValueError):
            encode_tile_gzip(tile)


if __name__ == "__main__":
    unittest.main()
