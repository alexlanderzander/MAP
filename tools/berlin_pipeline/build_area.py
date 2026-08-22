from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from cli import pack
from normalize import normalize_buildings, normalize_roads, normalize_trees
from wfs import SOURCES, WfsClient, WfsError


def load_area(path: str) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    bbox = data.get("bbox")
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise ValueError("area bbox must be [minE,minN,maxE,maxN]")
    values = tuple(float(v) for v in bbox)
    if values[2] <= values[0] or values[3] <= values[1]:
        raise ValueError("invalid area bbox")
    data["bbox"] = values
    return data


def build(args: argparse.Namespace) -> int:
    area = load_area(args.area)
    bbox = area["bbox"]
    client = WfsClient(timeout=args.timeout, retries=args.retries, page_size=args.page_size)
    normalizers = {"buildings": normalize_buildings, "trees": normalize_trees}
    normalized: dict[str, dict] = {}
    report_sources: list[dict] = []

    for kind in ("buildings", "roads", "trees"):
        source = SOURCES[kind]
        print(f"Fetching {kind} from {source.endpoint} ...")
        type_name, raw = client.fetch_source(source, bbox)
        cooked = normalize_roads(raw, bbox, args.tile_size) if kind == "roads" else normalizers[kind](raw, bbox)
        normalized[kind] = cooked
        report_sources.append({
            "kind": kind,
            "sourceId": source.id,
            "endpoint": source.endpoint,
            "featureType": type_name,
            "rawFeatures": len(raw.get("features") or []),
            "normalizedFeatures": len(cooked.get("features") or []),
            "license": "DL-DE-Zero-2.0",
        })
        print(f"  {len(raw.get('features') or [])} raw -> {len(cooked.get('features') or [])} normalized")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="berlin-world-") as tmp_name:
        tmp = Path(tmp_name)
        paths = {}
        for kind, payload in normalized.items():
            path = tmp / f"{kind}.geojson"
            path.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
            paths[kind] = path
        pack_args = argparse.Namespace(
            buildings=str(paths["buildings"]),
            roads=str(paths["roads"]),
            trees=str(paths["trees"]),
            out=str(out),
            tile_size=args.tile_size,
            level=args.level,
        )
        pack(pack_args)

    source_manifest = {
        "areaId": area.get("id"),
        "areaName": area.get("name"),
        "crs": area.get("crs", "EPSG:25833"),
        "bbox": list(bbox),
        "retrievedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sources": report_sources,
        "notes": "Raw WFS responses were processed in a temporary directory and are not part of the game build.",
    }
    (out / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download an official Berlin validation area and pack it directly into compact BWT1 Unity tiles"
    )
    parser.add_argument("--area", default="DataSources/hackescher_markt_area.json")
    parser.add_argument("--out", default="GeneratedBerlin/HackescherMarkt/Tiles")
    parser.add_argument("--tile-size", type=int, default=500, choices=range(100, 601))
    parser.add_argument("--level", type=int, default=9, choices=range(1, 10))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--page-size", type=int, default=5000)
    args = parser.parse_args()
    try:
        return build(args)
    except WfsError as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
