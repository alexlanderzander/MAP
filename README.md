# Berlin World for Unity

A storage-conscious **1:1-scale Berlin open world** for Unity. The project now has two coordinated layers: a tiny semantic/gameplay representation and an optional exact-source visual layer built from the official textured Berlin 3D mesh.

## Current milestone: Hackescher Markt v0.4 exact visual mode

The validation area is a tile-aligned **1 km × 1 km around Hackescher Markt, Berlin-Mitte**. `1 Unity unit = 1 metre`; coordinates are tied to `EPSG:25833` and translated around a local origin at E 391500 / N 5820500 for floating-point precision.

The compact BWT layer still provides building IDs and footprints, roads/paths/rail, mapped trees and surface semantics, streaming, gameplay colliders and procedural destruction. When exact mode is installed, those generated meshes become invisible gameplay proxies and the visible city comes from packed source OBJ geometry and source textures instead.

## What “exact” means

The exact-mode packer preserves the supplied Berlin source triangles instead of recreating buildings from footprints. It does not decimate geometry, resample UVs or recompress image files. Geometry is translated to the local Unity origin and stored as float32 positions/UVs with packed normals and 32-bit indices in gzip-compressed `BWM1` chunks. Texture bytes are copied unchanged and deduplicated by content hash.

This makes the rendered outdoor geometry/textures match the **official source mesh you provide**. The currently documented Berlin mesh is based on the June 2025 multiperspective aerial survey, so no software can truthfully turn it into a literal live August 2026 scan. Aerial photogrammetry also cannot reveal hidden interiors or unseen surfaces. Current semantic map data is kept separately so changed roads/building footprints can be detected and updated without corrupting the visual source.

## Install compact gameplay tiles

Requires Python 3.12+ and no third-party Python packages:

```bash
python tools/berlin_pipeline/build_area.py \
  --area DataSources/hackescher_markt_area.json \
  --out GeneratedBerlin/HackescherMarkt/Tiles
```

GitHub Actions also builds `HackescherMarkt-Unity-Tiles` without committing generated city data to Git.

## Install exact visual geometry

1. Obtain the required Hackescher Markt OBJ/texture tiles from the official Berlin 3D Downloadportal and accept its current provider terms.
2. Install this Unity package and the compact gameplay tiles.
3. In Unity choose **Berlin World > Hackescher Markt > Import Exact Berlin Source Mesh**.
4. Select the downloaded OBJ directory, a portal ZIP, or a directory of ZIPs.
5. Leave **Bind visual triangles to destructible semantic buildings** enabled and run the packer.
6. Run **Berlin World > Hackescher Markt > Create 1:1 Scene Rig** and press Play.

The importer intentionally does **not** download from or bypass the Berlin portal. The current mesh metadata uses provider-specific terms, so redistribution/commercial-game rights for the packed source geometry/textures must be checked against the terms you accepted.

See `Documentation~/EXACT_VISUAL_MODE.md` for the fidelity/storage/destruction design.

## Destruction with exact visuals

If semantic BWT tiles are supplied to the packer, above-ground source triangles are spatially associated with stable building IDs. When a `DestructibleBuilding` fractures, the corresponding triangles are removed from the exact visual mesh and its dense collider, while the lightweight procedural proxy generates debris at runtime. No pre-fractured photogrammetry city is stored.

The pre-damage visual can therefore be source-exact while destruction remains a game simulation rather than a claim about the building's real structural failure mode.

## Storage strategy

The semantic 1 km² layer remains tiny because it stores facts, not rendered geometry. Exact appearance inevitably costs more because photographic texture detail contains real information and cannot be losslessly replaced by a few kilobytes. v0.4 minimizes avoidable size by:

- retaining the portal's existing compressed image bytes instead of converting them to lossless textures;
- deduplicating identical textures by content hash;
- gzip-compressing the source geometry stream;
- storing only one visual mesh, not duplicate procedural render meshes;
- using semantic geometry as gameplay proxies rather than baking another collision city;
- generating destruction debris only when damage occurs.

## Formats

`BWT v2` stores compact semantic buildings, roads/rails, trees and surfaces with 2 cm local coordinate quantization. `BWM v1` stores exact-source visual geometry with float32 local coordinates, UVs, packed source normals, per-material index buffers and optional per-triangle semantic building ownership.

The C# readers are validated in CI against files produced by the Python packers.

## Licences / attribution

`DataSources/berlin_sources.json` records the intended source and licence role of each layer. OSM-derived semantic data requires `© OpenStreetMap contributors` attribution and applicable ODbL compliance. Official Berlin Open Data layers have their listed licences. The 2025 textured 3D mesh is not vendored in this repository because its current provider-specific terms must be checked for the intended distribution.
