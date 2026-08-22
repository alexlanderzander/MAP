using System;
using System.Collections.Generic;
using BerlinWorld.Data;
using UnityEngine;
using UnityEngine.Rendering;
namespace BerlinWorld.Procedural
{
 public static class SurfaceMeshBuilder
 {
  public static Mesh Build(IReadOnlyList<BerlinSurfaceData> surfaces,Func<BerlinSurfaceData,bool> include,float y,string name){var vertices=new List<Vector3>();var uvs=new List<Vector2>();var triangles=new List<int>();foreach(var s in surfaces){if(!include(s)||s.Footprint==null||s.Footprint.Length<3)continue;int start=vertices.Count;foreach(Vector2 p in s.Footprint){vertices.Add(new Vector3(p.x,y,p.y));uvs.Add(p*.08f);}List<int> local=PolygonTriangulator.Triangulate(s.Footprint);for(int i=0;i<local.Count;i+=3){triangles.Add(start+local[i]);triangles.Add(start+local[i+2]);triangles.Add(start+local[i+1]);}}var mesh=new Mesh{name=name};if(vertices.Count>65535)mesh.indexFormat=IndexFormat.UInt32;mesh.SetVertices(vertices);mesh.SetUVs(0,uvs);mesh.SetTriangles(triangles,0,true);mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;}
  public static Mesh BuildGround(int tileSizeMeters,float y=0f){float h=tileSizeMeters*.5f;var mesh=new Mesh{name="BerlinGround"};mesh.vertices=new[]{new Vector3(-h,y,-h),new Vector3(h,y,-h),new Vector3(h,y,h),new Vector3(-h,y,h)};mesh.uv=new[]{Vector2.zero,Vector2.right,Vector2.one,Vector2.up};mesh.triangles=new[]{0,2,1,0,3,2};mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;}
 }
}
