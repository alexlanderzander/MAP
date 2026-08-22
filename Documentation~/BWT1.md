# BWT compact Berlin tile format

`BWT1` is the file magic. The current wire version is **2** and the C# reader remains compatible with version 1. All numeric fields are little-endian. Local X/Z positions are signed 16-bit integers at the header quantization (currently **2 cm**) relative to the tile centre.

## Header

```text
4s magic=BWT1
u16 version=2
u16 quantization_cm=2
u16 tile_size_m
u16 surface_count   # reserved/zero in v1
s32 tile_x
s32 tile_z
f64 center_easting
f64 center_northing
u32 building_count
u32 road_count
u32 tree_count
```

## Building v2

`u64 id, u16 height, u16 min_height, u8 roof_type, u8 class, u16 point_count, u8 levels, u8 facade_type, u16 roof_height, u16 facade_rgb565, u16 roof_rgb565`, followed by signed 16-bit local X/Z point pairs.

## Road v2

`u64 id, u8 class, u8 lanes, u16 width, u16 point_count, u8 surface, u8 sidewalk_mask, u8 flags, s8 layer`, followed by local X/Z pairs. Flags encode bridge/tunnel/tram/rail/steps.

## Tree

Tree layout is unchanged from v1: ID, local X/Z, height, crown diameter and compact species code.

## Surface v2

`u64 id, u8 kind, u8 material, u16 point_count`, followed by local X/Z pairs. Surface polygons are clipped to tile boundaries before packing.

## Compression

Each tile is gzip-compressed with deterministic `mtime=0`. Render meshes are intentionally not part of the format; facade windows, roofs, sidewalks, rails and trees are expanded in Unity at runtime/editor time rather than duplicated on disk.
