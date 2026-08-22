using BerlinWorld.Data;
using UnityEngine;

namespace BerlinWorld.Destruction
{
    [DisallowMultipleComponent]
    public sealed class DestructibleBuilding : MonoBehaviour
    {
        [Min(1f)] public float DamageThreshold = 100f;
        [Min(0.5f)] public float ChunkWidth = 2.5f;
        [Min(0.5f)] public float ChunkHeight = 2.5f;
        [Min(8)] public int MaxChunks = 220;
        [Min(1f)] public float DebrisLifetime = 18f;

        private BerlinBuildingData _building;
        private float _damage;
        private bool _destroyed;
        private MeshRenderer _renderer;
        private Collider _collider;

        public ulong BuildingId => _building?.Id ?? 0;
        public bool IsDestroyed => _destroyed;

        public void Initialize(BerlinBuildingData building, float threshold)
        {
            _building = building;
            DamageThreshold = threshold;
            _renderer = GetComponent<MeshRenderer>();
            _collider = GetComponent<Collider>();
        }

        public void ApplyDamage(float amount, Vector3 worldPoint, float explosionForce = 700f, float explosionRadius = 8f)
        {
            if (_destroyed || _building == null || amount <= 0f) return;
            _damage += amount;
            if (_damage >= DamageThreshold) Fracture(worldPoint, explosionForce, explosionRadius);
        }

        [ContextMenu("Test Destruction")]
        private void TestDestruction()
        {
            if (Application.isPlaying) ApplyDamage(DamageThreshold, transform.position + Vector3.up * 2f);
        }

        private void Fracture(Vector3 worldPoint, float explosionForce, float explosionRadius)
        {
            _destroyed = true;
            if (_renderer != null) _renderer.enabled = false;
            if (_collider != null) _collider.enabled = false;

            Material material = _renderer != null ? _renderer.sharedMaterial : null;
            int spawned = 0;
            float bottom = _building.MinHeightMeters;
            float top = Mathf.Max(bottom + 0.1f, _building.HeightMeters);

            for (int edge = 0; edge < _building.Footprint.Length && spawned < MaxChunks; edge++)
            {
                Vector2 a2 = _building.Footprint[edge];
                Vector2 b2 = _building.Footprint[(edge + 1) % _building.Footprint.Length];
                Vector3 a = new(a2.x, 0f, a2.y);
                Vector3 b = new(b2.x, 0f, b2.y);
                Vector3 edgeVector = b - a;
                float length = edgeVector.magnitude;
                if (length < 0.25f) continue;
                Vector3 direction = edgeVector / length;
                float yaw = Mathf.Atan2(direction.x, direction.z) * Mathf.Rad2Deg;
                int horizontal = Mathf.Max(1, Mathf.CeilToInt(length / ChunkWidth));
                int vertical = Mathf.Max(1, Mathf.CeilToInt((top - bottom) / ChunkHeight));
                float w = length / horizontal;
                float h = (top - bottom) / vertical;

                for (int x = 0; x < horizontal && spawned < MaxChunks; x++)
                {
                    for (int y = 0; y < vertical && spawned < MaxChunks; y++)
                    {
                        Vector3 local = a + direction * ((x + 0.5f) * w);
                        local.y = bottom + (y + 0.5f) * h;
                        Vector3 wp = transform.TransformPoint(local);
                        var chunk = GameObject.CreatePrimitive(PrimitiveType.Cube);
                        chunk.name = $"Debris_{BuildingId}_{spawned}";
                        chunk.transform.SetPositionAndRotation(wp, Quaternion.Euler(0f, yaw, 0f));
                        chunk.transform.localScale = new Vector3(0.22f, h, w);
                        if (material != null) chunk.GetComponent<MeshRenderer>().sharedMaterial = material;
                        var body = chunk.AddComponent<Rigidbody>();
                        body.mass = Mathf.Max(2f, w * h * 8f);
                        body.AddExplosionForce(explosionForce, worldPoint, explosionRadius, 0.5f, ForceMode.Impulse);
                        Destroy(chunk, DebrisLifetime);
                        spawned++;
                    }
                }
            }
        }
    }
}
