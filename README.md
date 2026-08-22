# Berlin World for Unity

Storage-first tooling for a **1:1-scale Berlin open world** in Unity. The project keeps the geographic source data tiny and creates the expensive 3D geometry in Unity instead of shipping a city-sized OBJ/FBX.

## Current milestone: Hackescher Markt v0.3

The first playable validation area is a tile-aligned **1 km × 1 km around Hackescher Markt, Berlin-Mitte**. It is generated from live map data and stored as four compact 500 m tiles.

The v0.3 runtime generates:

- building footprints at 1:1 horizontal scale;
- source/estimated building heights and roof classes;
- procedural roof volumes, facade windows and per-building colours when source tags exist;
- roads, pedestrian/cycle paths and sidewalks;
- tram/rail tracks;
- parks, grass, paved plazas/parking and water polygons;
- combined low-overhead tree meshes;
- colliders and on-demand procedural building destruction;
- player-centred tile streaming.

The map format remains intentionally compact: 2 cm coordinate quantization inside 500 m tiles + gzip. No city-wide fracture meshes, duplicate building meshes or mandatory orthophoto textures are stored.

## Fidelity contract

**1 Unity unit = 1 metre.** Source geometry is converted to `EPSG:25833` (ETRS89 / UTM 33N), then translated to a local origin near Hackescher Markt for floating-point precision.

This is a real 1:1 geographic outdoor map, not a claim that every facade/window/roof/interior is a survey-grade copy of Berlin today. Public source data does not contain every street-level detail or interior. The pipeline prefers current official Berlin WFS data and enriches it with OpenStreetMap semantics; when Berlin GDI is under maintenance it automatically falls back to current OSM. Source provenance is written to `source_manifest.json` on every build.

## Build the Hackescher Markt tiles

Requires Python 3.12+ and no third-party Python packages:

```bash
python tools/berlin_pipeline/build_area.py \
  --area DataSources/hackescher_markt_area.json \
  --out GeneratedBerlin/HackescherMarkt/Tiles
```

`--source auto` (default) prefers official Berlin data. `--source osm` can force the current OSM path. Raw network responses are processed transiently and are not retained.

GitHub Actions also builds the area and uploads **HackescherMarkt-Unity-Tiles** as a workflow artifact, so generated map data does not need to live in Git history.

## Use in Unity

Target: **Unity 6000.3 / Unity 6.3 LTS**.

In Package Manager choose **Add package from git URL**:

```text
https://github.com/alexlanderzander/MAP.git
```

Then:

1. Generate/download the `HackescherMarkt-Unity-Tiles` folder.
2. Use **Berlin World > Install Generated Tiles** to copy the generated tile folder into the project.
3. Run **Berlin World > Hackescher Markt > Create 1:1 Scene Rig**.
4. Press Play.

Materials are optional. If no materials are assigned, the package creates lightweight fallback materials at runtime. Custom PBR materials can be assigned in `BerlinWorldSettings` without changing the map data.

## BWT v2 storage format

BWT v2 stores semantic facts rather than rendered geometry: building footprint/height/levels/roof/facade metadata; road/rail centre-lines with width/surface/sidewalk/bridge/tunnel flags; tree position/height/crown; and clipped water/park/grass/pedestrian/plaza/parking polygons.

Coordinates are signed 16-bit deltas at 2 cm resolution from each tile centre. The C# reader remains backward-compatible with BWT v1.

## Storage rules

Do not commit raw `.gml`, `.citygml`, `.gpkg`, `.pbf`, `.tif`, `.obj`, `.fbx`, photogrammetry or generated city output to normal Git. CI enforces a per-file size budget. Keep reusable textures/materials shared, generate facade/window/roof geometry procedurally, and only ship unique hero assets where they are visibly necessary.

## Licences / attribution

The generated `source_manifest.json` is authoritative for a build. Core Berlin Open Data layers are listed under **Datenlizenz Deutschland – Zero 2.0** in `DataSources/berlin_sources.json`. OSM fallback/enrichment is **ODbL 1.0** and requires `© OpenStreetMap contributors` attribution and applicable ODbL compliance when the derived database is distributed.

The Berlin 2025 photogrammetry mesh is **not** bundled because its provider-specific redistribution terms must be reviewed separately.
