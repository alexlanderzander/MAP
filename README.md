# Berlin World for Unity

A storage-first foundation for a **1:1-scale Berlin open world** in Unity. The project does not ship a gigantic Berlin mesh. Instead it stores compact geographic facts (building footprints/heights, road centre-lines, tree points) and creates meshes, colliders and destruction geometry in Unity.

Current status: **v0.2 real-data validation**. The compact tile format, Unity runtime, procedural destruction prototype and live Berlin-data ingestion pipeline are implemented. The first validation area is a tile-aligned **1 km × 1 km area around Hackescher Markt**.

## Why this approach

A city-sized OBJ/FBX repeats huge amounts of vertex, normal, UV and texture data. Berlin World uses a custom compact `BWT1` format:

- 500 m streaming tiles by default.
- 1 Unity unit = 1 metre.
- EPSG:25833 (ETRS89 / UTM 33N), with a local Unity origin for precision.
- 2 cm signed coordinate quantization inside each tile.
- Stable 64-bit feature IDs.
- Gzip-compressed binary tiles.
- No stored fracture meshes; destruction chunks are generated only when needed.
- No default orthophoto layer in a shipped build; high-resolution aerial imagery is an authoring/reference input.

This makes **procedural representation + compression** the main disk-saving mechanism, not simply compressing an already huge mesh.

## Install in Unity

Target editor: **Unity 6000.3 (Unity 6.3 LTS)**.

In Unity Package Manager choose **Add package from git URL** and enter:

```text
https://github.com/alexlanderzander/MAP.git
```

Then create a `BerlinWorldSettings` asset via **Assets > Create > Berlin World > World Settings**, put `BerlinWorldStreamer` on an empty scene object, assign the settings and a player/camera transform, and provide generated tiles under:

```text
Assets/StreamingAssets/Berlin/Tiles/
```

The package also exposes **Berlin World > Install Generated Tiles** for copying a generated tile folder already inside the Unity project.

## Build the real Hackescher Markt test area

The first real-world area **prefers** official Berlin WFS data for ALKIS buildings, Detailnetz roads/paths and the Berlin tree inventory. If Berlin's GDI services are under maintenance, the default `--source auto` transparently falls back to current OpenStreetMap data through Overpass. Raw responses are processed transiently and are **not** retained in the game or repository.

```bash
python tools/berlin_pipeline/build_area.py \
  --area DataSources/hackescher_markt_area.json \
  --out GeneratedBerlin/HackescherMarkt/Tiles
```

The selected EPSG:25833 bounds are `391000,5820000 → 392000,5821000`, exactly four 500 m BWT tiles. On the live CI build on **22 August 2026**, Berlin's WFS server returned its maintenance page, so the automatic OSM fallback successfully produced **814 buildings, 1,630 clipped road/path/tram parts and 713 mapped trees**. The compressed BWT geometry for all 3,157 features was **92,653 bytes** (the whole output directory including manifests occupied about 116 KiB).

That storage result is intentionally geometry/semantic data only; high-quality materials, unique landmarks, interiors and audio will be separate budgets. See `Documentation~/HACKESCHER_MARKT.md` for fidelity and licensing notes.

When official ALKIS is available, footprints/function/storeys can be ingested directly. Proper LoD2 measured heights and roof surfaces are the next building-data enrichment step.

## Create compact tiles from your own GeoJSON

The packer also consumes GeoJSON whose coordinates are already EPSG:25833 metres. It intentionally has no heavy Python dependencies.

```bash
python tools/berlin_pipeline/cli.py pack \
  --buildings path/to/buildings.geojson \
  --roads path/to/roads.geojson \
  --trees path/to/trees.geojson \
  --out GeneratedBerlin/Tiles
```

Try the synthetic CI sample:

```bash
python tools/berlin_pipeline/cli.py pack \
  --buildings tools/berlin_pipeline/sample/buildings.geojson \
  --roads tools/berlin_pipeline/sample/roads.geojson \
  --trees tools/berlin_pipeline/sample/trees.geojson \
  --out /tmp/berlin-tiles
```

The sample is deliberately synthetic and is **not** a Berlin map asset.

## Data plan

`DataSources/berlin_sources.json` records source pages, live endpoints and licensing notes. The preferred production stack is:

- Berlin LoD2 + ALKIS for buildings.
- Detailnetz for roads, paths, bridges and tunnels.
- Berlin tree inventory for mapped trees.
- OpenStreetMap as a live fallback/reference layer when official services are unavailable; OSM is ODbL and requires attribution/compliance.
- TrueDOP 2026 as an offline alignment/reference source rather than a mandatory game texture.
- The 2025 photogrammetry mesh only as an optional/reference layer after its provider-specific redistribution terms are reviewed.

Most core official Berlin layers are listed under **Datenlizenz Deutschland – Zero 2.0**. OpenStreetMap has separate **ODbL 1.0** terms. Every live build emits a `source_manifest.json` containing the source mode actually used, endpoint, counts, retrieval time and license information.

## Destruction prototype

`DestructibleBuilding` is deliberately disk-cheap. The intact building stores only its normal generated mesh. After the damage threshold is reached, wall chunks are created procedurally from the same footprint/height data and receive physics impulses. There are no city-wide fracture meshes on disk.

This is only the first destruction model. High-quality structural destruction will need floors, interior shells, structural cells, persistence, damage decals and localized mesh replacement rather than making every building a permanent rigid-body hierarchy.

## CI and storage guardrails

GitHub Actions runs binary-format, WFS/normalization and OSM-conversion tests, packs a synthetic sample, cross-checks the C# decoder and rejects accidentally committed raw GIS/photogrammetry files or individual repository files above 5 MiB. A separate live Hackescher Markt smoke build verifies that the current network-source path can produce the real 1 km area.

Run locally:

```bash
python -m unittest discover -s tools/berlin_pipeline/tests -v
python tools/validate_package.py
```

## Next milestones

1. Merge LoD2 measured heights and roof surfaces onto ALKIS building IDs/footprints.
2. Add terrain/elevation and water surfaces.
3. Turn Detailnetz/OSM centre-lines into proper intersections, curbs, sidewalks, markings, bridges and tunnels.
4. GPU-instance trees/props and add procedural Berlin facade/material variation.
5. Near/far building batching so hundreds of thousands of structures do not become individual GameObjects.
6. Structural destruction cells, debris pooling and persistent damage.
7. Benchmark the Hackescher Markt 1 km² build for disk, RAM, VRAM, frame time and load time before expanding the validation envelope.

See `Documentation~/ARCHITECTURE.md`, `Documentation~/BWT1.md` and `Documentation~/HACKESCHER_MARKT.md` for design details.
