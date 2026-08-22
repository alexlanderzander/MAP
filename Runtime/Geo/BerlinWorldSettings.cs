using UnityEngine;

namespace BerlinWorld.Geo
{
    [CreateAssetMenu(menuName = "Berlin World/World Settings", fileName = "BerlinWorldSettings")]
    public sealed class BerlinWorldSettings : ScriptableObject
    {
        [Header("Coordinate system")]
        public double WorldOriginEasting = 392000.0;
        public double WorldOriginNorthing = 5820000.0;
        [Min(100)] public int TileSizeMeters = 500;

        [Header("Streaming")]
        [Min(0)] public int LoadRadiusTiles = 1;
        [Min(1)] public int UnloadRadiusTiles = 2;
        [Min(0.05f)] public float PollIntervalSeconds = 0.35f;

        [Header("Rendering")]
        public Material BuildingMaterial;
        public Material RoadMaterial;
        public bool GenerateBuildingColliders = true;
        public bool EnableProceduralDestruction = true;
        [Min(1f)] public float BuildingDamageThreshold = 100f;
    }
}
