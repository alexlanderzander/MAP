using System.IO;
using System.IO.Compression;
using System.Text;
using UnityEngine;

namespace BerlinWorld.Data
{
    public static class BerlinTileReader
    {
        public static BerlinTileData ReadGzip(byte[] gzipBytes)
        {
            using var input = new MemoryStream(gzipBytes, false);
            using var gzip = new GZipStream(input, CompressionMode.Decompress, false);
            using var buffer = new MemoryStream();
            gzip.CopyTo(buffer);
            buffer.Position = 0;
            return Read(buffer);
        }

        public static BerlinTileData Read(Stream stream)
        {
            using var reader = new BinaryReader(stream, Encoding.UTF8, true);
            byte[] magic = reader.ReadBytes(4);
            if (magic.Length != 4 || magic[0] != (byte)'B' || magic[1] != (byte)'W' || magic[2] != (byte)'T' || magic[3] != (byte)'1')
                throw new InvalidDataException("Not a BWT1 tile.");

            ushort version = reader.ReadUInt16();
            ushort quantCm = reader.ReadUInt16();
            ushort tileSize = reader.ReadUInt16();
            reader.ReadUInt16();
            int tileX = reader.ReadInt32();
            int tileZ = reader.ReadInt32();
            double centerE = reader.ReadDouble();
            double centerN = reader.ReadDouble();
            uint buildingCount = reader.ReadUInt32();
            uint roadCount = reader.ReadUInt32();
            uint treeCount = reader.ReadUInt32();

            if (version != 1) throw new InvalidDataException($"Unsupported BWT version {version}.");
            float scale = quantCm / 100f;
            var tile = new BerlinTileData
            {
                TileX = tileX,
                TileZ = tileZ,
                TileSizeMeters = tileSize,
                CenterEastingMeters = centerE,
                CenterNorthingMeters = centerN,
            };

            for (uint i = 0; i < buildingCount; i++)
            {
                var b = new BerlinBuildingData
                {
                    Id = reader.ReadUInt64(),
                    HeightMeters = reader.ReadUInt16() * scale,
                    MinHeightMeters = reader.ReadUInt16() * scale,
                    RoofType = reader.ReadByte(),
                    BuildingClass = reader.ReadByte(),
                };
                ushort count = reader.ReadUInt16();
                b.Footprint = ReadPoints(reader, count, scale);
                tile.Buildings.Add(b);
            }

            for (uint i = 0; i < roadCount; i++)
            {
                var r = new BerlinRoadData
                {
                    Id = reader.ReadUInt64(),
                    RoadClass = reader.ReadByte(),
                    Lanes = reader.ReadByte(),
                    WidthMeters = reader.ReadUInt16() * scale,
                };
                ushort count = reader.ReadUInt16();
                r.Points = ReadPoints(reader, count, scale);
                tile.Roads.Add(r);
            }

            for (uint i = 0; i < treeCount; i++)
            {
                ulong id = reader.ReadUInt64();
                short x = reader.ReadInt16();
                short z = reader.ReadInt16();
                ushort height = reader.ReadUInt16();
                ushort crown = reader.ReadUInt16();
                ushort species = reader.ReadUInt16();
                tile.Trees.Add(new BerlinTreeData
                {
                    Id = id,
                    Position = new Vector2(x * scale, z * scale),
                    HeightMeters = height * scale,
                    CrownMeters = crown * scale,
                    SpeciesCode = species,
                });
            }
            return tile;
        }

        private static Vector2[] ReadPoints(BinaryReader reader, int count, float scale)
        {
            var result = new Vector2[count];
            for (int i = 0; i < count; i++)
                result[i] = new Vector2(reader.ReadInt16() * scale, reader.ReadInt16() * scale);
            return result;
        }
    }
}
