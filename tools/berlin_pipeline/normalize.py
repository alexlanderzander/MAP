from __future__ import annotations

import math
from typing import Iterable

from format import stable_id


def _props(feature: dict) -> dict:
    return {str(k).lower(): v for k, v in (feature.get("properties") or {}).items()}


def _first(props: dict, names: Iterable[str], default=None):
    for name in names:
        value = props.get(name.lower())
        if value not in (None, ""):
            return value
    return default


def _num(value, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except ValueError:
        return default


def _feature_id(feature: dict, props: dict, fallback: str) -> str:
    return str(feature.get("id") or _first(props, ("uuid", "gkn", "detailnetz_id", "baumid", "id"), fallback))


def _ring_area(ring) -> float:
    if len(ring) < 3:
        return 0.0
    return 0.5 * sum(
        ring[i][0] * ring[(i + 1) % len(ring)][1]
        - ring[(i + 1) % len(ring)][0] * ring[i][1]
        for i in range(len(ring))
    )


def _polygon_outer(geometry: dict) -> list[list[float]]:
    coords = geometry.get("coordinates") or []
    if geometry.get("type") == "Polygon":
        rings = [coords[0]] if coords else []
    elif geometry.get("type") == "MultiPolygon":
        rings = [poly[0] for poly in coords if poly]
    else:
        return []
    if not rings:
        return []
    ring = max(rings, key=lambda r: abs(_ring_area(r)))
    points = [[float(p[0]), float(p[1])] for p in ring]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    return points


def _centroid(points: list[list[float]]) -> tuple[float, float]:
    return sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)


def _inside(x: float, y: float, bbox: tuple[float, float, float, float]) -> bool:
    return bbox[0] <= x < bbox[2] and bbox[1] <= y < bbox[3]


def _building_class(text: str) -> str:
    value = text.casefold()
    if any(k in value for k in ("wohn", "wohnen")):
        return "residential"
    if any(k in value for k in ("handel", "geschäft", "geschaeft", "büro", "buero", "hotel", "gastronom")):
        return "commercial"
    if any(k in value for k in ("industrie", "lager", "fabrik", "werkstatt")):
        return "industrial"
    if any(k in value for k in ("kirche", "museum", "schule", "univers", "verwaltung", "rathaus", "theater", "bibliothek")):
        return "public"
    return "unknown"


def normalize_buildings(collection: dict, bbox: tuple[float, float, float, float]) -> dict:
    out: list[dict] = []
    for idx, feature in enumerate(collection.get("features") or []):
        points = _polygon_outer(feature.get("geometry") or {})
        if len(points) < 3:
            continue
        cx, cy = _centroid(points)
        if not _inside(cx, cy, bbox):
            continue
        props = _props(feature)
        storeys = _num(_first(props, ("aog", "storeysaboveground", "levels")), 0.0)
        height = _num(_first(props, ("measuredheight", "height", "hoehe", "höhe")), 0.0)
        if height <= 0:
            height = max(3.6, storeys * 3.2 + 0.8) if storeys > 0 else 12.0
        cls_text = str(_first(props, ("bezgfk", "building", "funktion", "function"), ""))
        out.append({
            "type": "Feature",
            "id": _feature_id(feature, props, f"building-{idx}"),
            "properties": {
                "height": round(height, 2),
                "min_height": 0.0,
                "roof_type": "flat",
                "class": _building_class(cls_text),
                "source": "ALKIS",
            },
            "geometry": {"type": "Polygon", "coordinates": [points + [points[0]]]},
        })
    return {"type": "FeatureCollection", "features": out}


def _road_class(props: dict) -> str:
    okstra = str(_first(props, ("okstra_klasse", "okstraklasse", "strklasse", "okstra"), "")).upper()
    step = str(_first(props, ("step_klasse", "stepklasse", "step"), "")).upper()
    rbs = str(_first(props, ("rbs_klasse", "rbsklasse", "rbs"), "")).upper()
    if okstra == "A" or "AUTO" in rbs:
        return "motorway"
    if okstra in {"F", "Q", "Z"} or any(k in rbs for k in ("FUWE", "FUSS", "PLAT", "ZG")):
        return "footway"
    if okstra in {"R", "X"}:
        return "cycleway"
    if step in {"I", "II"} or okstra in {"B", "L", "S", "K"}:
        return "primary"
    if step == "III":
        return "secondary"
    if step == "IV":
        return "tertiary"
    if any(k in rbs for k in ("PSTR", "ZUFA", "PAPL", "WIW")):
        return "service"
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
    "unknown": 6.0,
}


def _clip_segment(a, b, bbox):
    x0, y0 = float(a[0]), float(a[1])
    x1, y1 = float(b[0]), float(b[1])
    dx, dy = x1 - x0, y1 - y0
    p = (-dx, dx, -dy, dy)
    q = (x0 - bbox[0], bbox[2] - x0, y0 - bbox[1], bbox[3] - y0)
    u0, u1 = 0.0, 1.0
    for pi, qi in zip(p, q):
        if pi == 0:
            if qi < 0:
                return None
            continue
        r = qi / pi
        if pi < 0:
            u0 = max(u0, r)
        else:
            u1 = min(u1, r)
        if u0 > u1:
            return None
    return [x0 + u0 * dx, y0 + u0 * dy], [x0 + u1 * dx, y0 + u1 * dy]


def clip_line(points, bbox) -> list[list[list[float]]]:
    parts: list[list[list[float]]] = []
    current: list[list[float]] = []
    for a, b in zip(points, points[1:]):
        clipped = _clip_segment(a, b, bbox)
        if clipped is None:
            if len(current) >= 2:
                parts.append(current)
            current = []
            continue
        ca, cb = clipped
        if not current:
            current = [ca, cb]
        elif math.dist(current[-1], ca) < 1e-6:
            if math.dist(current[-1], cb) >= 1e-6:
                current.append(cb)
        else:
            if len(current) >= 2:
                parts.append(current)
            current = [ca, cb]
    if len(current) >= 2:
        parts.append(current)
    return parts


def split_line_to_tiles(points, tile_size: int) -> list[tuple[tuple[int, int], list[list[float]]]]:
    if len(points) < 2:
        return []
    min_x = min(float(p[0]) for p in points)
    max_x = max(float(p[0]) for p in points)
    min_y = min(float(p[1]) for p in points)
    max_y = max(float(p[1]) for p in points)
    tx0 = math.floor(min_x / tile_size)
    tx1 = tx0 if abs(max_x - min_x) < 1e-7 else math.floor((max_x - 1e-7) / tile_size)
    ty0 = math.floor(min_y / tile_size)
    ty1 = ty0 if abs(max_y - min_y) < 1e-7 else math.floor((max_y - 1e-7) / tile_size)
    result = []
    for tx in range(tx0, tx1 + 1):
        for ty in range(ty0, ty1 + 1):
            tb = (tx * tile_size, ty * tile_size, (tx + 1) * tile_size, (ty + 1) * tile_size)
            for part in clip_line(points, tb):
                if len(part) >= 2 and any(math.dist(part[i], part[i + 1]) > 1e-5 for i in range(len(part) - 1)):
                    result.append(((tx, ty), part))
    return result


def normalize_roads(collection: dict, bbox: tuple[float, float, float, float], tile_size: int = 500) -> dict:
    out: list[dict] = []
    for idx, feature in enumerate(collection.get("features") or []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") == "LineString":
            lines = [geometry.get("coordinates") or []]
        elif geometry.get("type") == "MultiLineString":
            lines = geometry.get("coordinates") or []
        else:
            continue
        props = _props(feature)
        cls = _road_class(props)
        width = _num(_first(props, ("width", "breite")), ROAD_WIDTHS[cls])
        lanes = int(max(1, _num(
            _first(props, ("lanes", "fahrstreifen")),
            1 if cls in {"footway", "cycleway", "service"} else 2,
        )))
        base_id = _feature_id(feature, props, f"road-{idx}")
        part_no = 0
        for line in lines:
            for clipped in clip_line(line, bbox):
                for (tx, ty), part in split_line_to_tiles(clipped, tile_size):
                    out.append({
                        "type": "Feature",
                        "id": f"{base_id}:{tx}:{ty}:{part_no}",
                        "properties": {
                            "width": round(width, 2),
                            "lanes": lanes,
                            "class": cls,
                            "source": "Detailnetz",
                        },
                        "geometry": {"type": "LineString", "coordinates": part},
                    })
                    part_no += 1
    return {"type": "FeatureCollection", "features": out}


def normalize_trees(collection: dict, bbox: tuple[float, float, float, float]) -> dict:
    out: list[dict] = []
    for idx, feature in enumerate(collection.get("features") or []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point" or len(geometry.get("coordinates") or []) < 2:
            continue
        x, y = map(float, geometry["coordinates"][:2])
        if not _inside(x, y, bbox):
            continue
        props = _props(feature)
        height = max(1.5, _num(_first(props, ("baumhoehe", "baumhoehe_", "height")), 8.0))
        crown = max(0.8, _num(
            _first(props, ("kronedurch", "kronendurchmesser", "kronedur_1", "crown")),
            4.0,
        ))
        species = str(_first(props, ("art_dtsch", "art_deutsch", "gattung_deutsch", "species"), "unknown"))
        out.append({
            "type": "Feature",
            "id": _feature_id(feature, props, f"tree-{idx}"),
            "properties": {
                "height": round(height, 2),
                "crown": round(crown, 2),
                "species_code": stable_id(species) & 0xFFFF,
                "source": "Baumbestand",
            },
            "geometry": {"type": "Point", "coordinates": [x, y]},
        })
    return {"type": "FeatureCollection", "features": out}
