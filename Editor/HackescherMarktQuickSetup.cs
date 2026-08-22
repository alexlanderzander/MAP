using System.IO;
using BerlinWorld.Geo;
using BerlinWorld.Photogrammetry;
using BerlinWorld.Streaming;
using UnityEditor;
using UnityEngine;

namespace BerlinWorld.Editor
{
    public static class HackescherMarktQuickSetup
    {
        private const string Dir="Assets/BerlinGenerated";
        private const string SettingsPath=Dir+"/HackescherMarktSettings.asset";

        [MenuItem("Berlin World/Hackescher Markt/Create 1:1 Scene Rig")]
        public static void CreateSceneRig()
        {
            if(!AssetDatabase.IsValidFolder(Dir)) AssetDatabase.CreateFolder("Assets","BerlinGenerated");
            var settings=AssetDatabase.LoadAssetAtPath<BerlinWorldSettings>(SettingsPath);
            if(settings==null)
            {
                settings=ScriptableObject.CreateInstance<BerlinWorldSettings>();
                AssetDatabase.CreateAsset(settings,SettingsPath);
            }
            settings.WorldOriginEasting=391500;
            settings.WorldOriginNorthing=5820500;
            settings.TileSizeMeters=500;
            settings.LoadRadiusTiles=1;
            settings.UnloadRadiusTiles=2;

            string exactManifest=Path.Combine(Application.streamingAssetsPath,"Berlin","Photogrammetry","photogrammetry_manifest.json");
            settings.UsePhotogrammetryVisualLayer=File.Exists(exactManifest);

            GameObject root=GameObject.Find("BerlinWorld_HackescherMarkt")??new GameObject("BerlinWorld_HackescherMarkt");
            var streamer=root.GetComponent<BerlinWorldStreamer>()??root.AddComponent<BerlinWorldStreamer>();
            streamer.Settings=settings;
            var exact=root.GetComponent<BerlinPhotogrammetryStreamer>()??root.AddComponent<BerlinPhotogrammetryStreamer>();
            exact.Settings=settings;

            GameObject anchor=GameObject.Find("HackescherMarkt_PlayerAnchor")??new GameObject("HackescherMarkt_PlayerAnchor");
            anchor.transform.position=new Vector3(0,1.7f,0);
            streamer.Target=anchor.transform;

            Camera camera=Camera.main;
            if(camera==null)
            {
                var cameraObject=new GameObject("Main Camera");
                cameraObject.tag="MainCamera";
                camera=cameraObject.AddComponent<Camera>();
                cameraObject.AddComponent<AudioListener>();
                camera.transform.position=new Vector3(0,18,-35);
                camera.transform.rotation=Quaternion.Euler(18,0,0);
            }
            if(Object.FindFirstObjectByType<Light>()==null)
            {
                var lightObject=new GameObject("Berlin Sun");
                var light=lightObject.AddComponent<Light>();
                light.type=LightType.Directional;
                light.intensity=1.25f;
                lightObject.transform.rotation=Quaternion.Euler(42,-28,0);
            }

            Selection.activeObject=root;
            EditorUtility.SetDirty(settings);
            AssetDatabase.SaveAssets();
            string tileDir=Path.Combine(Application.streamingAssetsPath,"Berlin","Tiles");
            Debug.Log(settings.UsePhotogrammetryVisualLayer
                ? $"Hackescher Markt exact visual rig ready. Source mesh: {exactManifest}; semantic gameplay tiles: {tileDir}"
                : $"Hackescher Markt procedural rig ready. Install an official Berlin source mesh to enable exact visual mode. Semantic tiles: {tileDir}");
        }
    }
}
