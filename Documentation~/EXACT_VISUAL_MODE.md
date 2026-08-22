# Hackescher Markt exact visual mode

The exact visual mode is deliberately different from the procedural fallback. The procedural BWT layer stays tiny and supplies stable building IDs, gameplay collision proxies, roads, navigation semantics and destruction triggers. The visible city can instead come directly from the official Berlin textured 3D mesh.

## Fidelity rule

The packer does not simplify source OBJ triangles, resample UVs, recompress image files or invent facade details. It translates georeferenced coordinates to a local Unity origin and stores position/UV data as float32, packed source normals and 32-bit indices in gzip-compressed `BWM1` chunks. Texture files are copied byte-for-byte and deduplicated by content hash.

That makes Unity reproduce the supplied source mesh rather than regenerate the appearance from footprints. It does **not** turn a June 2025 aerial survey into a literal August 2026 scan, nor can aerial photogrammetry contain unseen interiors or hidden surfaces.

## Import

1. Download the required Hackescher Markt tiles from the official Berlin 3D Downloadportal and accept the provider's current terms there.
2. Install/generate the compact semantic `BWT` tiles first.
3. In Unity choose **Berlin World > Hackescher Markt > Import Exact Berlin Source Mesh**.
4. Select the folder containing the downloaded OBJ files or ZIP files.
5. Keep destruction binding enabled and run **Pack + Install Exact Visual Layer**.
6. Re-run **Berlin World > Hackescher Markt > Create 1:1 Scene Rig**.

The importer never contacts the Berlin portal. This is intentional: the portal requires acceptance of its provider terms and current Berlin Open Data metadata classifies the 2025 mesh under a provider-specific license. The user is responsible for checking whether the intended game distribution is permitted.

## Destruction

When semantic BWT tiles are available during packing, each above-ground source triangle is spatially associated with a stable building ID. At runtime the exact source triangles for that building are removed when the gameplay building fractures. The existing procedural proxy produces debris on demand; no pre-fractured city mesh is stored.

The destruction result is a game simulation, not a structural-engineering model of the real building. Exact visual appearance before damage and exact real-world structural failure are separate problems.

## Storage

Exact source appearance necessarily costs more than the ~100 KB semantic representation because the source photographs/textures contain the visible detail. The package minimizes avoidable growth by keeping source image compression, deduplicating identical textures, gzip-compressing geometry, avoiding baked collision copies, and generating destruction debris only when needed.
