# Berlin World architecture

The project separates source truth, compact shipped data and runtime geometry.

```text
Official Berlin GIS / optional OSM fallback
        |
        | offline normalization
        v
EPSG:25833 features
        |
        | quantize + tile + gzip
        v
BWT1 tiles
        |
        | runtime generation
        v
Unity meshes, colliders, facades and destruction chunks
```

## Storage rules

1. Do not commit raw orthophotos, CityGML exports, OBJ city meshes or full GIS downloads.
2. Store building footprints and parameters instead of final triangles.
3. Use shared/procedural facade materials instead of unique textures per building.
4. Generate destruction fragments only after damage; do not store fracture meshes city-wide.
5. Reuse trees and props through instancing rather than duplicating mesh data.
6. Stream approximately 500 m tiles and unload distant geometry.
7. Keep high-resolution aerial imagery as authoring/reference input unless a deliberate shipped texture budget is approved.

## Accuracy

1 Unity unit equals 1 metre. Source coordinates are ETRS89 / UTM zone 33N (EPSG:25833), converted to local offsets from a configurable origin to retain float precision.

"Berlin today" is a composition of the newest compatible source layers. Different official layers have different acquisition dates, so every generated build should preserve a source manifest.

## Destruction

The v0.1 prototype stores no fracture geometry. Intact buildings are generated from footprints and heights. Once a threshold is reached, wall chunks are generated locally and given physics. Later versions should add structural cells, floors/interiors, debris pooling, damage persistence and localized road craters without changing the compact source representation.
