using System.IO;
using BerlinWorld.Geo;
using BerlinWorld.Streaming;
using UnityEditor;
using UnityEngine;
namespace BerlinWorld.Editor
{
 public static class HackescherMarktQuickSetup
 {
  const string Dir="Assets/BerlinGenerated",SettingsPath=Dir+"/HackescherMarktSettings.asset";
  [MenuItem("Berlin World/Hackescher Markt/Create 1:1 Scene Rig")]
  public static void CreateSceneRig(){if(!AssetDatabase.IsValidFolder(Dir))AssetDatabase.CreateFolder("Assets","BerlinGenerated");var settings=AssetDatabase.LoadAssetAtPath<BerlinWorldSettings>(SettingsPath);if(settings==null){settings=ScriptableObject.CreateInstance<BerlinWorldSettings>();settings.WorldOriginEasting=391500;settings.WorldOriginNorthing=5820500;settings.TileSizeMeters=500;settings.LoadRadiusTiles=1;settings.UnloadRadiusTiles=2;AssetDatabase.CreateAsset(settings,SettingsPath);}GameObject root=GameObject.Find("BerlinWorld_HackescherMarkt")??new GameObject("BerlinWorld_HackescherMarkt");var streamer=root.GetComponent<BerlinWorldStreamer>()??root.AddComponent<BerlinWorldStreamer>();streamer.Settings=settings;GameObject anchor=GameObject.Find("HackescherMarkt_PlayerAnchor")??new GameObject("HackescherMarkt_PlayerAnchor");anchor.transform.position=new Vector3(0,1.7f,0);streamer.Target=anchor.transform;Camera camera=Camera.main;if(camera==null){var cg=new GameObject("Main Camera");cg.tag="MainCamera";camera=cg.AddComponent<Camera>();cg.AddComponent<AudioListener>();camera.transform.position=new Vector3(0,18,-35);camera.transform.rotation=Quaternion.Euler(18,0,0);}if(Object.FindFirstObjectByType<Light>()==null){var lg=new GameObject("Berlin Sun");var light=lg.AddComponent<Light>();light.type=LightType.Directional;light.intensity=1.25f;lg.transform.rotation=Quaternion.Euler(42,-28,0);}Selection.activeObject=root;EditorUtility.SetDirty(settings);string tileDir=Path.Combine(Application.dataPath,"StreamingAssets","Berlin","Tiles");Debug.Log($"Hackescher Markt 1:1 scene rig ready. Tile directory: {tileDir}");}
 }
}
