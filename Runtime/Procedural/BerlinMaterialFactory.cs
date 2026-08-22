using System.Collections.Generic;
using UnityEngine;
namespace BerlinWorld.Procedural
{
 internal static class BerlinMaterialFactory
 {
  private static readonly Dictionary<string,Material> Cache=new();
  public static Material Get(string key,Color color,float metallic=0f,float smoothness=.25f){if(Cache.TryGetValue(key,out Material existing)&&existing!=null)return existing;Shader shader=Shader.Find("Universal Render Pipeline/Lit")??Shader.Find("HDRP/Lit")??Shader.Find("Standard");var material=new Material(shader){name=$"BerlinFallback_{key}",hideFlags=HideFlags.DontSave};SetColor(material,color);if(material.HasProperty("_Metallic"))material.SetFloat("_Metallic",metallic);if(material.HasProperty("_Smoothness"))material.SetFloat("_Smoothness",smoothness);if(material.HasProperty("_Glossiness"))material.SetFloat("_Glossiness",smoothness);Cache[key]=material;return material;}
  public static void SetColor(Material material,Color color){if(material==null)return;if(material.HasProperty("_BaseColor"))material.SetColor("_BaseColor",color);if(material.HasProperty("_Color"))material.SetColor("_Color",color);}
  public static void SetColor(MaterialPropertyBlock block,Color color){block.SetColor("_BaseColor",color);block.SetColor("_Color",color);}
 }
}
