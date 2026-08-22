# BWT1 compact tile format

BWT1 deliberately stores a **world description, not final meshes**. That is the main disk-size strategy.

Default tiles are 500 x 500 m in ETRS89 / UTM zone 33N (EPSG:25833). Positions are signed 16-bit offsets from the tile centre at 2 cm resolution, and each tile is gzip-compressed.

Stored data:
- Buildings: stable 64-bit ID, height, minimum height, class, roof type and footprint polygon.
- Roads: stable 64-bit ID, class, lanes, width and centre-line polyline.
- Trees: stable 64-bit ID, local position, height, crown diameter and compact species code.

Not stored:
- per-building triangle meshes,
- duplicate collision meshes,
- city-wide fracture meshes,
- unique facade textures,
- duplicate prop geometry.

Unity regenerates geometry from the compact features. This is usually far smaller than compressing an already-expanded city mesh.

## v0.1 limitations

- Polygon holes are not represented yet.
- The packer keeps only the largest outer ring of a MultiPolygon.
- Features must fit the signed local-coordinate range; production ingestion will clip/split long roads at tile boundaries.
- Terrain is planned as a separate quantized height-tile format so its resolution can be tuned independently.
- Roof type metadata is stored, but v0.1 rendering still uses flat tops. Proper LoD2 generalized roof reconstruction is a next milestone.
