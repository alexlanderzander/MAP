using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using BerlinWorld.Destruction;
using BerlinWorld.Geo;
using BerlinWorld.Streaming;
using UnityEngine;
using UnityEngine.Networking;

namespace BerlinWorld.Photogrammetry
{
    [DisallowMultipleComponent]
    public sealed class BerlinPhotogrammetryStreamer : MonoBehaviour
    {
        public BerlinWorldSettings Settings;
        public string RelativeFolder = "Berlin/Photogrammetry";

        private readonly List<BerlinPhotogrammetryChunk> _chunks = new();
        private readonly Dictionary<string, Texture2D> _textures = new(StringComparer.OrdinalIgnoreCase);
        private readonly Dictionary<string, Material> _materials = new(StringComparer.Ordinal);
        private Coroutine _loadRoutine;

        private void OnEnable() { DestructibleBuilding.BuildingDestroyed += OnBuildingDestroyed; }
        private void OnDisable() { DestructibleBuilding.BuildingDestroyed -= OnBuildingDestroyed; }

        private void Start()
        {
            if (Settings == null || !Settings.UsePhotogrammetryVisualLayer) return;
            _loadRoutine = StartCoroutine(LoadWorld());
        }

        private IEnumerator LoadWorld()
        {
            string folder = Path.Combine(Application.streamingAssetsPath, RelativeFolder);
            string manifestPath = Path.Combine(folder, "photogrammetry_manifest.json");
            using var manifestRequest = UnityWebRequest.Get(ToUri(manifestPath));
            yield return manifestRequest.SendWebRequest();
            if (manifestRequest.result != UnityWebRequest.Result.Success)
            {
                Debug.LogError($"Berlin exact visual layer unavailable: {manifestRequest.error}. Falling back to procedural visuals.");
                FallbackToProcedural(); yield break;
            }

            BerlinPhotogrammetryManifest manifest;
            try
            {
                manifest = JsonUtility.FromJson<BerlinPhotogrammetryManifest>(manifestRequest.downloadHandler.text);
                if (manifest == null || manifest.format != "BWM1" || manifest.version != 1) throw new InvalidDataException("Unsupported photogrammetry manifest.");
            }
            catch (Exception ex)
            {
                Debug.LogError($"Berlin exact visual manifest is invalid: {ex.Message}");
                FallbackToProcedural(); yield break;
            }

            if (Math.Abs(manifest.originEasting - Settings.WorldOriginEasting) > .01 || Math.Abs(manifest.originNorthing - Settings.WorldOriginNorthing) > .01)
            {
                Debug.LogError("Berlin photogrammetry origin does not match BerlinWorldSettings; refusing to render a shifted city.");
                FallbackToProcedural(); yield break;
            }

            var root = new GameObject("Exact_2025_Photogrammetry");
            root.transform.SetParent(transform, false);
            foreach (BerlinPhotogrammetryChunkManifest chunkManifest in manifest.chunks ?? Array.Empty<BerlinPhotogrammetryChunkManifest>())
            {
                Material[] materials = new Material[Math.Max(1, chunkManifest.materials?.Length ?? 0)];
                if (chunkManifest.materials == null || chunkManifest.materials.Length == 0) materials[0] = GetFallbackMaterial();
                else
                {
                    for (int i = 0; i < chunkManifest.materials.Length; i++)
                    {
                        BerlinPhotogrammetryMaterialManifest sourceMaterial = chunkManifest.materials[i];
                        if (!string.IsNullOrEmpty(sourceMaterial.texture) && !_textures.ContainsKey(sourceMaterial.texture))
                        {
                            string texturePath = Path.Combine(folder, sourceMaterial.texture.Replace('/', Path.DirectorySeparatorChar));
                            using var textureRequest = UnityWebRequestTexture.GetTexture(ToUri(texturePath), true);
                            yield return textureRequest.SendWebRequest();
                            if (textureRequest.result == UnityWebRequest.Result.Success)
                            {
                                Texture2D texture = DownloadHandlerTexture.GetContent(textureRequest);
                                texture.name = Path.GetFileNameWithoutExtension(sourceMaterial.texture);
                                _textures[sourceMaterial.texture] = texture;
                            }
                            else Debug.LogWarning($"Could not load Berlin texture {sourceMaterial.texture}: {textureRequest.error}");
                        }
                        materials[i] = GetMaterial(sourceMaterial);
                    }
                }

                string chunkPath = Path.Combine(folder, chunkManifest.file);
                using var chunkRequest = UnityWebRequest.Get(ToUri(chunkPath));
                yield return chunkRequest.SendWebRequest();
                if (chunkRequest.result != UnityWebRequest.Result.Success)
                {
                    Debug.LogError($"Could not load Berlin photogrammetry chunk {chunkManifest.file}: {chunkRequest.error}");
                    continue;
                }
                try
                {
                    BwmChunkData data = BwmReader.ReadGzip(chunkRequest.downloadHandler.data);
                    var go = new GameObject(Path.GetFileNameWithoutExtension(Path.GetFileNameWithoutExtension(chunkManifest.file)));
                    go.transform.SetParent(root.transform, false);
                    var chunk = go.AddComponent<BerlinPhotogrammetryChunk>();
                    chunk.Initialize(data, materials, Settings.GeneratePhotogrammetryColliders);
                    _chunks.Add(chunk);
                }
                catch (Exception ex) { Debug.LogError($"Could not decode Berlin photogrammetry chunk {chunkManifest.file}: {ex.Message}"); }
            }

            if (_chunks.Count == 0) { Destroy(root); FallbackToProcedural(); yield break; }
            Debug.Log($"Berlin exact visual layer active: {_chunks.Count} source-mesh chunk(s), survey {manifest.surveyDate}.");
        }

        private Material GetMaterial(BerlinPhotogrammetryMaterialManifest source)
        {
            string colorKey = source.baseColor != null && source.baseColor.Length >= 3 ? $"{source.baseColor[0]:R},{source.baseColor[1]:R},{source.baseColor[2]:R}" : "1,1,1";
            string key = $"{source.texture}|{colorKey}";
            if (_materials.TryGetValue(key, out Material cached)) return cached;
            Shader shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("HDRP/Lit") ?? Shader.Find("Standard") ?? Shader.Find("Unlit/Texture");
            var material = new Material(shader) { name = $"BerlinExact_{source.name}" };
            Color color = Color.white;
            if (source.baseColor != null && source.baseColor.Length >= 3) color = new Color(source.baseColor[0], source.baseColor[1], source.baseColor[2], 1f);
            SetColor(material, color);
            if (!string.IsNullOrEmpty(source.texture) && _textures.TryGetValue(source.texture, out Texture2D texture))
            {
                if (material.HasProperty("_BaseMap")) material.SetTexture("_BaseMap", texture);
                if (material.HasProperty("_MainTex")) material.SetTexture("_MainTex", texture);
            }
            _materials[key] = material; return material;
        }

        private Material GetFallbackMaterial()
        {
            const string key = "__fallback__";
            if (_materials.TryGetValue(key, out Material cached)) return cached;
            Shader shader = Shader.Find("Universal Render Pipeline/Lit") ?? Shader.Find("HDRP/Lit") ?? Shader.Find("Standard") ?? Shader.Find("Unlit/Color");
            var material = new Material(shader) { name = "BerlinExact_Fallback" };
            SetColor(material, Color.white); _materials[key] = material; return material;
        }

        private static void SetColor(Material material, Color color)
        {
            if (material.HasProperty("_BaseColor")) material.SetColor("_BaseColor", color);
            if (material.HasProperty("_Color")) material.SetColor("_Color", color);
        }

        private void OnBuildingDestroyed(ulong buildingId)
        {
            foreach (BerlinPhotogrammetryChunk chunk in _chunks) if (chunk != null) chunk.RemoveBuilding(buildingId);
        }

        private void FallbackToProcedural()
        {
            if (Settings != null) Settings.UsePhotogrammetryVisualLayer = false;
            foreach (BerlinTileInstance tile in FindObjectsByType<BerlinTileInstance>(FindObjectsSortMode.None))
                foreach (MeshRenderer renderer in tile.GetComponentsInChildren<MeshRenderer>(true)) renderer.enabled = true;
        }

        private static string ToUri(string path)
        {
            string normalized = path.Replace('\\', '/');
            if (normalized.Contains("://", StringComparison.Ordinal)) return normalized;
            return new Uri(Path.GetFullPath(path)).AbsoluteUri;
        }

        private void OnDestroy()
        {
            if (_loadRoutine != null) StopCoroutine(_loadRoutine);
            foreach (Material material in _materials.Values) if (material != null) Destroy(material);
            foreach (Texture2D texture in _textures.Values) if (texture != null) Destroy(texture);
        }
    }
}
