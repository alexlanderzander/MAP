from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import hashlib
import io
import math
import struct

MAGIC = b"BWT1"
VERSION = 1
QUANT_CM = 2
MAX_Q = 32767
MIN_Q = -32768
HEADER = struct.Struct("<4sHHHHii2dIII")
BUILDING_HEADER = struct.Struct("<QHHBBH")
ROAD_HEADER = struct.Struct("<QBBHH")
TREE = struct.Struct("<QhhHHH")
POINT = struct.Struct("<hh")

BUILDING_CLASSES = {"unknown": 0, "residential": 1, "commercial": 2, "industrial": 3, "public": 4, "historic": 5}
ROOF_TYPES = {"flat": 0, "gabled": 1, "hipped": 2, "mansard": 3, "shed": 4}
ROAD_CLASSES = {"unknown": 0, "motorway": 1, "trunk": 2, "primary": 3, "secondary": 4, "tertiary": 5, "residential": 6, "service": 7, "footway": 8, "cycleway": 9, "tram": 10}


def stable_id(value: object) -> int:
    if isinstance(value, int):
        return value & 0xFFFFFFFFFFFFFFFF
    return int.from_bytes(hashlib.blake2b(str(value).encode("utf-8"), digest_size=8).digest(), "little")


def enum_value(value: object, mapping: dict[str, int]) -> int:
    if isinstance(value, int):
        if 0 <= value <= 255:
            return value
        raise ValueError(f"enum integer out of byte range: {value}")
    return mapping.get(str(value).lower(), 0)


def q_meters(value_m: float) -> int:
    q = int(round(value_m * 100.0 / QUANT_CM))
    if not MIN_Q <= q <= MAX_Q:
        raise ValueError(f"coordinate delta {value_m:.2f} m exceeds BWT1 quantization range")
    return q


def uq_height(value_m: float) -> int:
    q = int(round(max(0.0, value_m) * 100.0 / QUANT_CM))
    if q > 65535:
        raise ValueError(f"height {value_m:.2f} m exceeds BWT1 range")
    return q


@dataclass(slots=True)
class Building:
    feature_id: int
    footprint: list[tuple[float, float]]
    height_m: float
    min_height_m: float = 0.0
    roof_type: int = 0
    building_class: int = 0


@dataclass(slots=True)
class Road:
    feature_id: int
    points: list[tuple[float, float]]
    width_m: float
    lanes: int = 1
    road_class: int = 0


@dataclass(slots=True)
class Tree:
    feature_id: int
    x_m: float
    z_m: float
    height_m: float = 8.0
    crown_m: float = 4.0
    species_code: int = 0


@dataclass(slots=True)
class Tile:
    tile_x: int
    tile_z: int
    tile_size_m: int
    center_easting_m: float
    center_northing_m: float
    buildings: list[Building] = field(default_factory=list)
    roads: list[Road] = field(default_factory=list)
    trees: list[Tree] = field(default_factory=list)


def _pack_local_point(buf: io.BytesIO, x_m: float, z_m: float, tile: Tile) -> None:
    buf.write(POINT.pack(q_meters(x_m - tile.center_easting_m), q_meters(z_m - tile.center_northing_m)))


def encode_tile(tile: Tile) -> bytes:
    if not 1 <= tile.tile_size_m <= 600:
        raise ValueError("tile size must be 1..600 m for BWT1")
    buf = io.BytesIO()
    buf.write(HEADER.pack(MAGIC, VERSION, QUANT_CM, tile.tile_size_m, 0, tile.tile_x, tile.tile_z, tile.center_easting_m, tile.center_northing_m, len(tile.buildings), len(tile.roads), len(tile.trees)))
    for b in tile.buildings:
        if len(b.footprint) < 3 or len(b.footprint) > 65535:
            raise ValueError("building footprint must contain 3..65535 vertices")
        buf.write(BUILDING_HEADER.pack(b.feature_id, uq_height(b.height_m), uq_height(b.min_height_m), b.roof_type, b.building_class, len(b.footprint)))
        for x, z in b.footprint:
            _pack_local_point(buf, x, z, tile)
    for r in tile.roads:
        if len(r.points) < 2 or len(r.points) > 65535:
            raise ValueError("road must contain 2..65535 points")
        buf.write(ROAD_HEADER.pack(r.feature_id, r.road_class, max(0, min(255, int(r.lanes))), uq_height(r.width_m), len(r.points)))
        for x, z in r.points:
            _pack_local_point(buf, x, z, tile)
    for t in tile.trees:
        buf.write(TREE.pack(t.feature_id, q_meters(t.x_m - tile.center_easting_m), q_meters(t.z_m - tile.center_northing_m), uq_height(t.height_m), uq_height(t.crown_m), max(0, min(65535, int(t.species_code)))))
    return buf.getvalue()


def encode_tile_gzip(tile: Tile, compresslevel: int = 9) -> bytes:
    return gzip.compress(encode_tile(tile), compresslevel=compresslevel, mtime=0)


def _read_exact(stream: io.BytesIO, size: int) -> bytes:
    data = stream.read(size)
    if len(data) != size:
        raise ValueError("truncated BWT1 tile")
    return data


def decode_tile(data: bytes) -> Tile:
    stream = io.BytesIO(data)
    magic, version, quant_cm, tile_size, _reserved, tx, tz, ce, cn, bc, rc, tc = HEADER.unpack(_read_exact(stream, HEADER.size))
    if magic != MAGIC or version != VERSION or quant_cm != QUANT_CM:
        raise ValueError("unsupported BWT1 tile")
    tile = Tile(tx, tz, tile_size, ce, cn)
    scale = quant_cm / 100.0
    for _ in range(bc):
        fid, hq, mhq, roof, cls, count = BUILDING_HEADER.unpack(_read_exact(stream, BUILDING_HEADER.size))
        pts = [(ce + POINT.unpack(_read_exact(stream, POINT.size))[0] * scale, 0.0) for _ in range(0)]
        pts = []
        for _ in range(count):
            qx, qz = POINT.unpack(_read_exact(stream, POINT.size))
            pts.append((ce + qx * scale, cn + qz * scale))
        tile.buildings.append(Building(fid, pts, hq * scale, mhq * scale, roof, cls))
    for _ in range(rc):
        fid, cls, lanes, widthq, count = ROAD_HEADER.unpack(_read_exact(stream, ROAD_HEADER.size))
        pts = []
        for _ in range(count):
            qx, qz = POINT.unpack(_read_exact(stream, POINT.size))
            pts.append((ce + qx * scale, cn + qz * scale))
        tile.roads.append(Road(fid, pts, widthq * scale, lanes, cls))
    for _ in range(tc):
        fid, qx, qz, hq, cq, species = TREE.unpack(_read_exact(stream, TREE.size))
        tile.trees.append(Tree(fid, ce + qx * scale, cn + qz * scale, hq * scale, cq * scale, species))
    if stream.read(1):
        raise ValueError("unexpected trailing bytes in BWT1 tile")
    return tile


def decode_tile_gzip(data: bytes) -> Tile:
    return decode_tile(gzip.decompress(data))


def tile_index(x_m: float, z_m: float, tile_size_m: int) -> tuple[int, int]:
    return math.floor(x_m / tile_size_m), math.floor(z_m / tile_size_m)


def tile_center(tx: int, tz: int, tile_size_m: int) -> tuple[float, float]:
    return (tx + 0.5) * tile_size_m, (tz + 0.5) * tile_size_m
