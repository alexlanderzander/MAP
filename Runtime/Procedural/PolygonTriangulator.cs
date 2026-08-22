using System.Collections.Generic;
using UnityEngine;

namespace BerlinWorld.Procedural
{
    internal static class PolygonTriangulator
    {
        public static List<int> Triangulate(IReadOnlyList<Vector2> polygon)
        {
            var result = new List<int>();
            int n = polygon.Count;
            if (n < 3) return result;
            var indices = new List<int>(n);
            if (SignedArea(polygon) > 0f)
            {
                for (int i = 0; i < n; i++) indices.Add(i);
            }
            else
            {
                for (int i = n - 1; i >= 0; i--) indices.Add(i);
            }

            int guard = n * n;
            while (indices.Count > 3 && guard-- > 0)
            {
                bool clipped = false;
                for (int i = 0; i < indices.Count; i++)
                {
                    int i0 = indices[(i - 1 + indices.Count) % indices.Count];
                    int i1 = indices[i];
                    int i2 = indices[(i + 1) % indices.Count];
                    Vector2 a = polygon[i0];
                    Vector2 b = polygon[i1];
                    Vector2 c = polygon[i2];
                    if (Cross(b - a, c - b) <= 0f) continue;
                    bool contains = false;
                    for (int j = 0; j < indices.Count; j++)
                    {
                        int p = indices[j];
                        if (p == i0 || p == i1 || p == i2) continue;
                        if (PointInTriangle(polygon[p], a, b, c)) { contains = true; break; }
                    }
                    if (contains) continue;
                    result.Add(i0); result.Add(i1); result.Add(i2);
                    indices.RemoveAt(i);
                    clipped = true;
                    break;
                }
                if (!clipped) break;
            }
            if (indices.Count == 3)
            {
                result.Add(indices[0]); result.Add(indices[1]); result.Add(indices[2]);
            }
            return result;
        }

        private static float SignedArea(IReadOnlyList<Vector2> polygon)
        {
            double sum = 0;
            for (int i = 0; i < polygon.Count; i++)
            {
                Vector2 a = polygon[i];
                Vector2 b = polygon[(i + 1) % polygon.Count];
                sum += (double)a.x * b.y - (double)b.x * a.y;
            }
            return (float)(sum * 0.5);
        }

        private static float Cross(Vector2 a, Vector2 b) => a.x * b.y - a.y * b.x;

        private static bool PointInTriangle(Vector2 p, Vector2 a, Vector2 b, Vector2 c)
        {
            float c1 = Cross(b - a, p - a);
            float c2 = Cross(c - b, p - b);
            float c3 = Cross(a - c, p - c);
            bool neg = c1 < 0f || c2 < 0f || c3 < 0f;
            bool pos = c1 > 0f || c2 > 0f || c3 > 0f;
            return !(neg && pos);
        }
    }
}
