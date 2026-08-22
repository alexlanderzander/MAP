using System;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Text;
using UnityEngine;

namespace BerlinWorld.Photogrammetry
{
    [Serializable]
    public sealed class BerlinPhotogrammetryManifest
    {
        public string format = "";
        public int version;
        public string source = "";
        public string surveyDate = "";
        public string crs = "";
        public string axisMapping = "";
        public double originEasting;
        public double originNorthing;
        public double baseElevation;
        public int semanticBuildingOwners;
        public BerlinPhotogrammetryChunkManifest[] chunks = Array.Empty<BerlinPhotogrammetryChunkManifest>();
    }

    [Serializable]
    public sealed class BerlinPhotogrammetryChunkManifest
    {
        public string file = "";
        public string sourceObj = "";
        public int vertices;
        public int triangles;
        public int owners;
        public float[] boundsLocal = Array.Empty<float>();
        public BerlinPhotogrammetryMaterialManifest[] materials = Array.Empty<BerlinPhotogrammetryMaterialManifest>();
        public long compressedBytes;
    }

    [Serializable]
    public sealed class BerlinPhotogrammetryMaterialManifest
    {
        public string name = "";
        public float[] baseColor = Array.Empty<float>();
        public string texture = "";
    }

    public sealed class BwmChunkData
    {
        public Vector3[] Positions = Array.Empty<Vector3>();
        public Vector2[] UV = Array.Empty<Vector2>();
        public Vector3[] Normals = Array.Empty<Vector3>();
        public ulong[] OwnerIds = Array.Empty<ulong>();
        public BwmSubmeshData[] Submeshes = Array.Empty<BwmSubmeshData>();
        public double SourceOriginEasting;
        public double SourceOriginNorthing;
        public double BaseElevation;
        public Bounds Bounds;
        public bool HasSourceNormals;
    }

    public sealed class BwmSubmeshData
    {
        public int MaterialIndex;
        public int[] Indices = Array.Empty<int>();
        public ushort[] TriangleOwners = Array.Empty<ushort>();
    }

    public static class BwmReader
    {
        private const ushort SupportedVersion = 1;
        private const int MaxVertices = 50_000_000;
        private const int MaxSubmeshes = 16_384;
        private const int MaxOwners = 65_534;

        public static BwmChunkData ReadGzip(byte[] gzipBytes)
        {
            if (gzipBytes == null) throw new ArgumentNullException(nameof(gzipBytes));
            using var input = new MemoryStream(gzipBytes, false);
            using var gzip = new GZipStream(input, CompressionMode.Decompress, false);
            using var buffer = new MemoryStream();
            gzip.CopyTo(buffer);
            buffer.Position = 0;
            return Read(buffer);
        }

        public static BwmChunkData Read(Stream stream)
        {
            if (stream == null) throw new ArgumentNullException(nameof(stream));
            using var reader = new BinaryReader(stream, Encoding.UTF8, true);
            byte[] magic = ReadExact(reader, 4);
            if (magic[0] != (byte)'B' || magic[1] != (byte)'W' || magic[2] != (byte)'M' || magic[3] != (byte)'1')
                throw new InvalidDataException("Not a BWM1 photogrammetry chunk.");

            ushort version = reader.ReadUInt16();
            ushort flags = reader.ReadUInt16();
            uint vertexCountRaw = reader.ReadUInt32();
            uint submeshCountRaw = reader.ReadUInt32();
            ushort ownerCountRaw = reader.ReadUInt16();
            reader.ReadUInt16();
            double originE = reader.ReadDouble();
            double originN = reader.ReadDouble();
            double baseElevation = reader.ReadDouble();
            float minX = reader.ReadSingle();
            float minY = reader.ReadSingle();
            float minZ = reader.ReadSingle();
            float maxX = reader.ReadSingle();
            float maxY = reader.ReadSingle();
            float maxZ = reader.ReadSingle();

            if (version != SupportedVersion) throw new InvalidDataException($"Unsupported BWM version {version}.");
            if (vertexCountRaw > MaxVertices) throw new InvalidDataException($"Implausible BWM vertex count {vertexCountRaw}.");
            if (submeshCountRaw > MaxSubmeshes) throw new InvalidDataException($"Implausible BWM submesh count {submeshCountRaw}.");
            if (ownerCountRaw > MaxOwners) throw new InvalidDataException($"Implausible BWM owner count {ownerCountRaw}.");
            if (!(minX <= maxX && minY <= maxY && minZ <= maxZ)) throw new InvalidDataException("Invalid BWM bounds.");

            int vertexCount = checked((int)vertexCountRaw);
            int submeshCount = checked((int)submeshCountRaw);
            int ownerCount = ownerCountRaw;
            var positions = new Vector3[vertexCount];
            var uv = new Vector2[vertexCount];
            var normals = new Vector3[vertexCount];
            bool hasNormals = (flags & 1) != 0;

            for (int i = 0; i < vertexCount; i++)
            {
                float x = reader.ReadSingle();
                float y = reader.ReadSingle();
                float z = reader.ReadSingle();
                float u = reader.ReadSingle();
                float v = reader.ReadSingle();
                short nx = reader.ReadInt16();
                short ny = reader.ReadInt16();
                short nz = reader.ReadInt16();
                positions[i] = new Vector3(x, y, z);
                uv[i] = new Vector2(u, v);
                normals[i] = hasNormals ? new Vector3(nx / 32767f, ny / 32767f, nz / 32767f).normalized : Vector3.zero;
            }

            var owners = new ulong[ownerCount];
            for (int i = 0; i < ownerCount; i++) owners[i] = reader.ReadUInt64();

            var submeshes = new BwmSubmeshData[submeshCount];
            for (int s = 0; s < submeshCount; s++)
            {
                ushort materialIndex = reader.ReadUInt16();
                uint indexCountRaw = reader.ReadUInt32();
                if (indexCountRaw > (uint)(vertexCount * 12L)) throw new InvalidDataException($"Implausible BWM index count {indexCountRaw}.");
                int indexCount = checked((int)indexCountRaw);
                if (indexCount % 3 != 0) throw new InvalidDataException("BWM triangle index count must be divisible by three.");
                var indices = new int[indexCount];
                for (int i = 0; i < indexCount; i++)
                {
                    uint index = reader.ReadUInt32();
                    if (index >= vertexCountRaw) throw new InvalidDataException("BWM index outside vertex array.");
                    indices[i] = checked((int)index);
                }

                uint triangleOwnerCountRaw = reader.ReadUInt32();
                if (triangleOwnerCountRaw != indexCountRaw / 3) throw new InvalidDataException("BWM owner count does not match triangle count.");
                int triangleOwnerCount = checked((int)triangleOwnerCountRaw);
                var triangleOwners = new ushort[triangleOwnerCount];
                for (int i = 0; i < triangleOwnerCount; i++)
                {
                    ushort owner = reader.ReadUInt16();
                    if (owner > ownerCountRaw) throw new InvalidDataException("BWM triangle owner outside owner table.");
                    triangleOwners[i] = owner;
                }
                submeshes[s] = new BwmSubmeshData { MaterialIndex = materialIndex, Indices = indices, TriangleOwners = triangleOwners };
            }

            if (stream.ReadByte() != -1) throw new InvalidDataException("Unexpected trailing bytes in BWM chunk.");
            return new BwmChunkData
            {
                Positions = positions,
                UV = uv,
                Normals = normals,
                OwnerIds = owners,
                Submeshes = submeshes,
                SourceOriginEasting = originE,
                SourceOriginNorthing = originN,
                BaseElevation = baseElevation,
                Bounds = new Bounds(new Vector3((minX + maxX) * .5f, (minY + maxY) * .5f, (minZ + maxZ) * .5f), new Vector3(maxX - minX, maxY - minY, maxZ - minZ)),
                HasSourceNormals = hasNormals,
            };
        }

        private static byte[] ReadExact(BinaryReader reader, int count)
        {
            byte[] data = reader.ReadBytes(count);
            if (data.Length != count) throw new EndOfStreamException("Truncated BWM chunk.");
            return data;
        }
    }
}
