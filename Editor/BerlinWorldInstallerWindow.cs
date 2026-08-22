using System.IO;
using BerlinWorld.Geo;
using UnityEditor;
using UnityEngine;

namespace BerlinWorld.Editor
{
    public sealed class BerlinWorldInstallerWindow : EditorWindow
    {
        private DefaultAsset _generatedTilesFolder;
        private string _settingsPath = "Assets/BerlinWorld/BerlinWorldSettings.asset";

        [MenuItem("Berlin World/Install Generated Tiles")]
        public static void ShowWindow() => GetWindow<BerlinWorldInstallerWindow>("Berlin World");

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Install compact Berlin tiles", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox("Copies only compact .bwt.gz tiles into StreamingAssets; raw GIS data stays outside the game.", MessageType.Info);
            _generatedTilesFolder = (DefaultAsset)EditorGUILayout.ObjectField("Generated tile folder", _generatedTilesFolder, typeof(DefaultAsset), false);
            _settingsPath = EditorGUILayout.TextField("Settings asset", _settingsPath);
            using (new EditorGUI.DisabledScope(_generatedTilesFolder == null))
                if (GUILayout.Button("Install tiles + create settings")) Install();
        }

        private void Install()
        {
            string source = AssetDatabase.GetAssetPath(_generatedTilesFolder);
            if (!AssetDatabase.IsValidFolder(source))
            {
                EditorUtility.DisplayDialog("Berlin World", "Choose a project folder containing generated tiles.", "OK");
                return;
            }

            const string destination = "Assets/StreamingAssets/Berlin/Tiles";
            EnsureFolder("Assets/StreamingAssets");
            EnsureFolder("Assets/StreamingAssets/Berlin");
            EnsureFolder(destination);
            foreach (string file in Directory.GetFiles(source, "*.bwt.gz", SearchOption.TopDirectoryOnly))
                File.Copy(file, Path.Combine(destination, Path.GetFileName(file)), true);
            string manifest = Path.Combine(source, "manifest.json");
            if (File.Exists(manifest)) File.Copy(manifest, Path.Combine(destination, "manifest.json"), true);

            Directory.CreateDirectory(Path.GetDirectoryName(_settingsPath) ?? "Assets");
            var settings = AssetDatabase.LoadAssetAtPath<BerlinWorldSettings>(_settingsPath);
            if (settings == null)
            {
                settings = CreateInstance<BerlinWorldSettings>();
                AssetDatabase.CreateAsset(settings, _settingsPath);
            }
            AssetDatabase.Refresh();
            Selection.activeObject = settings;
            EditorGUIUtility.PingObject(settings);
        }

        private static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path)?.Replace('\\', '/');
            string name = Path.GetFileName(path);
            if (!string.IsNullOrEmpty(parent) && !AssetDatabase.IsValidFolder(parent)) EnsureFolder(parent);
            if (!string.IsNullOrEmpty(parent)) AssetDatabase.CreateFolder(parent, name);
        }
    }
}
