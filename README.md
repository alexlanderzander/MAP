# Berlin World for Unity

A storage-first foundation for a **1:1-scale Berlin open world** in Unity. The project does not ship a gigantic Berlin mesh. Instead it stores compact geographic facts (building footprints/heights, road centre-lines, tree points) and creates meshes, colliders and destruction geometry in Unity.

Current status: **v0.1 foundation / prototype**. It is not yet a full present-day Berlin download. The core tile format, Python packer, Unity runtime reader, 1:1 UTM coordinate mapping, streaming prototype, procedural building/road meshes and zero-disk fracture prototype are implemented so the real Berlin ingest can be layered on top without committing gigabytes.

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

## Create compact tiles

The v0.1 packer consumes GeoJSON whose coordinates are already EPSG:25833 metres. It intentionally has no heavy Python dependencies.

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

## Official data plan

`DataSources/berlin_sources.json` records the stable source pages and licensing notes. The intended production stack is:

- Berlin LoD2 / ALKIS for buildings.
- Detailnetz for roads, paths, bridges and tunnels.
- Berlin tree inventory for mapped trees.
- TrueDOP 2026 as an offline alignment/reference source rather than a mandatory game texture.
- The 2025 photogrammetry mesh only as an optional/reference layer after its provider-specific redistribution terms are reviewed.

Most core official layers are listed by Berlin Open Data under **Datenlizenz Deutschland – Zero 2.0**; provider-specific layers must be treated separately. Always preserve a source manifest for every generated world build.

## Destruction prototype

`DestructibleBuilding` is deliberately disk-cheap. The intact building stores only its normal generated mesh. After the damage threshold is reached, wall chunks are created procedurally from the same footprint/height data and receive physics impulses. There are no city-wide fracture meshes on disk.

This is only the first destruction model. High-quality structural destruction will need floors, interior shells, structural cells, persistence, damage decals and localized mesh replacement rather than making every building a permanent rigid-body hierarchy.

## CI and storage guardrails

GitHub Actions runs the binary-format tests, packs a synthetic sample and rejects accidentally committed raw GIS/photogrammetry files or individual repository files above 5 MiB. Large generated Berlin content belongs outside normal Git.

Run locally:

```bash
python -m unittest discover -s tools/berlin_pipeline/tests -v
python tools/validate_package.py
```

## Next milestones

1. Add a robust Berlin downloader/normalizer that can ingest WFS/ATOM/CityGML and cache source data outside the repository.
2. Proper LoD2 roof reconstruction and polygon holes.
3. Road clipping, intersections, curbs, sidewalks, markings, bridges and tunnels.
4. Quantized terrain tiles and water surfaces.
5. GPU-instanced trees/props and material/facade variation.
6. Near/far building batching so hundreds of thousands of structures do not become individual GameObjects.
7. Structural destruction cells, debris pooling and persistent damage.
8. An automated 1 km² real-Berlin validation build before scaling city-wide.

See `Documentation~/ARCHITECTURE.md` and `Documentation~/BWT1.md` for the design details.
