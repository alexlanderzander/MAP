from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean

from format import Building, Road, Tree, Tile, BUILDING_CLASSES, ROAD_CLASSES, ROOF_TYPES, enum_value, encode_tile_gzip, stable_id, tile_center, tile_index


def load_geojson(path: str | None) -> dict:
    if not path:
        return {"type": "FeatureCollection", "features": []}
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if data.get("type") != "FeatureCollection":
        raise ValueError(f"{path}: expected GeoJSON FeatureCollection")
    return data


def polygon_outer(geometry: dict) -> list[tuple[float, float]]:
    gtype = geometry.get("type")
    coords = geometry.get("coordinates", [])
    if gtype == "Polygon":
        ring = coords[0] if coords else []
    elif gtype == "MultiPolygon":
        rings = [poly[0] for poly in coords if poly]
        ring = max(rings, key=len) if rings else []
    else:
        return []
    pts = [(float(p[0]), float(p[1])) for p in ring]
    if len(pts) >= 2 and pts[0] == pts[-1]:
        pts.pop()
    return pts


def line_points(geometry: dict) -> list[tuple[float, float]]:
    if geometry.get("type") != "LineString":
        return []
    return [(float(p[0]), float(p[1])) for p in geometry.get("coordinates", [])]


def point_xy(geometry: dict) -> tuple[float, float] | None:
    if geometry.get("type") != "Point":
        return None
    c = geometry.get("coordinates", [])
    return (float(c[0]), float(c[1])) if len(c) >= 2 else None


def feature_id(feature: dict, fallback: str) -> int:
    props = feature.get("properties") or {}
    return stable_id(feature.get("id", props.get("id", fallback)))


def centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
    return mean(p[0] for p in points), mean(p[1] for p in points)


def pack(args: argparse.Namespace) -> int:
    tile_size = args.tile_size
    buckets: dict[tuple[int, int], dict[str, list]] = defaultdict(lambda: {"buildings": [], "roads": [], "trees": []})

    for idx, feature in enumerate(load_geojson(args.buildings)["features"]):
        pts = polygon_outer(feature.get("geometry") or {})
        if len(pts) < 3:
            continue
        props = feature.get("properties") or {}
        key = tile_index(*centroid(pts), tile_size)
        buckets[key]["buildings"].append(Building(
            feature_id(feature, f"building-{idx}"), pts,
            float(props.get("height", props.get("measuredHeight", 12.0))),
            float(props.get("min_height", 0.0)),
            enum_value(props.get("roof_type", "flat"), ROOF_TYPES),
            enum_value(props.get("class", "unknown"), BUILDING_CLASSES),
        ))

    for idx, feature in enumerate(load_geojson(args.roads)["features"]):
        pts = line_points(feature.get("geometry") or {})
        if len(pts) < 2:
            continue
        props = feature.get("properties") or {}
        key = tile_index(*centroid(pts), tile_size)
        buckets[key]["roads"].append(Road(
            feature_id(feature, f"road-{idx}"), pts,
            float(props.get("width", 7.0)), int(props.get("lanes", 1)),
            enum_value(props.get("class", "unknown"), ROAD_CLASSES),
        ))

    for idx, feature in enumerate(load_geojson(args.trees)["features"]):
        point = point_xy(feature.get("geometry") or {})
        if point is None:
            continue
        props = feature.get("properties") or {}
        key = tile_index(point[0], point[1], tile_size)
        buckets[key]["trees"].append(Tree(
            feature_id(feature, f"tree-{idx}"), point[0], point[1],
            float(props.get("height", 8.0)), float(props.get("crown", 4.0)), int(props.get("species_code", 0)),
        ))

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"format": "BWT1", "crs": "EPSG:25833", "tileSizeM": tile_size, "quantizationCm": 2, "compression": "gzip", "tiles": []}
    total_bytes = 0
    total_features = 0

    for (tx, tz), bucket in sorted(buckets.items()):
        ce, cn = tile_center(tx, tz, tile_size)
        tile = Tile(tx, tz, tile_size, ce, cn, bucket["buildings"], bucket["roads"], bucket["trees"])
        payload = encode_tile_gzip(tile, compresslevel=args.level)
        filename = f"tile_{tx}_{tz}.bwt.gz"
        (out / filename).write_bytes(payload)
        count = sum(len(bucket[k]) for k in ("buildings", "roads", "trees"))
        total_bytes += len(payload)
        total_features += count
        manifest["tiles"].append({"x": tx, "z": tz, "file": filename, "bytes": len(payload), "buildings": len(bucket["buildings"]), "roads": len(bucket["roads"]), "trees": len(bucket["trees"])})

    manifest["totalBytes"] = total_bytes
    manifest["totalFeatures"] = total_features
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Packed {len(manifest['tiles'])} tiles, {total_features} features, {total_bytes:,} bytes")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Pack Berlin EPSG:25833 GeoJSON into compact BWT1 Unity tiles")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("pack")
    p.add_argument("--buildings")
    p.add_argument("--roads")
    p.add_argument("--trees")
    p.add_argument("--out", required=True)
    p.add_argument("--tile-size", type=int, default=500, choices=range(100, 601))
    p.add_argument("--level", type=int, default=9, choices=range(1, 10))
    p.set_defaults(func=pack)
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
