using System;
using System.Collections.Generic;
using BerlinWorld.Data;
using UnityEngine;
using UnityEngine.Rendering;

namespace BerlinWorld.Procedural
{
    public static class BuildingMeshBuilder
    {
        public static Mesh Build(BerlinBuildingData building)
        {
            if (building == null) throw new ArgumentNullException(nameof(building));
            if (building.Footprint == null || building.Footprint.Length < 3)
                throw new ArgumentException("Building footprint needs at least three vertices.", nameof(building));

            var vertices = new List<Vector3>(building.Footprint.Length * 6);
            var uv = new List<Vector2>(building.Footprint.Length * 6);
            var triangles = new List<int>(building.Footprint.Length * 9);
            float bottom = building.MinHeightMeters;
            float top = Mathf.Max(bottom + 0.1f, building.HeightMeters);

            for (int i = 0; i < building.Footprint.Length; i++)
            {
                Vector2 a2 = building.Footprint[i];
                Vector2 b2 = building.Footprint[(i + 1) % building.Footprint.Length];
                float edgeLength = Vector2.Distance(a2, b2);
                int start = vertices.Count;
                vertices.Add(new Vector3(a2.x, bottom, a2.y));
                vertices.Add(new Vector3(b2.x, bottom, b2.y));
                vertices.Add(new Vector3(b2.x, top, b2.y));
                vertices.Add(new Vector3(a2.x, top, a2.y));
                uv.Add(new Vector2(0, 0));
                uv.Add(new Vector2(edgeLength, 0));
                uv.Add(new Vector2(edgeLength, top - bottom));
                uv.Add(new Vector2(0, top - bottom));
                triangles.Add(start); triangles.Add(start + 2); triangles.Add(start + 1);
                triangles.Add(start); triangles.Add(start + 3); triangles.Add(start + 2);
            }

            int roofStart = vertices.Count;
            foreach (Vector2 p in building.Footprint)
            {
                vertices.Add(new Vector3(p.x, top, p.y));
                uv.Add(p * 0.1f);
            }
            List<int> roof = PolygonTriangulator.Triangulate(building.Footprint);
            for (int i = 0; i < roof.Count; i += 3)
            {
                triangles.Add(roofStart + roof[i]);
                triangles.Add(roofStart + roof[i + 2]);
                triangles.Add(roofStart + roof[i + 1]);
            }

            var mesh = new Mesh { name = $"BerlinBuilding_{building.Id}" };
            if (vertices.Count > 65535) mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(vertices);
            mesh.SetUVs(0, uv);
            mesh.SetTriangles(triangles, 0, true);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }
    }
}
