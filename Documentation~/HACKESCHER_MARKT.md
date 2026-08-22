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

This is exactly four 500 m BWT tiles (`x=782..783`, `z=11640..11641`). Hackescher Markt station is near the middle of the square.

## Build it

From the repository root:

```bash
python tools/berlin_pipeline/build_area.py \
  --area DataSources/hackescher_markt_area.json \
  --out GeneratedBerlin/HackescherMarkt/Tiles
```

The command talks directly to Berlin's current WFS endpoints, normalizes the returned GeoJSON, writes temporary intermediate files, packs BWT1 tiles, and deletes the temporary files. Only the compact tiles and two small manifests remain.

The generated directory is ignored by Git by design. Copy/link it to `Assets/StreamingAssets/Berlin/Tiles/` in a Unity project using this package.

## Current official layers

- **ALKIS Gebäude**: exact cadastral footprints, building function and number of above-ground storeys. The v0.2 importer uses real footprints and uses `aog` as a temporary height estimate (`storeys × 3.2 m + 0.8 m`) when measured height is absent.
- **Detailnetz Berlin**: official road/path centre-lines and classifications. Long streets are clipped to the 1 km area and split at 500 m tile boundaries before BWT quantization.
- **Baumbestand Berlin**: official mapped tree points, with real height/crown values when present.

All three are consumed in EPSG:25833, so no reprojection or approximate scaling is necessary.

## What is real vs generated at this milestone

Real now:

- building footprints and placement;
- street/path alignment from Detailnetz;
- mapped public tree placement;
- metric 1:1 scale.

Generated/estimated now:

- building facade appearance;
- roof shape (temporarily flat in this importer);
- building height when ALKIS has storeys but no measured height;
- street surface width where Detailnetz does not provide a width;
- materials and street furniture.

The next building pass should merge the same ALKIS building IDs/footprints with Berlin LoD2 roof/height data. We intentionally do not bake a giant photogrammetry mesh into the game.

## Storage policy

Raw WFS responses are not stored in the repository. `build_area.py` uses a temporary directory and emits a `source_manifest.json` with source URL, selected feature type, feature counts, retrieval time and license. This keeps the game data reproducible without retaining bulky source files.

The most important storage rule remains: **store semantic city data, generate meshes at runtime/editor-build time, and only keep unique textures/hero assets when they add visible value.**

## Availability

Berlin's geodata services can occasionally be unavailable during maintenance. The WFS client discovers feature type names from `GetCapabilities`, has known-name fallbacks, paginates responses, retries transient failures and gives a clear error if no candidate works. CI includes a non-blocking live Hackescher Markt smoke build so service availability is visible without making normal code tests flaky.
