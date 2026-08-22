using UnityEngine;
namespace BerlinWorld.Geo
{
    [CreateAssetMenu(menuName="Berlin World/World Settings",fileName="BerlinWorldSettings")]
    public sealed class BerlinWorldSettings:ScriptableObject
    {
        [Header("Coordinate system")]
        public double WorldOriginEasting=391500.0;
        public double WorldOriginNorthing=5820500.0;
        [Min(100)] public int TileSizeMeters=500;

        [Header("Streaming")]
        [Min(0)] public int LoadRadiusTiles=1;
        [Min(1)] public int UnloadRadiusTiles=2;
        [Min(.05f)] public float PollIntervalSeconds=.35f;

        [Header("Exact visual layer")]
        [Tooltip("Render packed official Berlin source mesh instead of the procedural visual shell. Semantic tiles still provide gameplay proxies.")]
        public bool UsePhotogrammetryVisualLayer=false;
        [Tooltip("Use the dense source mesh as static collision. Accurate but more expensive than semantic proxy colliders.")]
        public bool GeneratePhotogrammetryColliders=true;

        [Header("Geometry")]
        public bool GenerateBuildingColliders=true;
        public bool GenerateFacadeWindows=true;
        public bool GenerateTrees=true;
        public bool EnableProceduralDestruction=true;
        [Min(1f)] public float BuildingDamageThreshold=100f;
        [Min(.8f)] public float SidewalkWidthMeters=1.8f;

        [Header("Optional materials (automatic fallbacks are used when empty)")]
        public Material BuildingMaterial;
        public Material RoofMaterial;
        public Material WindowMaterial;
        public Material RoadMaterial;
        public Material FootwayMaterial;
        public Material SidewalkMaterial;
        public Material RailMaterial;
        public Material GroundMaterial;
        public Material WaterMaterial;
        public Material GrassMaterial;
        public Material PavingMaterial;
        public Material TreeTrunkMaterial;
        public Material TreeCanopyMaterial;
    }
}
