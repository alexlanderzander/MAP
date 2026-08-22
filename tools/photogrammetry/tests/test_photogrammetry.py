import argparse
import gzip
import importlib.util
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / 'prepare_photogrammetry.py'
spec = importlib.util.spec_from_file_location('prepare_photogrammetry', MODULE_PATH)
photo = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = photo
assert spec.loader
spec.loader.exec_module(photo)


def write_semantic_tile(path: Path, building_id=4242):
    ce, cn = 391750.0, 5820750.0
    pts = [(391590.0, 5820340.0), (391610.0, 5820340.0), (391610.0, 5820360.0), (391590.0, 5820360.0)]
    scale = 0.02
    raw = bytearray(photo.BWT_HEADER.pack(b'BWT1', 2, 2, 500, 0, 783, 11641, ce, cn, 1, 0, 0))
    raw += photo.BWT_BUILDING_V2.pack(building_id, 1000, 0, 0, 1, len(pts), 3, 1, 0, 0, 0)
    for x, z in pts:
        raw += photo.BWT_POINT.pack(round((x-ce)/scale), round((z-cn)/scale))
    path.write_bytes(gzip.compress(bytes(raw), compresslevel=9, mtime=0))


def write_obj(folder: Path):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'wall.jpg').write_bytes(b'fake-jpeg-payload')
    (folder / 'test.mtl').write_text('newmtl wall\nKd 0.8 0.7 0.6\nmap_Kd wall.jpg\n', encoding='utf-8')
    (folder / 'test.obj').write_text('''mtllib test.mtl
v 391590 5820340 35
v 391610 5820340 35
v 391610 5820360 35
v 391590 5820340 36
v 391610 5820340 36
v 391600 5820350 45
vt 0 0
vt 1 0
vt 1 1
vn 0 0 1
usemtl wall
f 1/1/1 2/2/1 3/3/1
f 4/1/1 5/2/1 6/3/1
''', encoding='utf-8')


class PhotogrammetryTests(unittest.TestCase):
    def test_axis_detection_and_handedness(self):
        vertices = [(391600.0, 5820350.0, 35.0), (391700.0, 5820450.0, 60.0)]
        self.assertEqual(photo.detect_axis(vertices), 'xyz')
        self.assertTrue(photo.axis_winding_flipped('xyz'))
        self.assertFalse(photo.axis_winding_flipped('xzy'))
        self.assertEqual(photo.transform_point(vertices[0], 'xyz', 391500, 5820500, 35), (100.0, 0.0, -150.0))

    def test_pack_preserves_source_mesh_and_binds_building(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); source = root / 'source'; semantic = root / 'semantic'; out = root / 'out'
            write_obj(source); semantic.mkdir(); write_semantic_tile(semantic / 'tile_783_11641.bwt.gz')
            args = argparse.Namespace(input=str(source), out=str(out), semantic_tiles=str(semantic), axis='auto', origin_e=391500.0, origin_n=5820500.0, base_elevation=35.0, input_origin_e=None, input_origin_n=None, area_bbox=photo.AREA_BBOX, clean=True)
            self.assertEqual(photo.build(args), 0)
            manifest = json.loads((out / 'photogrammetry_manifest.json').read_text())
            self.assertEqual(manifest['format'], 'BWM1'); self.assertEqual(manifest['axisMapping'], 'xyz')
            self.assertEqual(manifest['chunks'][0]['triangles'], 2); self.assertEqual(manifest['chunks'][0]['owners'], 1)
            self.assertTrue(manifest['chunks'][0]['materials'][0]['texture'].startswith('Textures/'))
            raw = gzip.decompress((out / 'chunk_0000.bwm.gz').read_bytes()); header = photo.BWM_HEADER.unpack_from(raw, 0)
            self.assertEqual(header[0], b'BWM1'); self.assertEqual(header[1], 1); self.assertEqual(header[3], 6); self.assertEqual(header[5], 1)
            offset = photo.BWM_HEADER.size + header[3] * photo.BWM_VERTEX.size
            self.assertEqual(struct.unpack_from('<Q', raw, offset)[0], 4242); offset += 8
            _, index_count = photo.BWM_SUBMESH.unpack_from(raw, offset); offset += photo.BWM_SUBMESH.size + index_count * 4
            owner_count = struct.unpack_from('<I', raw, offset)[0]; offset += 4
            self.assertEqual(struct.unpack_from(f'<{owner_count}H', raw, offset), (0, 1))

    def test_zip_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); archive = root / 'bad.zip'
            with zipfile.ZipFile(archive, 'w') as zf: zf.writestr('../escape.obj', 'v 0 0 0\nf 1 1 1\n')
            with self.assertRaisesRegex(ValueError, 'unsafe path'): photo.collect_sources(archive, root / 'unpack')


if __name__ == '__main__': unittest.main()
