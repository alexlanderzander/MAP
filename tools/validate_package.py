from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_BYTES = 5 * 1024 * 1024
FORBIDDEN_SUFFIXES = {".tif", ".tiff", ".las", ".laz", ".obj", ".fbx", ".gpkg", ".pbf"}


def main() -> int:
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    assert package["name"] == "com.alexlanderzander.berlin-world"
    assert package["unity"].startswith("6000.3")
    assert (ROOT / "Runtime" / "BerlinWorld.asmdef").exists()
    assert (ROOT / "Runtime" / "Data" / "BerlinTileReader.cs").exists()
    errors = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts:
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            errors.append(f"oversized repository file: {path.relative_to(ROOT)}")
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            errors.append(f"raw/generated geodata must not be committed: {path.relative_to(ROOT)}")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print("package structure and size budget OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
