from __future__ import annotations

import json
import math
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from format import stable_id
from normalize import clip_line, split_line_to_tiles


OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)


class OsmError(RuntimeError):
    pass


def wgs84_to_utm33(lon_deg: float, lat_deg: float) -> tuple[float, float]:
    """WGS84 -> EPSG:25833/UTM zone 33N, accurate to far below game-map precision."""
    a = 6378137.0
    ecc_sq = 0.0066943799901413165
    k0 = 0.9996
    ecc_prime_sq = ecc_sq / (1.0 - ecc_sq)
    lat = math.radians(lat_deg)
    lon = math.radians(lon_deg)
    lon_origin = math.radians(15.0)
    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    tan_lat = math.tan(lat)
    n = a / math.sqrt(1.0 - ecc_sq * sin_lat * sin_lat)
    t = tan_lat * tan_lat
    c = ecc_prime_sq * cos_lat * cos_lat
    aa = cos_lat * (lon - lon_origin)
    e2 = ecc_sq * ecc_sq
    e3 = e2 * ecc_sq
    m = a * (
        (1.0 - ecc_sq / 4.0 - 3.0 * e2 / 64.0 - 5.0 * e3 / 256.0) * lat
        - (3.0 * ecc_sq / 8.0 + 3.0 * e2 / 32.0 + 45.0 * e3 / 1024.0) * math.sin(2.0 * lat)
        + (15.0 * e2 / 256.0 + 45.0 * e3 / 1024.0) * math.sin(4.0 * lat)
        - (35.0 * e3 / 3072.0) * math.sin(6.0 * lat)
    )
    easting = k0 * n * (
        aa
        + (1.0 - t + c) * aa**3 / 6.0
        + (5.0 - 18.0 * t + t * t + 72.0 * c - 58.0 * ecc_prime_sq) * aa**5 / 120.0
    ) + 500000.0
    northing = k0 * (
        m
        + n * tan_lat * (
            aa * aa / 2.0
            + (5.0 - t + 9.0 * c + 4.0 * c * c) * aa**4 / 24.0
            + (61.0 - 58.0 * t + t * t + 600.0 * c - 330.0 * ecc_prime_sq) * aa**6 / 720.0
        )
    )
    return easting, northing


def _number(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", str(value))
    if not match:
        return default
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return default


def _utm_geometry(geometry: list[dict]) -> list[list[float]]:
    result = []
    for p in geometry or []:
        if "lon" in p and "lat" in p:
            e, n = wgs84_to_utm33(float(p["lon"]), float(p["lat"]))
            result.append([e, n])
    return result


def _centroid(points: list[list[float]]) -> tuple[float, float]:
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def _inside(x: float, y: float, bbox) -> bool:
    return bbox[0] <= x < bbox[2] and bbox[1] <= y < bbox[3]


def _building_class(tags: dict) -> str:
    value = str(tags.get("building", "")).casefold()
    if value in {"apartments", "residential", "house", "detached", "terrace", "dormitory"}:
        return "residential"
    if value in {"commercial", "retail", "office", "hotel"}:
        return "commercial"
    if value in {"industrial", "warehouse", "factory"}:
        return "industrial"
    if value in {"civic", "public", "school", "university", "hospital", "church", "cathedral", "government"}:
        return "public"
    return "unknown"


ROOF_MAP = {
    "flat": "flat",
    "gabled": "gabled",
    "gable": "gabled",
    "hipped": "hipped",
    "hip": "hipped",
    "mansard": "mansard",
    "skillion": "shed",
    "shed": "shed",
}


def _building_properties(tags: dict) -> dict:
    height = _number(tags.get("height"), 0.0)
    levels = _number(tags.get("building:levels"), 0.0)
    if height <= 0.0:
        height = max(3.6, levels * 3.2 + 0.8) if levels > 0.0 else 12.0
    min_height = _number(tags.get("min_height"), 0.0)
    roof = ROOF_MAP.get(str(tags.get("roof:shape", "flat")).casefold(), "flat")
    return {
        "height": round(height, 2),
        "min_height": round(max(0.0, min_height), 2),
        "roof_type": roof,
        "class": _building_class(tags),
        "source": "OpenStreetMap",
    }


def _road_class(tags: dict) -> str:
    if tags.get("railway") == "tram":
        return "tram"
    highway = str(tags.get("highway", "")).casefold()
    if highway in {"motorway", "motorway_link"}:
        return "motorway"
    if highway in {"trunk", "trunk_link"}:
        return "trunk"
    if highway in {"primary", "primary_link"}:
        return "primary"
    if highway in {"secondary", "secondary_link"}:
        return "secondary"
    if highway in {"tertiary", "tertiary_link"}:
        return "tertiary"
    if highway in {"service", "track"}:
        return "service"
    if highway in {"cycleway"}:
        return "cycleway"
    if highway in {"footway", "pedestrian", "path", "steps"}:
        return "footway"
    return "residential"


ROAD_WIDTHS = {
    "motorway": 20.0,
    "trunk": 14.0,
    "primary": 12.0,
    "secondary": 10.0,
    "tertiary": 8.0,
    "residential": 6.5,
    "service": 4.0,
    "footway": 2.5,
    "cycleway": 2.2,
    "tram": 3.0,
}


def _stitch_outer_relation(element: dict) -> list[list[float]]:
    segments = []
    for member in element.get("members") or []:
        if member.get("type") != "way" or member.get("role", "outer") not in ("", "outer"):
            continue
        pts = _utm_geometry(member.get("geometry") or [])
        if len(pts) >= 2:
            segments.append(pts)
    if not segments:
        return []
    chains: list[list[list[float]]] = []
    while segments:
        chain = segments.pop(0)
        changed = True
        while changed and segments:
            changed = False
            for i, segment in enumerate(segments):
                if math.dist(chain[-1], segment[0]) < 0.75:
                    chain.extend(segment[1:]); segments.pop(i); changed = True; break
                if math.dist(chain[-1], segment[-1]) < 0.75:
                    chain.extend(reversed(segment[:-1])); segments.pop(i); changed = True; break
                if math.dist(chain[0], segment[-1]) < 0.75:
                    chain = segment[:-1] + chain; segments.pop(i); changed = True; break
                if math.dist(chain[0], segment[0]) < 0.75:
                    chain = list(reversed(segment[1:])) + chain; segments.pop(i); changed = True; break
        chains.append(chain)
    chain = max(chains, key=len)
    if len(chain) >= 3 and math.dist(chain[0], chain[-1]) < 2.0:
        chain[-1] = chain[0]
    return chain


class OverpassClient:
    def __init__(self, timeout: float = 60.0, retries: int = 2):
        self.timeout = timeout
        self.retries = retries

    def fetch(self, bbox_wgs84: tuple[float, float, float, float]) -> tuple[str, dict]:
        west, south, east, north = bbox_wgs84
        bb = f"{south},{west},{north},{east}"
        query = f'''[out:json][timeout:{max(20, int(self.timeout))}];
(
  way["building"]({bb});
  relation["building"]({bb});
  way["highway"]({bb});
  way["railway"="tram"]({bb});
  node["natural"="tree"]({bb});
);
out body geom;'''
        encoded = urlencode({"data": query}).encode("utf-8")
        failures = []
        for endpoint in OVERPASS_ENDPOINTS:
            for attempt in range(self.retries):
                try:
                    request = Request(endpoint, data=encoded, headers={
                        "Accept": "application/json",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "User-Agent": "BerlinWorldUnity/0.2 (+https://github.com/alexlanderzander/MAP)",
                    })
                    with urlopen(request, timeout=self.timeout) as response:
                        payload = json.loads(response.read())
                    if not isinstance(payload.get("elements"), list):
                        raise OsmError("Overpass response has no elements array")
                    return endpoint, payload
                except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, OsmError) as exc:
                    failures.append(f"{endpoint}: {exc}")
                    if attempt + 1 < self.retries:
                        time.sleep(min(5 * (attempt + 1), 15))
        raise OsmError("All Overpass endpoints failed: " + " | ".join(failures))


def normalize_osm(payload: dict, bbox_utm: tuple[float, float, float, float], tile_size: int = 500) -> dict[str, dict]:
    buildings: list[dict] = []
    roads: list[dict] = []
    trees: list[dict] = []
    seen_buildings: set[str] = set()
    seen_roads: set[str] = set()

    for element in payload.get("elements") or []:
        etype = element.get("type")
        eid = element.get("id")
        tags = element.get("tags") or {}
        source_id = f"osm:{etype}/{eid}"

        if tags.get("building") and etype in {"way", "relation"}:
            points = _utm_geometry(element.get("geometry") or []) if etype == "way" else _stitch_outer_relation(element)
            if len(points) >= 3:
                if points[0] == points[-1]:
                    ring = points[:-1]
                else:
                    ring = points
                if len(ring) >= 3:
                    cx, cy = _centroid(ring)
                    if _inside(cx, cy, bbox_utm) and source_id not in seen_buildings:
                        seen_buildings.add(source_id)
                        closed = ring + [ring[0]]
                        buildings.append({
                            "type": "Feature",
                            "id": source_id,
                            "properties": _building_properties(tags),
                            "geometry": {"type": "Polygon", "coordinates": [closed]},
                        })

        if etype == "way" and (tags.get("highway") or tags.get("railway") == "tram"):
            points = _utm_geometry(element.get("geometry") or [])
            if len(points) < 2:
                continue
            road_class = _road_class(tags)
            width = _number(tags.get("width"), ROAD_WIDTHS[road_class])
            lanes = int(max(1, min(255, _number(tags.get("lanes"), 1 if road_class in {"footway", "cycleway", "service", "tram"} else 2))))
            part_no = 0
            for clipped in clip_line(points, bbox_utm):
                for (tx, ty), part in split_line_to_tiles(clipped, tile_size):
                    part_id = f"{source_id}:{tx}:{ty}:{part_no}"
                    if part_id in seen_roads:
                        continue
                    seen_roads.add(part_id)
                    roads.append({
                        "type": "Feature",
                        "id": part_id,
                        "properties": {
                            "width": round(width, 2),
                            "lanes": lanes,
                            "class": road_class,
                            "source": "OpenStreetMap",
                        },
                        "geometry": {"type": "LineString", "coordinates": part},
                    })
                    part_no += 1

        if etype == "node" and tags.get("natural") == "tree" and "lon" in element and "lat" in element:
            e, n = wgs84_to_utm33(float(element["lon"]), float(element["lat"]))
            if not _inside(e, n, bbox_utm):
                continue
            height = max(1.5, _number(tags.get("height"), 8.0))
            crown = max(0.8, _number(tags.get("diameter_crown"), 4.0))
            species = tags.get("species") or tags.get("genus") or tags.get("taxon") or "unknown"
            trees.append({
                "type": "Feature",
                "id": source_id,
                "properties": {
                    "height": round(height, 2),
                    "crown": round(crown, 2),
                    "species_code": stable_id(species) & 0xFFFF,
                    "source": "OpenStreetMap",
                },
                "geometry": {"type": "Point", "coordinates": [e, n]},
            })

    return {
        "buildings": {"type": "FeatureCollection", "features": buildings},
        "roads": {"type": "FeatureCollection", "features": roads},
        "trees": {"type": "FeatureCollection", "features": trees},
    }
