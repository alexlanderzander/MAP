using System;
using System.Collections.Generic;
using UnityEngine;

namespace BerlinWorld.Data
{
    [Serializable]
    public sealed class BerlinTileData
    {
        public int TileX;
        public int TileZ;
        public int TileSizeMeters;
        public double CenterEastingMeters;
        public double CenterNorthingMeters;
        public readonly List<BerlinBuildingData> Buildings = new();
        public readonly List<BerlinRoadData> Roads = new();
        public readonly List<BerlinTreeData> Trees = new();
    }

    [Serializable]
    public sealed class BerlinBuildingData
    {
        public ulong Id;
        public float HeightMeters;
        public float MinHeightMeters;
        public byte RoofType;
        public byte BuildingClass;
        public Vector2[] Footprint = Array.Empty<Vector2>();
    }

    [Serializable]
    public sealed class BerlinRoadData
    {
        public ulong Id;
        public byte RoadClass;
        public byte Lanes;
        public float WidthMeters;
        public Vector2[] Points = Array.Empty<Vector2>();
    }

    [Serializable]
    public sealed class BerlinTreeData
    {
        public ulong Id;
        public Vector2 Position;
        public float HeightMeters;
        public float CrownMeters;
        public ushort SpeciesCode;
    }
}
