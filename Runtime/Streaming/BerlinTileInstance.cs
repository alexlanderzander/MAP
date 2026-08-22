using BerlinWorld.Data;
using BerlinWorld.Destruction;
using BerlinWorld.Geo;
using BerlinWorld.Procedural;
using UnityEngine;
namespace BerlinWorld.Streaming
{
 public sealed class BerlinTileInstance:MonoBehaviour
 {
  static readonly Color WallFallback=new(.72f,.69f,.63f),RoofFallback=new(.30f,.25f,.22f);
  public void Build(BerlinTileData tile,BerlinWorldSettings settings){name=$"BerlinTile_{tile.TileX}_{tile.TileZ}";BuildGround(tile,settings);if(tile.Surfaces.Count>0)BuildSurfaces(tile,settings);if(tile.Roads.Count>0)BuildRoadNetwork(tile,settings);foreach(var b in tile.Buildings)BuildBuilding(b,settings);if(settings.GenerateTrees&&tile.Trees.Count>0)BuildTrees(tile,settings);}
  void BuildGround(BerlinTileData tile,BerlinWorldSettings s){Mesh m=SurfaceMeshBuilder.BuildGround(tile.TileSizeMeters);GameObject go=MakeMeshObject("Ground",m,new[]{s.GroundMaterial??BerlinMaterialFactory.Get("ground",new Color(.33f,.35f,.31f),0,.05f)});go.AddComponent<MeshCollider>().sharedMesh=m;}
  void BuildSurfaces(BerlinTileData tile,BerlinWorldSettings s){BuildSurfaceGroup("Water",tile,x=>x.Kind==1,.025f,s.WaterMaterial??BerlinMaterialFactory.Get("water",new Color(.18f,.34f,.42f),0,.72f));BuildSurfaceGroup("Green",tile,x=>x.Kind is 2 or 3,.035f,s.GrassMaterial??BerlinMaterialFactory.Get("grass",new Color(.25f,.38f,.20f),0,.05f));BuildSurfaceGroup("PavedAreas",tile,x=>x.Kind is 4 or 5 or 6 or 7 or 8,.045f,s.PavingMaterial??BerlinMaterialFactory.Get("paving",new Color(.46f,.45f,.42f),0,.08f));}
  void BuildSurfaceGroup(string n,BerlinTileData tile,System.Func<BerlinSurfaceData,bool> f,float y,Material mat){Mesh m=SurfaceMeshBuilder.Build(tile.Surfaces,f,y,n);if(m.vertexCount==0){Destroy(m);return;}MakeMeshObject(n,m,new[]{mat});}
  void BuildRoadNetwork(BerlinTileData tile,BerlinWorldSettings s){AddLayer("Roads",RoadMeshBuilder.BuildRoads(tile.Roads),s.RoadMaterial??BerlinMaterialFactory.Get("asphalt",new Color(.14f,.14f,.14f),0,.18f));AddLayer("Footways",RoadMeshBuilder.BuildFootways(tile.Roads),s.FootwayMaterial??BerlinMaterialFactory.Get("footway",new Color(.48f,.45f,.40f),0,.08f));AddLayer("Sidewalks",RoadMeshBuilder.BuildSidewalks(tile.Roads,s.SidewalkWidthMeters),s.SidewalkMaterial??BerlinMaterialFactory.Get("sidewalk",new Color(.55f,.53f,.49f),0,.08f));AddLayer("Rails",RoadMeshBuilder.BuildRails(tile.Roads),s.RailMaterial??BerlinMaterialFactory.Get("rail",new Color(.2f,.2f,.2f),.75f,.55f));}
  void AddLayer(string n,Mesh m,Material mat){if(m.vertexCount==0){Destroy(m);return;}MakeMeshObject(n,m,new[]{mat});}
  void BuildBuilding(BerlinBuildingData b,BerlinWorldSettings s){var go=new GameObject($"Building_{b.Id}");go.transform.SetParent(transform,false);var mf=go.AddComponent<MeshFilter>();mf.sharedMesh=BuildingMeshBuilder.Build(b,s.GenerateFacadeWindows);var mr=go.AddComponent<MeshRenderer>();mr.sharedMaterials=new[]{s.BuildingMaterial??BerlinMaterialFactory.Get("building",WallFallback,0,.12f),s.RoofMaterial??BerlinMaterialFactory.Get("roof",RoofFallback,0,.1f),s.WindowMaterial??BerlinMaterialFactory.Get("windows",new Color(.10f,.18f,.22f),.12f,.78f)};var block=new MaterialPropertyBlock();BerlinMaterialFactory.SetColor(block,BerlinPackedColor.DecodeRgb565(b.FacadeColorRgb565,BuildingClassColor(b.BuildingClass)));mr.SetPropertyBlock(block,0);block.Clear();BerlinMaterialFactory.SetColor(block,BerlinPackedColor.DecodeRgb565(b.RoofColorRgb565,RoofFallback));mr.SetPropertyBlock(block,1);if(s.GenerateBuildingColliders){var c=go.AddComponent<MeshCollider>();c.sharedMesh=mf.sharedMesh;}if(s.EnableProceduralDestruction){var d=go.AddComponent<DestructibleBuilding>();d.Initialize(b,s.BuildingDamageThreshold);}}
  void BuildTrees(BerlinTileData tile,BerlinWorldSettings s){Mesh m=TreeMeshBuilder.Build(tile.Trees);if(m.vertexCount==0){Destroy(m);return;}MakeMeshObject("Trees",m,new[]{s.TreeTrunkMaterial??BerlinMaterialFactory.Get("trunk",new Color(.23f,.16f,.1f),0,.05f),s.TreeCanopyMaterial??BerlinMaterialFactory.Get("canopy",new Color(.19f,.34f,.15f),0,.05f)});}
  GameObject MakeMeshObject(string n,Mesh m,Material[] mats){var go=new GameObject(n);go.transform.SetParent(transform,false);go.AddComponent<MeshFilter>().sharedMesh=m;go.AddComponent<MeshRenderer>().sharedMaterials=mats;return go;}
  static Color BuildingClassColor(byte c)=>c switch{1=>new Color(.72f,.68f,.60f),2=>new Color(.63f,.64f,.62f),3=>new Color(.55f,.56f,.55f),4=>new Color(.75f,.72f,.65f),5=>new Color(.68f,.60f,.50f),_=>WallFallback};
  void OnDestroy(){foreach(var f in GetComponentsInChildren<MeshFilter>())if(f.sharedMesh!=null)Destroy(f.sharedMesh);}
 }
}
