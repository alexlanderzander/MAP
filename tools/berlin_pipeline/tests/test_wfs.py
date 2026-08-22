import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wfs import WfsClient, WfsSource

CAPABILITIES = b'''<WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0"><wfs:FeatureTypeList><wfs:FeatureType><wfs:Name>detailnetz:c_strassenabschnitte</wfs:Name></wfs:FeatureType></wfs:FeatureTypeList></WFS_Capabilities>'''


class FakeClient(WfsClient):
    def __init__(self):
        super().__init__(retries=1, page_size=2)
        self.urls = []

    def _request(self, url: str, accept: str) -> bytes:
        self.urls.append(url)
        if "GetCapabilities" in url:
            return CAPABILITIES
        if "startIndex=0" in url:
            return json.dumps({
                "type": "FeatureCollection",
                "numberMatched": 3,
                "numberReturned": 2,
                "features": [{"id": "1", "geometry": None}, {"id": "2", "geometry": None}],
            }).encode()
        return json.dumps({
            "type": "FeatureCollection",
            "numberMatched": 3,
            "numberReturned": 1,
            "features": [{"id": "3", "geometry": None}],
        }).encode()


class WfsTests(unittest.TestCase):
    def test_discovery_and_pagination(self):
        client = FakeClient()
        source = WfsSource(
            "x",
            "https://example.test/wfs",
            ("strassenabschnitte",),
            ("fallback:x",),
        )
        self.assertEqual(client.candidate_names(source)[0], "detailnetz:c_strassenabschnitte")
        fc = client.fetch_geojson(source.endpoint, "detailnetz:c_strassenabschnitte", (1, 2, 3, 4))
        self.assertEqual(len(fc["features"]), 3)
        self.assertTrue(any("EPSG:25833" in url for url in client.urls))


if __name__ == "__main__":
    unittest.main()
