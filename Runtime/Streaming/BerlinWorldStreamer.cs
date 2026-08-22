using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using BerlinWorld.Data;
using BerlinWorld.Geo;
using UnityEngine;
using UnityEngine.Networking;

namespace BerlinWorld.Streaming
{
    [DisallowMultipleComponent]
    public sealed class BerlinWorldStreamer : MonoBehaviour
    {
        public Transform Target;
        public BerlinWorldSettings Settings;

        private readonly Dictionary<Vector2Int, BerlinTileInstance> _loaded = new();
        private readonly HashSet<Vector2Int> _loading = new();
        private readonly HashSet<Vector2Int> _missing = new();
        private float _nextPoll;

        private void Start()
        {
            if (Target == null && Camera.main != null) Target = Camera.main.transform;
        }

        private void Update()
        {
            if (Settings == null || Target == null || Time.unscaledTime < _nextPoll) return;
            _nextPoll = Time.unscaledTime + Settings.PollIntervalSeconds;
            Refresh();
        }

        private void Refresh()
        {
            Vector2Int center = BerlinCoordinates.UnityToTile(Target.position, Settings);
            int loadRadius = Mathf.Max(0, Settings.LoadRadiusTiles);
            for (int dz = -loadRadius; dz <= loadRadius; dz++)
            for (int dx = -loadRadius; dx <= loadRadius; dx++)
            {
                var key = new Vector2Int(center.x + dx, center.y + dz);
                if (!_loaded.ContainsKey(key) && !_loading.Contains(key) && !_missing.Contains(key))
                    StartCoroutine(LoadTile(key));
            }

            int unloadRadius = Mathf.Max(loadRadius + 1, Settings.UnloadRadiusTiles);
            var toUnload = new List<Vector2Int>();
            foreach (var pair in _loaded)
                if (Mathf.Abs(pair.Key.x - center.x) > unloadRadius || Mathf.Abs(pair.Key.y - center.y) > unloadRadius)
                    toUnload.Add(pair.Key);

            foreach (Vector2Int key in toUnload)
            {
                if (_loaded.Remove(key, out BerlinTileInstance instance) && instance != null)
                    Destroy(instance.gameObject);
            }
        }

        private IEnumerator LoadTile(Vector2Int key)
        {
            _loading.Add(key);
            string filename = $"tile_{key.x}_{key.y}.bwt.gz";
            string path = Path.Combine(Application.streamingAssetsPath, "Berlin", "Tiles", filename);
            string uri = path.Contains("://", StringComparison.Ordinal) ? path : new Uri(Path.GetFullPath(path)).AbsoluteUri;
            using var request = UnityWebRequest.Get(uri);
            yield return request.SendWebRequest();
            _loading.Remove(key);

            if (request.result != UnityWebRequest.Result.Success)
            {
                _missing.Add(key);
                yield break;
            }

            BerlinTileData tile;
            try { tile = BerlinTileReader.ReadGzip(request.downloadHandler.data); }
            catch (Exception ex)
            {
                Debug.LogError($"Failed to decode {filename}: {ex.Message}");
                _missing.Add(key);
                yield break;
            }

            var go = new GameObject();
            go.transform.SetParent(transform, false);
            go.transform.position = BerlinCoordinates.UtmToUnity(tile.CenterEastingMeters, 0, tile.CenterNorthingMeters, Settings);
            var instance = go.AddComponent<BerlinTileInstance>();
            instance.Build(tile, Settings);
            _loaded[key] = instance;
        }

        public void ForgetMissingTiles() => _missing.Clear();
    }
}
