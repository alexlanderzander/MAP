using System;
using System.Collections.Generic;
using UnityEngine;
namespace BerlinWorld.Data
{
 [Serializable] public sealed class BerlinTileData { public int TileX; public int TileZ; public int TileSizeMeters; public double CenterEastingMeters; public double CenterNorthingMeters; public readonly List<BerlinBuildingData> Buildings=new(); public readonly List<BerlinRoadData> Roads=new(); public readonly List<BerlinTreeData> Trees=new(); public readonly List<BerlinSurfaceData> Surfaces=new(); }
 [Serializable] public sealed class BerlinBuildingData { public ulong Id; public float HeightMeters; public float MinHeightMeters; public byte RoofType; public byte BuildingClass; public byte Levels; public byte FacadeType; public float RoofHeightMeters; public ushort FacadeColorRgb565; public ushort RoofColorRgb565; public Vector2[] Footprint=Array.Empty<Vector2>(); }
 [Serializable] public sealed class BerlinRoadData { public ulong Id; public byte RoadClass; public byte Lanes; public float WidthMeters; public byte SurfaceType; public byte SidewalkMask; public byte Flags; public sbyte Layer; public Vector2[] Points=Array.Empty<Vector2>(); public bool IsBridge=>(Flags&1)!=0; public bool IsTunnel=>(Flags&2)!=0; public bool IsTram=>(Flags&4)!=0||RoadClass==10; public bool IsRail=>(Flags&8)!=0||RoadClass==11; public bool IsSteps=>(Flags&16)!=0; }
 [Serializable] public sealed class BerlinTreeData { public ulong Id; public Vector2 Position; public float HeightMeters; public float CrownMeters; public ushort SpeciesCode; }
 [Serializable] public sealed class BerlinSurfaceData { public ulong Id; public byte Kind; public byte MaterialType; public Vector2[] Footprint=Array.Empty<Vector2>(); }
 public static class BerlinPackedColor { public static Color DecodeRgb565(ushort packed,Color fallback) { if(packed==0)return fallback; float r=((packed>>11)&31)/31f,g=((packed>>5)&63)/63f,b=(packed&31)/31f; return new Color(r,g,b,1f); } }
}
