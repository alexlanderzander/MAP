# Hackescher Markt real-data validation area

The first real-world validation area is **Hackescher Markt / Berlin-Mitte**, not Alexanderplatz.

## Bounds

The project uses a tile-aligned 1 km square in ETRS89 / UTM 33N (`EPSG:25833`):

```text
min easting:   391000 m
min northing: 5820000 m
max easting:   392000 m
max northing: 5821000 m
```

This is exactly four 500 m BWT tiles (`x=782..783`, `z=11640..11641`). Hackescher Markt is near the middle of the square.

## Build it

From the repository root:

```bash
python tools/berlin_pipeline/build_area.py \
  --area DataSources/hackescher_markt_area.json \
  --out GeneratedBerlin/HackescherMarkt/Tiles
```

The default `--source auto` first tries Berlin's official WFS services. If they are down for maintenance, it falls back to a current OpenStreetMap Overpass query for the same 1 km area. Intermediate network data is temporary; the persistent output is compact BWT1 plus manifests.

To force one source:

```bash
# official Berlin data only; fail instead of falling back
python tools/berlin_pipeline/build_area.py --source official

# current OSM only
python tools/berlin_pipeline/build_area.py --source osm
```

The generated directory is ignored by Git by design. Copy/link it to `Assets/StreamingAssets/Berlin/Tiles/` in a Unity project using this package.

## Preferred official layers

- **ALKIS Gebäude**: cadastral footprints, building function and number of above-ground storeys. The v0.2 importer uses `aog` as a temporary height estimate (`storeys × 3.2 m + 0.8 m`) when measured height is absent.
- **Detailnetz Berlin**: official road/path centre-lines and classifications. Long streets are clipped to the 1 km area and split at 500 m tile boundaries before BWT quantization.
- **Baumbestand Berlin**: official mapped tree points, with real height/crown values when present.

All three are consumed in EPSG:25833, so no approximate scale conversion is necessary.

## Maintenance fallback

During development on 22 August 2026 the live Berlin GDI endpoint returned its `Wartungsarbeiten` HTML page instead of WFS GeoJSON. Rather than blocking the milestone, `auto` now falls back to OpenStreetMap for the validation area.

The fallback queries buildings, highways, tram ways and mapped trees through Overpass, converts WGS84 directly to UTM zone 33N in the pipeline, and then uses the same clipping, 500 m tiling and BWT compression path as official data. It tries the main Overpass instance and the current Private.coffee public instance.

The OSM fallback is **ODbL 1.0** data and requires attribution (`© OpenStreetMap contributors`) plus compliance with the ODbL when derived database data is distributed. `source_manifest.json` records which source mode was actually used. For a whole-Berlin production build, use a regional OSM extract rather than repeatedly querying a public Overpass server.

## What is real vs generated at this milestone

Real/source-derived now:

- building footprints and placement;
- street/path/tram alignment;
- mapped tree placement;
- metric 1:1 scale.

Generated/estimated now:

- building facade appearance;
- roof shape when the selected source does not provide a supported roof tag;
- building height when the selected source has storeys but no measured height;
- street surface width when no explicit width exists;
- materials and street furniture.

The next building pass should merge ALKIS with Berlin LoD2 roof/height data once that service is available. We intentionally do not bake a giant photogrammetry mesh into the game.

## Storage policy

Raw WFS/Overpass responses are not stored in the repository. `build_area.py` processes them transiently and emits a `source_manifest.json` with source URL, counts, retrieval time and license. This keeps the game data reproducible without retaining bulky source files.

The most important storage rule remains: **store semantic city data, generate meshes at runtime/editor-build time, and only keep unique textures/hero assets when they add visible value.**

## Availability and CI

The WFS client discovers feature type names from `GetCapabilities`, has known-name fallbacks, paginates responses and retries transient failures. The Overpass client similarly retries across public instances. CI includes a live Hackescher Markt smoke build in addition to deterministic unit/cross-language tests.
