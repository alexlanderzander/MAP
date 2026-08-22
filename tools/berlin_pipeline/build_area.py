from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import tempfile

from cli import pack
from normalize import normalize_buildings, normalize_roads, normalize_trees
from osm import OsmError, OverpassClient, normalize_osm
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
    wgs = data.get("bboxWgs84")
    if wgs is not None:
        if not isinstance(wgs, list) or len(wgs) != 4:
            raise ValueError("area bboxWgs84 must be [west,south,east,north]")
        data["bboxWgs84"] = tuple(float(v) for v in wgs)
    return data


def fetch_official(args: argparse.Namespace, bbox) -> tuple[dict[str, dict], list[dict]]:
    client = WfsClient(timeout=args.timeout, retries=args.retries, page_size=args.page_size)
    normalizers = {"buildings": normalize_buildings, "trees": normalize_trees}
    normalized: dict[str, dict] = {}
    report_sources: list[dict] = []
    for kind in ("buildings", "roads", "trees"):
        source = SOURCES[kind]
        print(f"Fetching official {kind} from {source.endpoint} ...")
        type_name, raw = client.fetch_source(source, bbox)
        cooked = normalize_roads(raw, bbox, args.tile_size) if kind == "roads" else normalizers[kind](raw, bbox)
        count = len(cooked.get("features") or [])
        if count == 0:
            raise WfsError(f"Official {kind} source returned no usable features for this central-Berlin area")
        normalized[kind] = cooked
        report_sources.append({
            "kind": kind,
            "sourceId": source.id,
            "endpoint": source.endpoint,
            "featureType": type_name,
            "rawFeatures": len(raw.get("features") or []),
            "normalizedFeatures": count,
            "license": "DL-DE-Zero-2.0",
        })
        print(f"  {len(raw.get('features') or [])} raw -> {count} normalized")
    return normalized, report_sources


def fetch_osm(args: argparse.Namespace, area: dict, bbox) -> tuple[dict[str, dict], list[dict]]:
    wgs = area.get("bboxWgs84")
    if not wgs:
        raise OsmError("OSM fallback requires bboxWgs84 in the area definition")
    print("Fetching current OpenStreetMap fallback through Overpass ...")
    endpoint, payload = OverpassClient(timeout=max(args.timeout, 45.0), retries=args.retries).fetch(wgs)
    normalized = normalize_osm(payload, bbox, args.tile_size)
    counts = {kind: len(fc.get("features") or []) for kind, fc in normalized.items()}
    if counts["buildings"] == 0 or counts["roads"] == 0:
        raise OsmError(f"OSM fallback produced an implausible empty core layer: {counts}")
    print(f"  OSM -> {counts['buildings']} buildings, {counts['roads']} road parts, {counts['trees']} trees")
    report_sources = [{
        "kind": "buildings+roads+trees",
        "sourceId": "openstreetmap-overpass",
        "endpoint": endpoint,
        "rawElements": len(payload.get("elements") or []),
        "normalizedFeatures": counts,
        "license": "ODbL-1.0",
        "attribution": "© OpenStreetMap contributors",
        "statusNote": "Fallback used because official Berlin WFS services were unavailable or unusable. For city-scale production prefer a regional OSM extract over repeated public Overpass queries.",
    }]
    return normalized, report_sources


def build(args: argparse.Namespace) -> int:
    area = load_area(args.area)
    bbox = area["bbox"]
    normalized: dict[str, dict]
    report_sources: list[dict]
    source_mode = args.source
    official_error = None

    if source_mode in {"auto", "official"}:
        try:
            normalized, report_sources = fetch_official(args, bbox)
            source_mode = "official"
        except WfsError as exc:
            official_error = str(exc)
            if args.source == "official":
                raise
            print(f"Official Berlin WFS unavailable; switching to OSM fallback. Reason: {exc}")
            normalized, report_sources = fetch_osm(args, area, bbox)
            source_mode = "osm-fallback"
    else:
        normalized, report_sources = fetch_osm(args, area, bbox)
        source_mode = "osm"

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
        "sourceMode": source_mode,
        "retrievedAtUtc": datetime.now(timezone.utc).isoformat(),
        "sources": report_sources,
        "officialFailure": official_error,
        "notes": "Raw network responses were processed transiently and are not part of the game build. Inspect license/attribution fields before distributing generated data.",
    }
    (out / "source_manifest.json").write_text(json.dumps(source_manifest, indent=2) + "\n", encoding="utf-8")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Download the Hackescher Markt Berlin validation area and pack it directly into compact BWT1 Unity tiles"
    )
    parser.add_argument("--area", default="DataSources/hackescher_markt_area.json")
    parser.add_argument("--out", default="GeneratedBerlin/HackescherMarkt/Tiles")
    parser.add_argument("--source", choices=("auto", "official", "osm"), default="auto",
                        help="auto prefers official Berlin WFS and falls back to OSM if Berlin services are under maintenance")
    parser.add_argument("--tile-size", type=int, default=500, choices=range(100, 601))
    parser.add_argument("--level", type=int, default=9, choices=range(1, 10))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--page-size", type=int, default=5000)
    args = parser.parse_args()
    try:
        return build(args)
    except (WfsError, OsmError, ValueError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
