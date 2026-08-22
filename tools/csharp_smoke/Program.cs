using BerlinWorld.Data;

if (args.Length != 1) return 2;
BerlinTileData tile = BerlinTileReader.ReadGzip(File.ReadAllBytes(args[0]));
if (tile.Buildings.Count != 1 || tile.Roads.Count != 1 || tile.Trees.Count != 2)
    throw new Exception($"unexpected sample counts: b={tile.Buildings.Count} r={tile.Roads.Count} t={tile.Trees.Count}");
if (Math.Abs(tile.Buildings[0].HeightMeters - 27.5f) > 0.021f) throw new Exception("building height decode mismatch");
if (Math.Abs(tile.Roads[0].WidthMeters - 8.0f) > 0.021f) throw new Exception("road width decode mismatch");
if (Math.Abs(tile.Trees[0].HeightMeters - 11.0f) > 0.021f) throw new Exception("tree height decode mismatch");
Console.WriteLine($"C# BWT1 decoder OK: tile {tile.TileX},{tile.TileZ}");
return 0;
