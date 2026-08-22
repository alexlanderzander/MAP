from __future__ import annotations

from dataclasses import dataclass
import json
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import xml.etree.ElementTree as ET


class WfsError(RuntimeError):
    pass


@dataclass(frozen=True)
class WfsSource:
    id: str
    endpoint: str
    preferred_names: tuple[str, ...]
    fallback_names: tuple[str, ...]


SOURCES: dict[str, WfsSource] = {
    "buildings": WfsSource(
        "alkis-gebaeude",
        "https://gdi.berlin.de/services/wfs/alkis_gebaeude",
        ("re_gebaeude", "gebaeude"),
        ("fis:re_gebaeude", "alkis_gebaeude:re_gebaeude", "alkis_gebaeude:gebaeude"),
    ),
    "roads": WfsSource(
        "detailnetz-strassenabschnitte",
        "https://gdi.berlin.de/services/wfs/detailnetz",
        ("c_strassenabschnitte", "strassenabschnitte"),
        ("detailnetz:c_strassenabschnitte",),
    ),
    "trees": WfsSource(
        "baumbestand",
        "https://gdi.berlin.de/services/wfs/baumbestand",
        ("baumbestand", "baum", "baeume"),
        ("fis:s_wfs_baumbestand", "baumbestand:baumbestand", "baumbestand:baeume"),
    ),
}


class WfsClient:
    def __init__(self, timeout: float = 30.0, retries: int = 3, page_size: int = 5000):
        self.timeout = timeout
        self.retries = retries
        self.page_size = page_size

    def _request(self, url: str, accept: str) -> bytes:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            try:
                request = Request(url, headers={
                    "Accept": accept,
                    "User-Agent": "BerlinWorldUnity/0.2 (+https://github.com/alexlanderzander/MAP)",
                })
                with urlopen(request, timeout=self.timeout) as response:
                    return response.read()
            except (HTTPError, URLError, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt + 1 < self.retries:
                    time.sleep(min(2 ** attempt, 4))
        raise WfsError(f"WFS request failed after {self.retries} attempts: {url}: {last_error}")

    @staticmethod
    def _url(endpoint: str, params: dict[str, object]) -> str:
        return endpoint.rstrip("?") + "?" + urlencode(params, doseq=True, safe=":,")

    def feature_types(self, endpoint: str) -> list[str]:
        url = self._url(endpoint, {"service": "WFS", "request": "GetCapabilities"})
        raw = self._request(url, "application/xml,text/xml")
        try:
            root = ET.fromstring(raw)
        except ET.ParseError as exc:
            raise WfsError(f"Invalid GetCapabilities XML from {endpoint}: {exc}") from exc
        result: list[str] = []
        for elem in root.iter():
            if elem.tag.rsplit("}", 1)[-1] != "FeatureType":
                continue
            for child in elem:
                if child.tag.rsplit("}", 1)[-1] == "Name" and child.text:
                    result.append(child.text.strip())
                    break
        return result

    def candidate_names(self, source: WfsSource) -> list[str]:
        candidates: list[str] = []
        try:
            available = self.feature_types(source.endpoint)
        except WfsError:
            available = []
        for needle in source.preferred_names:
            needle = needle.lower()
            for name in available:
                if needle in name.lower() and name not in candidates:
                    candidates.append(name)
        for name in source.fallback_names:
            if name not in candidates:
                candidates.append(name)
        return candidates

    def fetch_geojson(self, endpoint: str, type_name: str, bbox: tuple[float, float, float, float]) -> dict:
        all_features: list[dict] = []
        seen: set[str] = set()
        start = 0
        for _page in range(100):
            params = {
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": type_name,
                "bbox": ",".join(str(v) for v in (*bbox, "EPSG:25833")),
                "srsName": "EPSG:25833",
                "outputFormat": "application/json",
                "count": self.page_size,
                "startIndex": start,
            }
            url = self._url(endpoint, params)
            raw = self._request(url, "application/json,application/geo+json,*/*;q=0.1")
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                snippet = raw[:250].decode("utf-8", "replace")
                raise WfsError(f"WFS did not return GeoJSON for {type_name}: {snippet}") from exc
            if payload.get("type") != "FeatureCollection":
                raise WfsError(f"Unexpected WFS payload for {type_name}: {payload.get('type')!r}")
            features = payload.get("features") or []
            new_count = 0
            for feature in features:
                key = str(feature.get("id") or json.dumps(feature.get("geometry"), sort_keys=True))
                if key in seen:
                    continue
                seen.add(key)
                all_features.append(feature)
                new_count += 1
            returned = int(payload.get("numberReturned", len(features)) or len(features))
            matched = payload.get("numberMatched")
            if matched not in (None, "unknown"):
                try:
                    if len(all_features) >= int(matched):
                        break
                except (TypeError, ValueError):
                    pass
            if returned == 0 or len(features) < self.page_size or new_count == 0:
                break
            start += returned
        else:
            raise WfsError(f"Pagination limit reached for {type_name}")
        return {"type": "FeatureCollection", "features": all_features}

    def fetch_source(self, source: WfsSource, bbox: tuple[float, float, float, float]) -> tuple[str, dict]:
        failures: list[str] = []
        for name in self.candidate_names(source):
            try:
                return name, self.fetch_geojson(source.endpoint, name, bbox)
            except WfsError as exc:
                failures.append(f"{name}: {exc}")
        raise WfsError(f"No usable feature type for {source.id}. " + " | ".join(failures))
