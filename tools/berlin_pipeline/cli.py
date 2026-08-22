from __future__ import annotations

import argparse,json
from collections import defaultdict
from pathlib import Path
from statistics import mean
from format import Building,Road,Tree,Surface,Tile,BUILDING_CLASSES,ROAD_CLASSES,ROOF_TYPES,FACADE_TYPES,ROAD_SURFACES,SURFACE_KINDS,SURFACE_MATERIALS,enum_value,rgb565,encode_tile_gzip,stable_id,tile_center,tile_index

def load_geojson(path):
    if not path:return {"type":"FeatureCollection","features":[]}
    with open(path,"r",encoding="utf-8") as f:data=json.load(f)
    if data.get("type")!="FeatureCollection":raise ValueError(f"{path}: expected GeoJSON FeatureCollection")
    return data

def polygon_outer(geometry):
    coords=geometry.get("coordinates",[]);gtype=geometry.get("type")
    if gtype=="Polygon":ring=coords[0] if coords else []
    elif gtype=="MultiPolygon":
        rings=[poly[0] for poly in coords if poly];ring=max(rings,key=len) if rings else []
    else:return []
    pts=[(float(p[0]),float(p[1])) for p in ring]
    if len(pts)>=2 and pts[0]==pts[-1]:pts.pop()
    return pts

def line_points(g):return [(float(p[0]),float(p[1])) for p in g.get("coordinates",[])] if g.get("type")=="LineString" else []
def point_xy(g):
    c=g.get("coordinates",[]);return (float(c[0]),float(c[1])) if g.get("type")=="Point" and len(c)>=2 else None
def feature_id(f,fallback):
    p=f.get("properties") or {};return stable_id(f.get("id",p.get("id",fallback)))
def centroid(points):return mean(p[0] for p in points),mean(p[1] for p in points)

def pack(args):
    ts=args.tile_size;buckets=defaultdict(lambda:{"buildings":[],"roads":[],"trees":[],"surfaces":[]})
    for idx,f in enumerate(load_geojson(args.buildings)["features"]):
        pts=polygon_outer(f.get("geometry") or {})
        if len(pts)<3:continue
        p=f.get("properties") or {};key=tile_index(*centroid(pts),ts)
        buckets[key]["buildings"].append(Building(feature_id(f,f"building-{idx}"),pts,float(p.get("height",p.get("measuredHeight",12.0))),float(p.get("min_height",0.0)),enum_value(p.get("roof_type","flat"),ROOF_TYPES),enum_value(p.get("class","unknown"),BUILDING_CLASSES),int(float(p.get("levels",0) or 0)),enum_value(p.get("facade_type","unknown"),FACADE_TYPES),float(p.get("roof_height",0.0) or 0.0),rgb565(p.get("facade_color")),rgb565(p.get("roof_color"))))
    for idx,f in enumerate(load_geojson(args.roads)["features"]):
        pts=line_points(f.get("geometry") or {})
        if len(pts)<2:continue
        p=f.get("properties") or {};key=tile_index(*centroid(pts),ts)
        buckets[key]["roads"].append(Road(feature_id(f,f"road-{idx}"),pts,float(p.get("width",7.0)),int(float(p.get("lanes",1) or 1)),enum_value(p.get("class","unknown"),ROAD_CLASSES),enum_value(p.get("surface","unknown"),ROAD_SURFACES),int(p.get("sidewalk_mask",0) or 0),int(p.get("flags",0) or 0),int(p.get("layer",0) or 0)))
    for idx,f in enumerate(load_geojson(args.trees)["features"]):
        point=point_xy(f.get("geometry") or {})
        if point is None:continue
        p=f.get("properties") or {};key=tile_index(point[0],point[1],ts)
        buckets[key]["trees"].append(Tree(feature_id(f,f"tree-{idx}"),point[0],point[1],float(p.get("height",8.0)),float(p.get("crown",4.0)),int(p.get("species_code",0))))
    for idx,f in enumerate(load_geojson(getattr(args,"surfaces",None))["features"]):
        pts=polygon_outer(f.get("geometry") or {})
        if len(pts)<3:continue
        p=f.get("properties") or {};key=tile_index(*centroid(pts),ts)
        buckets[key]["surfaces"].append(Surface(feature_id(f,f"surface-{idx}"),pts,enum_value(p.get("kind","unknown"),SURFACE_KINDS),enum_value(p.get("material","unknown"),SURFACE_MATERIALS)))
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True);manifest={"format":"BWT1","version":2,"crs":"EPSG:25833","tileSizeM":ts,"quantizationCm":2,"compression":"gzip","tiles":[]};total_bytes=total_features=0
    for (tx,tz),bucket in sorted(buckets.items()):
        ce,cn=tile_center(tx,tz,ts);tile=Tile(tx,tz,ts,ce,cn,bucket["buildings"],bucket["roads"],bucket["trees"],bucket["surfaces"]);payload=encode_tile_gzip(tile,compresslevel=args.level);fn=f"tile_{tx}_{tz}.bwt.gz";(out/fn).write_bytes(payload);count=sum(len(bucket[k]) for k in ("buildings","roads","trees","surfaces"));total_bytes+=len(payload);total_features+=count;manifest["tiles"].append({"x":tx,"z":tz,"file":fn,"bytes":len(payload),"buildings":len(bucket["buildings"]),"roads":len(bucket["roads"]),"trees":len(bucket["trees"]),"surfaces":len(bucket["surfaces"])})
    manifest["totalBytes"]=total_bytes;manifest["totalFeatures"]=total_features;(out/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8");print(f"Packed {len(manifest['tiles'])} tiles, {total_features} features, {total_bytes:,} bytes");return 0

def main():
    parser=argparse.ArgumentParser(description="Pack Berlin EPSG:25833 GeoJSON into compact BWT Unity tiles");sub=parser.add_subparsers(dest="cmd",required=True);p=sub.add_parser("pack");p.add_argument("--buildings");p.add_argument("--roads");p.add_argument("--trees");p.add_argument("--surfaces");p.add_argument("--out",required=True);p.add_argument("--tile-size",type=int,default=500,choices=range(100,601));p.add_argument("--level",type=int,default=9,choices=range(1,10));p.set_defaults(func=pack);args=parser.parse_args();return args.func(args)
if __name__=="__main__":raise SystemExit(main())
