using System.Collections.Generic;
using BerlinWorld.Data;
using UnityEngine;
using UnityEngine.Rendering;

namespace BerlinWorld.Procedural
{
    public static class RoadMeshBuilder
    {
        public static Mesh Build(IReadOnlyList<BerlinRoadData> roads, float y = 0.03f)
        {
            var vertices = new List<Vector3>();
            var uvs = new List<Vector2>();
            var triangles = new List<int>();

            foreach (BerlinRoadData road in roads)
            {
                if (road.Points == null || road.Points.Length < 2) continue;
                float halfWidth = Mathf.Max(0.25f, road.WidthMeters * 0.5f);
                float distance = 0f;
                for (int i = 0; i < road.Points.Length - 1; i++)
                {
                    Vector2 a = road.Points[i];
                    Vector2 b = road.Points[i + 1];
                    Vector2 dir = (b - a).normalized;
                    if (dir.sqrMagnitude < 0.5f) continue;
                    Vector2 right = new Vector2(dir.y, -dir.x) * halfWidth;
                    float segmentLength = Vector2.Distance(a, b);
                    int start = vertices.Count;
                    vertices.Add(new Vector3(a.x - right.x, y, a.y - right.y));
                    vertices.Add(new Vector3(a.x + right.x, y, a.y + right.y));
                    vertices.Add(new Vector3(b.x + right.x, y, b.y + right.y));
                    vertices.Add(new Vector3(b.x - right.x, y, b.y - right.y));
                    uvs.Add(new Vector2(0, distance));
                    uvs.Add(new Vector2(1, distance));
                    uvs.Add(new Vector2(1, distance + segmentLength));
                    uvs.Add(new Vector2(0, distance + segmentLength));
                    triangles.Add(start); triangles.Add(start + 1); triangles.Add(start + 2);
                    triangles.Add(start); triangles.Add(start + 2); triangles.Add(start + 3);
                    distance += segmentLength;
                }
            }

            var mesh = new Mesh { name = "BerlinRoads" };
            if (vertices.Count > 65535) mesh.indexFormat = IndexFormat.UInt32;
            mesh.SetVertices(vertices);
            mesh.SetUVs(0, uvs);
            mesh.SetTriangles(triangles, 0, true);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();
            return mesh;
        }
    }
}
