from __future__ import annotations
import argparse,json,tempfile
from datetime import datetime,timezone
from pathlib import Path
from cli import pack
from normalize import normalize_buildings,normalize_roads,normalize_trees
from osm import OsmError,OverpassClient,normalize_osm
from wfs import SOURCES,WfsClient,WfsError

def load_area(path):
 d=json.loads(Path(path).read_text(encoding="utf-8"));bbox=d.get("bbox")
 if not isinstance(bbox,list) or len(bbox)!=4:raise ValueError("area bbox must be [minE,minN,maxE,maxN]")
 v=tuple(float(x) for x in bbox)
 if v[2]<=v[0] or v[3]<=v[1]:raise ValueError("invalid area bbox")
 d["bbox"]=v;w=d.get("bboxWgs84")
 if w is not None:
  if not isinstance(w,list) or len(w)!=4:raise ValueError("area bboxWgs84 must be [west,south,east,north]")
  d["bboxWgs84"]=tuple(float(x) for x in w)
 return d
def fetch_official(args,bbox):
 client=WfsClient(timeout=args.timeout,retries=args.retries,page_size=args.page_size);normalizers={"buildings":normalize_buildings,"trees":normalize_trees};norm={};report=[]
 for kind in ("buildings","roads","trees"):
  src=SOURCES[kind];print(f"Fetching official {kind} from {src.endpoint} ...");tn,raw=client.fetch_source(src,bbox);cooked=normalize_roads(raw,bbox,args.tile_size) if kind=="roads" else normalizers[kind](raw,bbox);count=len(cooked.get("features") or [])
  if count==0:raise WfsError(f"Official {kind} source returned no usable features for this central-Berlin area")
  norm[kind]=cooked;report.append({"kind":kind,"sourceId":src.id,"endpoint":src.endpoint,"featureType":tn,"rawFeatures":len(raw.get("features") or []),"normalizedFeatures":count,"license":"DL-DE-Zero-2.0"});print(f"  {len(raw.get('features') or [])} raw -> {count} normalized")
 norm["surfaces"]={"type":"FeatureCollection","features":[]};return norm,report
def fetch_osm(args,area,bbox):
 wgs=area.get("bboxWgs84")
 if not wgs:raise OsmError("OSM source requires bboxWgs84 in the area definition")
 print("Fetching current OpenStreetMap detail through Overpass ...");endpoint,payload=OverpassClient(timeout=max(args.timeout,45.),retries=args.retries).fetch(wgs);norm=normalize_osm(payload,bbox,args.tile_size);counts={k:len(fc.get("features") or []) for k,fc in norm.items()}
 if counts["buildings"]==0 or counts["roads"]==0:raise OsmError(f"OSM produced an implausible empty core layer: {counts}")
 print(f"  OSM -> {counts['buildings']} buildings, {counts['roads']} road/rail parts, {counts['trees']} trees, {counts['surfaces']} surfaces")
 return norm,[{"kind":"buildings+roads+rails+trees+surfaces","sourceId":"openstreetmap-overpass","endpoint":endpoint,"rawElements":len(payload.get("elements") or []),"normalizedFeatures":counts,"license":"ODbL-1.0","attribution":"© OpenStreetMap contributors","statusNote":"Used for current street-level semantic detail. For city-scale production use a regional OSM extract rather than repeated public Overpass queries."}]
def _try_osm_surface_enrichment(args,area,bbox,norm,report):
 try:
  osm,sources=fetch_osm(args,area,bbox);norm["surfaces"]=osm["surfaces"];norm["roads"]["features"].extend([f for f in osm["roads"]["features"] if (f.get("properties") or {}).get("class") in {"tram","rail","footway","cycleway"}]);report.extend(sources);report[-1]["statusNote"]="OSM semantic enrichment for surfaces, rail/tram and pedestrian/cycle detail; official Berlin remains the primary building/road/tree source."
 except OsmError as ex:print(f"OSM enrichment unavailable; continuing with official layers only: {ex}")
def build(args):
 area=load_area(args.area);bbox=area["bbox"];mode=args.source;official_error=None
 if mode in {"auto","official"}:
  try:norm,report=fetch_official(args,bbox);mode="official+osm-enrichment";_try_osm_surface_enrichment(args,area,bbox,norm,report)
  except WfsError as ex:
   official_error=str(ex)
   if args.source=="official":raise
   print(f"Official Berlin WFS unavailable; switching to current OSM. Reason: {ex}");norm,report=fetch_osm(args,area,bbox);mode="osm-fallback"
 else:norm,report=fetch_osm(args,area,bbox);mode="osm"
 out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 with tempfile.TemporaryDirectory(prefix="berlin-world-") as td:
  tmp=Path(td);paths={}
  for kind in ("buildings","roads","trees","surfaces"):
   p=tmp/f"{kind}.geojson";p.write_text(json.dumps(norm.get(kind,{"type":"FeatureCollection","features":[]}),separators=(",",":")),encoding="utf-8");paths[kind]=p
  pack(argparse.Namespace(buildings=str(paths["buildings"]),roads=str(paths["roads"]),trees=str(paths["trees"]),surfaces=str(paths["surfaces"]),out=str(out),tile_size=args.tile_size,level=args.level))
 manifest={"areaId":area.get("id"),"areaName":area.get("name"),"crs":area.get("crs","EPSG:25833"),"bbox":list(bbox),"sourceMode":mode,"retrievedAtUtc":datetime.now(timezone.utc).isoformat(),"sources":report,"officialFailure":official_error,"fidelity":"1:1 horizontal metric layout from source geometry; heights/roofs use source tags when present and deterministic estimates otherwise.","notes":"Raw network responses are transient and not part of the game build. Inspect license/attribution fields before distributing generated data."};(out/"source_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n",encoding="utf-8");return 0
def main():
 p=argparse.ArgumentParser(description="Build the Hackescher Markt 1 km² Unity-ready compact 3D world data");p.add_argument("--area",default="DataSources/hackescher_markt_area.json");p.add_argument("--out",default="GeneratedBerlin/HackescherMarkt/Tiles");p.add_argument("--source",choices=("auto","official","osm"),default="auto");p.add_argument("--tile-size",type=int,default=500,choices=range(100,601));p.add_argument("--level",type=int,default=9,choices=range(1,10));p.add_argument("--timeout",type=float,default=30.);p.add_argument("--retries",type=int,default=3);p.add_argument("--page-size",type=int,default=5000);a=p.parse_args()
 try:return build(a)
 except (WfsError,OsmError,ValueError) as ex:p.error(str(ex));return 2
if __name__=="__main__":raise SystemExit(main())
