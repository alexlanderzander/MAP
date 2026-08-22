# Hackescher Markt 1 km² 3D validation area

## Bounds and scale

The area is exactly `391000,5820000 → 392000,5821000` in `EPSG:25833`, split into four 500 m BWT tiles (`x=782..783`, `z=11640..11641`). Unity's origin is set to the area centre (`391500,5820500`) and **1 Unity unit = 1 metre**.

## What v0.3 constructs in 3D

Buildings are extruded from real source footprints. Tagged levels, heights, roof shape/height, facade material and colours are packed when available. Unity generates wall/roof submeshes and repeating window geometry at runtime. Non-flat roofs receive lightweight generated roof volumes; these are visual approximations until current Berlin LoD2 roof planes can be ingested again.

Road semantics include width, surface type, sidewalks, bridge/tunnel flags, level, tram and rail. The runtime creates separate road, footway, sidewalk and rail meshes. OSM area features add parks, grass, water, pedestrian/plaza/parking surfaces. Mapped trees are emitted as one combined two-material mesh per tile rather than one GameObject per tree.

A flat tile ground currently underlies the scene. Official Berlin DGM1 remains the intended elevation source; the live GDI endpoint was returning its maintenance page during this milestone. The architecture keeps ground generation isolated so DGM elevation can replace the flat base without changing building IDs or horizontal coordinates.

## Destruction

Buildings remain static during ordinary streaming. When their damage threshold is reached, `DestructibleBuilding` disables the intact renderer/collider and generates local wall chunks on demand. This keeps fracture geometry off disk. The current model is gameplay destruction, not engineering-grade structural simulation.

## Build

```bash
python tools/berlin_pipeline/build_area.py \
  --area DataSources/hackescher_markt_area.json \
  --out GeneratedBerlin/HackescherMarkt/Tiles
```

Every build writes `manifest.json`, `source_manifest.json` and four `tile_*.bwt.gz` files. Generated data is intentionally outside normal Git. CI uploads the same folder as `HackescherMarkt-Unity-Tiles`.

## Fidelity limits that cannot be invented

The pipeline must not fabricate claims of survey accuracy where the public data lacks detail. Exact contemporary facade ornament, every window/balcony/shop sign, interiors, utility infrastructure and every roof plane are not universally present in the live sources. Procedural details are generated deterministically to make the world game-ready while geographic position/scale remain tied to source geometry.

For unique landmarks or hero facades, use separately licensed/manual high-detail assets and keep the BWT footprint/ID as the placement anchor. This gives high visual quality without duplicating the whole city as textured meshes.
