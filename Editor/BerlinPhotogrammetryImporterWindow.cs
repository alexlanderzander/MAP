using System;
using System.Diagnostics;
using System.IO;
using System.Reflection;
using UnityEditor;
using UnityEditor.PackageManager;
using UnityEngine;

namespace BerlinWorld.Editor
{
    public sealed class BerlinPhotogrammetryImporterWindow : EditorWindow
    {
        private string _sourcePath = "";
        private string _python = "python";
        private bool _acceptedProviderTerms;
        private bool _bindDestruction = true;

        [MenuItem("Berlin World/Hackescher Markt/Import Exact Berlin Source Mesh")]
        public static void ShowWindow() => GetWindow<BerlinPhotogrammetryImporterWindow>("Berlin Exact Import");

        private void OnGUI()
        {
            EditorGUILayout.LabelField("Exact Berlin visual layer", EditorStyles.boldLabel);
            EditorGUILayout.HelpBox(
                "Select OBJ/ZIP files you obtained from the official Berlin 3D download portal. " +
                "This tool does not fetch or bypass the portal. It preserves source geometry/UVs and texture bytes, " +
                "then packs them into streamable BWM chunks for Unity.", MessageType.Info);

            using (new EditorGUILayout.HorizontalScope())
            {
                _sourcePath = EditorGUILayout.TextField("Portal export", _sourcePath);
                if (GUILayout.Button("Folder", GUILayout.Width(62)))
                {
                    string selected = EditorUtility.OpenFolderPanel("Berlin 3D OBJ/ZIP folder", _sourcePath, "");
                    if (!string.IsNullOrEmpty(selected)) _sourcePath = selected;
                }
                if (GUILayout.Button("ZIP", GUILayout.Width(48)))
                {
                    string selected = EditorUtility.OpenFilePanel("Berlin 3D portal ZIP", _sourcePath, "zip");
                    if (!string.IsNullOrEmpty(selected)) _sourcePath = selected;
                }
            }
            _python = EditorGUILayout.TextField("Python executable", _python);
            _bindDestruction = EditorGUILayout.ToggleLeft("Bind visual triangles to destructible semantic buildings", _bindDestruction);
            _acceptedProviderTerms = EditorGUILayout.ToggleLeft("I obtained these files under the provider terms and will verify redistribution rights", _acceptedProviderTerms);

            bool canRun = _acceptedProviderTerms && !string.IsNullOrWhiteSpace(_sourcePath) && (Directory.Exists(_sourcePath) || File.Exists(_sourcePath));
            using (new EditorGUI.DisabledScope(!canRun))
                if (GUILayout.Button("Pack + Install Exact Visual Layer")) PackAndInstall();
        }

        private void PackAndInstall()
        {
            string packageRoot = PackageInfo.FindForAssembly(typeof(BerlinPhotogrammetryImporterWindow).Assembly)?.resolvedPath;
            if (string.IsNullOrEmpty(packageRoot))
            {
                EditorUtility.DisplayDialog("Berlin World", "Could not locate the Berlin World package on disk.", "OK");
                return;
            }
            string script = Path.Combine(packageRoot, "tools", "photogrammetry", "prepare_photogrammetry.py");
            if (!File.Exists(script))
            {
                EditorUtility.DisplayDialog("Berlin World", $"Photogrammetry packer not found:\n{script}", "OK");
                return;
            }

            string projectRoot = Directory.GetParent(Application.dataPath)?.FullName ?? Application.dataPath;
            string destination = Path.Combine(Application.streamingAssetsPath, "Berlin", "Photogrammetry");
            string semantic = Path.Combine(Application.streamingAssetsPath, "Berlin", "Tiles");
            Directory.CreateDirectory(destination);

            string args = $"{Quote(script)} --input {Quote(_sourcePath)} --out {Quote(destination)} --clean";
            if (_bindDestruction && Directory.Exists(semantic)) args += $" --semantic-tiles {Quote(semantic)}";

            var start = new ProcessStartInfo
            {
                FileName = string.IsNullOrWhiteSpace(_python) ? "python" : _python,
                Arguments = args,
                WorkingDirectory = projectRoot,
                UseShellExecute = false,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true,
            };

            try
            {
                using Process process = Process.Start(start);
                if (process == null) throw new InvalidOperationException("Python process did not start.");
                string stdout = process.StandardOutput.ReadToEnd();
                string stderr = process.StandardError.ReadToEnd();
                process.WaitForExit();
                if (process.ExitCode != 0)
                {
                    UnityEngine.Debug.LogError($"Berlin exact import failed.\n{stdout}\n{stderr}");
                    EditorUtility.DisplayDialog("Berlin World", "Exact import failed. See Console for details.", "OK");
                    return;
                }
                UnityEngine.Debug.Log(stdout);
                AssetDatabase.Refresh();
                EditorUtility.DisplayDialog("Berlin World", "Exact Berlin source mesh packed and installed. Re-run Create 1:1 Scene Rig to enable exact mode.", "OK");
            }
            catch (Exception ex)
            {
                UnityEngine.Debug.LogException(ex);
                EditorUtility.DisplayDialog("Berlin World", $"Could not run the exact importer:\n{ex.Message}", "OK");
            }
        }

        private static string Quote(string value) => "\"" + value.Replace("\"", "\\\"") + "\"";
    }
}
