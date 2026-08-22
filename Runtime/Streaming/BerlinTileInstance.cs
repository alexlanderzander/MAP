using BerlinWorld.Data;
using BerlinWorld.Destruction;
using BerlinWorld.Geo;
using BerlinWorld.Procedural;
using UnityEngine;

namespace BerlinWorld.Streaming
{
    public sealed class BerlinTileInstance : MonoBehaviour
    {
        private static readonly Color WallFallback = new(.72f,.69f,.63f);
        private static readonly Color RoofFallback = new(.30f,.25f,.22f);
        private bool _renderProceduralVisuals = true;

        public void Build(BerlinTileData tile, BerlinWorldSettings settings)
        {
            name = $"BerlinTile_{tile.TileX}_{tile.TileZ}";
            _renderProceduralVisuals = !settings.UsePhotogrammetryVisualLayer;
            BuildGround(tile, settings);
            if (tile.Surfaces.Count > 0) BuildSurfaces(tile, settings);
            if (tile.Roads.Count > 0) BuildRoadNetwork(tile, settings);
            foreach (BerlinBuildingData building in tile.Buildings) BuildBuilding(building, settings);
            if (settings.GenerateTrees && tile.Trees.Count > 0) BuildTrees(tile, settings);
        }

        private void BuildGround(BerlinTileData tile, BerlinWorldSettings settings)
        {
            Mesh mesh = SurfaceMeshBuilder.BuildGround(tile.TileSizeMeters);
            GameObject go = MakeMeshObject("Ground", mesh, new[]{ settings.GroundMaterial ?? BerlinMaterialFactory.Get("ground", new Color(.33f,.35f,.31f),0,.05f) });
            go.AddComponent<MeshCollider>().sharedMesh = mesh;
        }

        private void BuildSurfaces(BerlinTileData tile, BerlinWorldSettings settings)
        {
            BuildSurfaceGroup("Water", tile, x => x.Kind == 1, .025f, settings.WaterMaterial ?? BerlinMaterialFactory.Get("water", new Color(.18f,.34f,.42f),0,.72f));
            BuildSurfaceGroup("Green", tile, x => x.Kind is 2 or 3, .035f, settings.GrassMaterial ?? BerlinMaterialFactory.Get("grass", new Color(.25f,.38f,.20f),0,.05f));
            BuildSurfaceGroup("PavedAreas", tile, x => x.Kind is 4 or 5 or 6 or 7 or 8, .045f, settings.PavingMaterial ?? BerlinMaterialFactory.Get("paving", new Color(.46f,.45f,.42f),0,.08f));
        }

        private void BuildSurfaceGroup(string name, BerlinTileData tile, System.Func<BerlinSurfaceData,bool> filter, float y, Material material)
        {
            Mesh mesh = SurfaceMeshBuilder.Build(tile.Surfaces, filter, y, name);
            if (mesh.vertexCount == 0) { Destroy(mesh); return; }
            MakeMeshObject(name, mesh, new[]{ material });
        }

        private void BuildRoadNetwork(BerlinTileData tile, BerlinWorldSettings settings)
        {
            AddLayer("Roads", RoadMeshBuilder.BuildRoads(tile.Roads), settings.RoadMaterial ?? BerlinMaterialFactory.Get("asphalt", new Color(.14f,.14f,.14f),0,.18f));
            AddLayer("Footways", RoadMeshBuilder.BuildFootways(tile.Roads), settings.FootwayMaterial ?? BerlinMaterialFactory.Get("footway", new Color(.48f,.45f,.40f),0,.08f));
            AddLayer("Sidewalks", RoadMeshBuilder.BuildSidewalks(tile.Roads, settings.SidewalkWidthMeters), settings.SidewalkMaterial ?? BerlinMaterialFactory.Get("sidewalk", new Color(.55f,.53f,.49f),0,.08f));
            AddLayer("Rails", RoadMeshBuilder.BuildRails(tile.Roads), settings.RailMaterial ?? BerlinMaterialFactory.Get("rail", new Color(.2f,.2f,.2f),.75f,.55f));
        }

        private void AddLayer(string name, Mesh mesh, Material material)
        {
            if (mesh.vertexCount == 0) { Destroy(mesh); return; }
            MakeMeshObject(name, mesh, new[]{ material });
        }

        private void BuildBuilding(BerlinBuildingData building, BerlinWorldSettings settings)
        {
            var go = new GameObject($"Building_{building.Id}");
            go.transform.SetParent(transform, false);
            var filter = go.AddComponent<MeshFilter>();
            filter.sharedMesh = BuildingMeshBuilder.Build(building, settings.GenerateFacadeWindows);
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.enabled = _renderProceduralVisuals;
            renderer.sharedMaterials = new[]{
                settings.BuildingMaterial ?? BerlinMaterialFactory.Get("building", WallFallback,0,.12f),
                settings.RoofMaterial ?? BerlinMaterialFactory.Get("roof", RoofFallback,0,.1f),
                settings.WindowMaterial ?? BerlinMaterialFactory.Get("windows", new Color(.10f,.18f,.22f),.12f,.78f)
            };
            var block = new MaterialPropertyBlock();
            BerlinMaterialFactory.SetColor(block, BerlinPackedColor.DecodeRgb565(building.FacadeColorRgb565, BuildingClassColor(building.BuildingClass)));
            renderer.SetPropertyBlock(block, 0);
            block.Clear();
            BerlinMaterialFactory.SetColor(block, BerlinPackedColor.DecodeRgb565(building.RoofColorRgb565, RoofFallback));
            renderer.SetPropertyBlock(block, 1);
            if (settings.GenerateBuildingColliders)
            {
                var collider = go.AddComponent<MeshCollider>();
                collider.sharedMesh = filter.sharedMesh;
            }
            if (settings.EnableProceduralDestruction)
            {
                var destructible = go.AddComponent<DestructibleBuilding>();
                destructible.Initialize(building, settings.BuildingDamageThreshold);
            }
        }

        private void BuildTrees(BerlinTileData tile, BerlinWorldSettings settings)
        {
            Mesh mesh = TreeMeshBuilder.Build(tile.Trees);
            if (mesh.vertexCount == 0) { Destroy(mesh); return; }
            MakeMeshObject("Trees", mesh, new[]{
                settings.TreeTrunkMaterial ?? BerlinMaterialFactory.Get("trunk", new Color(.23f,.16f,.1f),0,.05f),
                settings.TreeCanopyMaterial ?? BerlinMaterialFactory.Get("canopy", new Color(.19f,.34f,.15f),0,.05f)
            });
        }

        private GameObject MakeMeshObject(string name, Mesh mesh, Material[] materials)
        {
            var go = new GameObject(name);
            go.transform.SetParent(transform, false);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.enabled = _renderProceduralVisuals;
            renderer.sharedMaterials = materials;
            return go;
        }

        private static Color BuildingClassColor(byte value) => value switch
        {
            1 => new Color(.72f,.68f,.60f),
            2 => new Color(.63f,.64f,.62f),
            3 => new Color(.55f,.56f,.55f),
            4 => new Color(.75f,.72f,.65f),
            5 => new Color(.68f,.60f,.50f),
            _ => WallFallback
        };

        private void OnDestroy()
        {
            foreach (MeshFilter filter in GetComponentsInChildren<MeshFilter>())
                if (filter.sharedMesh != null) Destroy(filter.sharedMesh);
        }
    }
}
