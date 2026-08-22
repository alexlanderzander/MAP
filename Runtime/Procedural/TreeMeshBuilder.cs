using System.Collections.Generic;
using BerlinWorld.Data;
using UnityEngine;
using UnityEngine.Rendering;
namespace BerlinWorld.Procedural
{
 public static class TreeMeshBuilder
 {
  public static Mesh Build(IReadOnlyList<BerlinTreeData> trees){var vertices=new List<Vector3>(trees.Count*14);var uv=new List<Vector2>(trees.Count*14);var trunk=new List<int>(trees.Count*24);var crown=new List<int>(trees.Count*24);foreach(var tree in trees){float h=Mathf.Max(1.5f,tree.HeightMeters),crownD=Mathf.Clamp(tree.CrownMeters,.8f,h*.9f),trunkH=Mathf.Max(1.2f,h-crownD*.65f),r=Mathf.Clamp(crownD*.08f,.08f,.45f);Vector2 p=tree.Position;int s=vertices.Count;vertices.Add(new Vector3(p.x-r,0,p.y-r));vertices.Add(new Vector3(p.x+r,0,p.y-r));vertices.Add(new Vector3(p.x+r,trunkH,p.y-r));vertices.Add(new Vector3(p.x-r,trunkH,p.y-r));vertices.Add(new Vector3(p.x-r,0,p.y+r));vertices.Add(new Vector3(p.x+r,0,p.y+r));vertices.Add(new Vector3(p.x+r,trunkH,p.y+r));vertices.Add(new Vector3(p.x-r,trunkH,p.y+r));for(int i=0;i<8;i++)uv.Add(Vector2.zero);int[] ti={0,2,1,0,3,2,5,6,4,6,7,4,4,7,0,7,3,0,1,2,5,2,6,5};foreach(int t in ti)trunk.Add(s+t);int c=vertices.Count;float cr=crownD*.5f,cy=trunkH+crownD*.28f;vertices.Add(new Vector3(p.x,cy+cr,p.y));vertices.Add(new Vector3(p.x+cr,cy,p.y));vertices.Add(new Vector3(p.x,cy,p.y+cr));vertices.Add(new Vector3(p.x-cr,cy,p.y));vertices.Add(new Vector3(p.x,cy,p.y-cr));vertices.Add(new Vector3(p.x,cy-cr,p.y));for(int i=0;i<6;i++)uv.Add(Vector2.zero);int[] ci={0,1,2,0,2,3,0,3,4,0,4,1,5,2,1,5,3,2,5,4,3,5,1,4};foreach(int t in ci)crown.Add(c+t);}var mesh=new Mesh{name="BerlinTrees"};if(vertices.Count>65535)mesh.indexFormat=IndexFormat.UInt32;mesh.SetVertices(vertices);mesh.SetUVs(0,uv);mesh.subMeshCount=2;mesh.SetTriangles(trunk,0,false);mesh.SetTriangles(crown,1,true);mesh.RecalculateNormals();mesh.RecalculateBounds();return mesh;}
 }
}
