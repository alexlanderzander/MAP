using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace BerlinWorld.Photogrammetry
{
    [DisallowMultipleComponent]
    public sealed class BerlinPhotogrammetryChunk : MonoBehaviour
    {
        private BwmChunkData _data;
        private Mesh _mesh;
        private MeshRenderer _renderer;
        private MeshCollider _collider;
        private readonly HashSet<ulong> _ownedBuildingIds = new();
        private readonly HashSet<ulong> _destroyedBuildingIds = new();

        public void Initialize(BwmChunkData data, Material[] materials, bool generateCollider)
        {
            _data = data;
            _ownedBuildingIds.Clear();
            foreach (ulong id in data.OwnerIds) _ownedBuildingIds.Add(id);

            _mesh = new Mesh { name = "BerlinPhotogrammetry" };
            if (data.Positions.Length > 65535) _mesh.indexFormat = IndexFormat.UInt32;
            _mesh.vertices = data.Positions;
            _mesh.uv = data.UV;
            _mesh.subMeshCount = data.Submeshes.Length;
            for (int s = 0; s < data.Submeshes.Length; s++) _mesh.SetTriangles(data.Submeshes[s].Indices, s, false);
            if (data.HasSourceNormals) _mesh.normals = data.Normals; else _mesh.RecalculateNormals();
            _mesh.bounds = data.Bounds;

            var filter = gameObject.AddComponent<MeshFilter>();
            filter.sharedMesh = _mesh;
            _renderer = gameObject.AddComponent<MeshRenderer>();
            _renderer.sharedMaterials = materials;
            if (generateCollider)
            {
                _collider = gameObject.AddComponent<MeshCollider>();
                _collider.sharedMesh = _mesh;
            }
        }

        public bool RemoveBuilding(ulong buildingId)
        {
            if (_mesh == null || !_ownedBuildingIds.Contains(buildingId) || !_destroyedBuildingIds.Add(buildingId)) return false;
            for (int s = 0; s < _data.Submeshes.Length; s++)
            {
                BwmSubmeshData source = _data.Submeshes[s];
                var kept = new List<int>(source.Indices.Length);
                for (int triangle = 0; triangle < source.TriangleOwners.Length; triangle++)
                {
                    ushort ownerCode = source.TriangleOwners[triangle];
                    ulong ownerId = ownerCode == 0 ? 0UL : _data.OwnerIds[ownerCode - 1];
                    if (ownerId == buildingId) continue;
                    int i = triangle * 3;
                    kept.Add(source.Indices[i]); kept.Add(source.Indices[i + 1]); kept.Add(source.Indices[i + 2]);
                }
                _mesh.SetTriangles(kept, s, false);
            }
            _mesh.RecalculateBounds();
            if (_collider != null) { _collider.sharedMesh = null; _collider.sharedMesh = _mesh; }
            return true;
        }

        private void OnDestroy() { if (_mesh != null) Destroy(_mesh); }
    }
}
