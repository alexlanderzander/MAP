using BerlinWorld.Data;
using BerlinWorld.Destruction;
using BerlinWorld.Geo;
using BerlinWorld.Procedural;
using UnityEngine;

namespace BerlinWorld.Streaming
{
    public sealed class BerlinTileInstance : MonoBehaviour
    {
        public void Build(BerlinTileData tile, BerlinWorldSettings settings)
        {
            name = $"BerlinTile_{tile.TileX}_{tile.TileZ}";
            if (tile.Roads.Count > 0) BuildRoads(tile, settings);
            foreach (BerlinBuildingData building in tile.Buildings) BuildBuilding(building, settings);
        }

        private void BuildRoads(BerlinTileData tile, BerlinWorldSettings settings)
        {
            var go = new GameObject("Roads");
            go.transform.SetParent(transform, false);
            var filter = go.AddComponent<MeshFilter>();
            filter.sharedMesh = RoadMeshBuilder.Build(tile.Roads);
            go.AddComponent<MeshRenderer>().sharedMaterial = settings.RoadMaterial;
            go.AddComponent<MeshCollider>().sharedMesh = filter.sharedMesh;
        }

        private void BuildBuilding(BerlinBuildingData building, BerlinWorldSettings settings)
        {
            var go = new GameObject($"Building_{building.Id}");
            go.transform.SetParent(transform, false);
            var filter = go.AddComponent<MeshFilter>();
            filter.sharedMesh = BuildingMeshBuilder.Build(building);
            go.AddComponent<MeshRenderer>().sharedMaterial = settings.BuildingMaterial;
            if (settings.GenerateBuildingColliders) go.AddComponent<MeshCollider>().sharedMesh = filter.sharedMesh;
            if (settings.EnableProceduralDestruction)
            {
                var destructible = go.AddComponent<DestructibleBuilding>();
                destructible.Initialize(building, settings.BuildingDamageThreshold);
            }
        }

        private void OnDestroy()
        {
            foreach (MeshFilter filter in GetComponentsInChildren<MeshFilter>())
                if (filter.sharedMesh != null) Destroy(filter.sharedMesh);
        }
    }
}
