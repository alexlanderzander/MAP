using System;
using System.Collections.Generic;
using BerlinWorld.Data;
using UnityEngine;
using UnityEngine.Rendering;
namespace BerlinWorld.Procedural
{
 public static class RoadMeshBuilder
 {
  public static Mesh Build(IReadOnlyList<BerlinRoadData> roads,float y=.03f)=>BuildRoads(roads,y);
  public static Mesh BuildRoads(IReadOnlyList<BerlinRoadData> roads,float y=.03f)=>BuildFiltered(roads,r=>r.RoadClass is not (8 or 9 or 10 or 11 or 12),r=>Mathf.Max(.5f,r.WidthMeters),y,"BerlinRoads");
  public static Mesh BuildFootways(IReadOnlyList<BerlinRoadData> roads,float y=.055f)=>BuildFiltered(roads,r=>r.RoadClass is 8 or 9 or 12,r=>Mathf.Max(1f,r.WidthMeters),y,"BerlinFootways");
  public static Mesh BuildSidewalks(IReadOnlyList<BerlinRoadData> roads,float sidewalkWidth=1.8f,float y=.065f){var v=new List<Vector3>();var u=new List<Vector2>();var t=new List<int>();foreach(var r in roads){if(r.Points==null||r.Points.Length<2||r.SidewalkMask==0||r.RoadClass is 8 or 9 or 10 or 11 or 12)continue;float half=Mathf.Max(.25f,r.WidthMeters*.5f);if((r.SidewalkMask&1)!=0)AddOffsetRibbon(r.Points,-(half+sidewalkWidth*.5f),sidewalkWidth,y,v,u,t);if((r.SidewalkMask&2)!=0)AddOffsetRibbon(r.Points,half+sidewalkWidth*.5f,sidewalkWidth,y,v,u,t);}return Finish("BerlinSidewalks",v,u,t);}
  public static Mesh BuildRails(IReadOnlyList<BerlinRoadData> roads,float y=.09f){var v=new List<Vector3>();var u=new List<Vector2>();var t=new List<int>();foreach(var r in roads){if(r.Points==null||r.Points.Length<2||!(r.IsTram||r.IsRail))continue;const float gauge=1.435f;AddOffsetRibbon(r.Points,-gauge*.5f,.11f,y,v,u,t);AddOffsetRibbon(r.Points,gauge*.5f,.11f,y,v,u,t);}return Finish("BerlinRails",v,u,t);}
  static Mesh BuildFiltered(IReadOnlyList<BerlinRoadData> roads,Func<BerlinRoadData,bool> include,Func<BerlinRoadData,float> width,float y,string name){var v=new List<Vector3>();var u=new List<Vector2>();var t=new List<int>();foreach(var r in roads){if(!include(r)||r.Points==null||r.Points.Length<2)continue;AddOffsetRibbon(r.Points,0,width(r),y+r.Layer*.01f,v,u,t);}return Finish(name,v,u,t);}
  static void AddOffsetRibbon(Vector2[] points,float offset,float width,float y,List<Vector3> v,List<Vector2> u,List<int> t){float hw=Mathf.Max(.04f,width*.5f),distance=0;for(int i=0;i<points.Length-1;i++){Vector2 a=points[i],b=points[i+1],delta=b-a;float len=delta.magnitude;if(len<.02f)continue;Vector2 dir=delta/len,right=new(dir.y,-dir.x);a+=right*offset;b+=right*offset;Vector2 side=right*hw;int s=v.Count;v.Add(new Vector3(a.x-side.x,y,a.y-side.y));v.Add(new Vector3(a.x+side.x,y,a.y+side.y));v.Add(new Vector3(b.x+side.x,y,b.y+side.y));v.Add(new Vector3(b.x-side.x,y,b.y-side.y));u.Add(new Vector2(0,distance));u.Add(new Vector2(1,distance));u.Add(new Vector2(1,distance+len));u.Add(new Vector2(0,distance+len));t.Add(s);t.Add(s+1);t.Add(s+2);t.Add(s);t.Add(s+2);t.Add(s+3);distance+=len;}}
  static Mesh Finish(string name,List<Vector3> v,List<Vector2> u,List<int> t){var m=new Mesh{name=name};if(v.Count>65535)m.indexFormat=IndexFormat.UInt32;m.SetVertices(v);m.SetUVs(0,u);m.SetTriangles(t,0,true);m.RecalculateNormals();m.RecalculateBounds();return m;}
 }
}
