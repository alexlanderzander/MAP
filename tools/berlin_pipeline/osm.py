from __future__ import annotations
import json,math,re,time
from urllib.error import HTTPError,URLError
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from format import stable_id,ROAD_FLAG_BRIDGE,ROAD_FLAG_TUNNEL,ROAD_FLAG_TRAM,ROAD_FLAG_RAIL,ROAD_FLAG_STEPS
from normalize import clip_line,split_line_to_tiles
OVERPASS_ENDPOINTS=("https://overpass-api.de/api/interpreter","https://overpass.private.coffee/api/interpreter")
class OsmError(RuntimeError):pass

def wgs84_to_utm33(lon_deg,lat_deg):
 a=6378137.;ecc_sq=.0066943799901413165;k0=.9996;ep=ecc_sq/(1-ecc_sq);lat=math.radians(lat_deg);lon=math.radians(lon_deg);lo=math.radians(15.);s=math.sin(lat);c0=math.cos(lat);t0=math.tan(lat);n=a/math.sqrt(1-ecc_sq*s*s);t=t0*t0;c=ep*c0*c0;aa=c0*(lon-lo);e2=ecc_sq*ecc_sq;e3=e2*ecc_sq;m=a*((1-ecc_sq/4-3*e2/64-5*e3/256)*lat-(3*ecc_sq/8+3*e2/32+45*e3/1024)*math.sin(2*lat)+(15*e2/256+45*e3/1024)*math.sin(4*lat)-(35*e3/3072)*math.sin(6*lat));e=k0*n*(aa+(1-t+c)*aa**3/6+(5-18*t+t*t+72*c-58*ep)*aa**5/120)+500000.;nn=k0*(m+n*t0*(aa*aa/2+(5-t+9*c+4*c*c)*aa**4/24+(61-58*t+t*t+600*c-330*ep)*aa**6/720));return e,nn

def _number(value,default=0.):
 if value in (None,""):return default
 m=re.search(r"[-+]?\d+(?:[.,]\d+)?",str(value))
 if not m:return default
 try:return float(m.group(0).replace(",","."))
 except ValueError:return default

def _utm_geometry(geometry):
 out=[]
 for p in geometry or []:
  if "lon" in p and "lat" in p:out.append(list(wgs84_to_utm33(float(p["lon"]),float(p["lat"]))))
 return out

def _centroid(points):return sum(p[0] for p in points)/len(points),sum(p[1] for p in points)/len(points)
def _inside(x,y,b):return b[0]<=x<b[2] and b[1]<=y<b[3]
def _building_class(tags):
 v=str(tags.get("building","")).casefold();h=str(tags.get("historic","")).casefold()
 if h and h!="no":return "historic"
 if v in {"apartments","residential","house","detached","terrace","dormitory"}:return "residential"
 if v in {"commercial","retail","office","hotel"}:return "commercial"
 if v in {"industrial","warehouse","factory"}:return "industrial"
 if v in {"civic","public","school","university","hospital","church","cathedral","government","train_station"}:return "public"
 return "unknown"
ROOF_MAP={"flat":"flat","gabled":"gabled","gable":"gabled","half-hipped":"hipped","hipped":"hipped","hip":"hipped","mansard":"mansard","skillion":"shed","shed":"shed","pyramidal":"pyramidal","pyramid":"pyramidal","dome":"dome","onion":"dome","round":"dome"}
def _facade_type(tags):
 m=str(tags.get("building:material",tags.get("facade:material",""))).casefold()
 if m in {"brick","bricks","clinker"}:return "brick"
 if m=="glass":return "glass"
 if m=="concrete":return "concrete"
 if m in {"stone","sandstone","granite","limestone"}:return "stone"
 if m in {"metal","steel","aluminium","aluminum"}:return "metal"
 if m in {"wood","timber"}:return "timber"
 if m in {"plaster","stucco","render"}:return "plaster"
 return "unknown"
def _building_properties(tags):
 levels=max(0,int(round(_number(tags.get("building:levels"),0))));roof_levels=max(0.,_number(tags.get("roof:levels"),0));shape=ROOF_MAP.get(str(tags.get("roof:shape","flat")).casefold(),"flat");rh=max(0.,_number(tags.get("roof:height"),0))
 if shape!="flat" and rh<=0:rh=roof_levels*2.6 if roof_levels>0 else 2.6
 height=_number(tags.get("height"),0)
 if height<=0:height=(max(3.6,levels*3.15) if levels>0 else 11.5)+rh
 mh=_number(tags.get("min_height"),0)
 if mh<=0:
  ml=_number(tags.get("building:min_level"),0)
  if ml>0:mh=ml*3.15
 return {"height":round(max(2.4,height),2),"min_height":round(max(0.,mh),2),"levels":min(255,levels),"roof_type":shape,"roof_height":round(min(max(0.,rh),max(0.,height-mh)),2),"class":_building_class(tags),"facade_type":_facade_type(tags),"facade_color":tags.get("building:colour") or tags.get("building:color") or tags.get("facade:colour") or "","roof_color":tags.get("roof:colour") or tags.get("roof:color") or "","source":"OpenStreetMap"}
def _road_class(tags):
 r=str(tags.get("railway","")).casefold()
 if r=="tram":return "tram"
 if r in {"rail","light_rail","subway","narrow_gauge"}:return "rail"
 if r=="platform":return "platform"
 h=str(tags.get("highway","")).casefold()
 if h in {"motorway","motorway_link"}:return "motorway"
 if h in {"trunk","trunk_link"}:return "trunk"
 if h in {"primary","primary_link"}:return "primary"
 if h in {"secondary","secondary_link"}:return "secondary"
 if h in {"tertiary","tertiary_link"}:return "tertiary"
 if h in {"service","track"}:return "service"
 if h=="cycleway":return "cycleway"
 if h in {"footway","pedestrian","path","steps"}:return "footway"
 return "residential"
ROAD_WIDTHS={"motorway":20.,"trunk":14.,"primary":12.,"secondary":10.,"tertiary":8.,"residential":6.5,"service":4.,"footway":2.5,"cycleway":2.2,"tram":3.,"rail":3.2,"platform":3.}
def _road_surface(tags):
 v=str(tags.get("surface","")).casefold()
 if v in {"asphalt","bitumen"}:return "asphalt"
 if v in {"paving_stones","paved","tiles"}:return "paving"
 if v in {"sett","unhewn_cobblestone"}:return "sett"
 if v=="cobblestone":return "cobblestone"
 if v in {"concrete","concrete:plates","concrete:lanes"}:return "concrete"
 if v in {"gravel","fine_gravel","compacted"}:return "gravel"
 if v in {"ground","earth","dirt","sand","unpaved"}:return "unpaved"
 if v in {"grass","grass_paver"}:return "grass"
 return "unknown"
def _sidewalk_mask(tags):
 v=str(tags.get("sidewalk","")).casefold()
 if v in {"both","yes"}:return 3
 if v=="left":return 1
 if v=="right":return 2
 m=0
 if str(tags.get("sidewalk:left","")).casefold() not in {"","no","none","separate"}:m|=1
 if str(tags.get("sidewalk:right","")).casefold() not in {"","no","none","separate"}:m|=2
 return m
def _road_flags(tags):
 f=0;r=str(tags.get("railway","")).casefold()
 if str(tags.get("bridge","")).casefold() not in {"","no"}:f|=ROAD_FLAG_BRIDGE
 if str(tags.get("tunnel","")).casefold() not in {"","no"}:f|=ROAD_FLAG_TUNNEL
 if r=="tram":f|=ROAD_FLAG_TRAM
 if r in {"rail","light_rail","subway","narrow_gauge"}:f|=ROAD_FLAG_RAIL
 if str(tags.get("highway","")).casefold()=="steps":f|=ROAD_FLAG_STEPS
 return f
def _stitch_outer_relation(e):
 seg=[]
 for m in e.get("members") or []:
  if m.get("type")!="way" or m.get("role","outer") not in ("","outer"):continue
  p=_utm_geometry(m.get("geometry") or [])
  if len(p)>=2:seg.append(p)
 if not seg:return []
 chains=[]
 while seg:
  chain=seg.pop(0);changed=True
  while changed and seg:
   changed=False
   for i,s in enumerate(seg):
    if math.dist(chain[-1],s[0])<.75:chain.extend(s[1:]);seg.pop(i);changed=True;break
    if math.dist(chain[-1],s[-1])<.75:chain.extend(reversed(s[:-1]));seg.pop(i);changed=True;break
  chains.append(chain)
 chain=max(chains,key=len)
 if len(chain)>=3 and math.dist(chain[0],chain[-1])<2:chain[-1]=chain[0]
 return chain
def _poly_area(p):return abs(sum(p[i][0]*p[(i+1)%len(p)][1]-p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))*.5) if len(p)>=3 else 0.
def _clip_polygon_rect(points,rect):
 if len(points)>=2 and points[0]==points[-1]:points=points[:-1]
 out=[list(p) for p in points];mnx,mny,mxx,mxy=rect
 def clip(poly,inside,intersect):
  if not poly:return []
  r=[];prev=poly[-1];pin=inside(prev)
  for cur in poly:
   cin=inside(cur)
   if cin:
    if not pin:r.append(intersect(prev,cur))
    r.append(cur)
   elif pin:r.append(intersect(prev,cur))
   prev,pin=cur,cin
  return r
 def ix(x,a,b):
  dx=b[0]-a[0];t=0 if abs(dx)<1e-12 else (x-a[0])/dx;return [x,a[1]+(b[1]-a[1])*t]
 def iy(y,a,b):
  dy=b[1]-a[1];t=0 if abs(dy)<1e-12 else (y-a[1])/dy;return [a[0]+(b[0]-a[0])*t,y]
 out=clip(out,lambda p:p[0]>=mnx,lambda a,b:ix(mnx,a,b));out=clip(out,lambda p:p[0]<=mxx,lambda a,b:ix(mxx,a,b));out=clip(out,lambda p:p[1]>=mny,lambda a,b:iy(mny,a,b));out=clip(out,lambda p:p[1]<=mxy,lambda a,b:iy(mxy,a,b));clean=[]
 for p in out:
  if not clean or math.dist(clean[-1],p)>.01:clean.append(p)
 if len(clean)>=2 and math.dist(clean[0],clean[-1])<.01:clean.pop()
 return clean
def _split_polygon_to_tiles(points,bbox,ts):
 if len(points)<3:return
 mnx=max(bbox[0],min(p[0] for p in points));mxx=min(bbox[2],max(p[0] for p in points));mny=max(bbox[1],min(p[1] for p in points));mxy=min(bbox[3],max(p[1] for p in points))
 if mxx<=mnx or mxy<=mny:return
 for ty in range(math.floor(mny/ts),math.floor((mxy-1e-6)/ts)+1):
  for tx in range(math.floor(mnx/ts),math.floor((mxx-1e-6)/ts)+1):
   rect=(max(bbox[0],tx*ts),max(bbox[1],ty*ts),min(bbox[2],(tx+1)*ts),min(bbox[3],(ty+1)*ts));c=_clip_polygon_rect(points,rect)
   if len(c)>=3 and _poly_area(c)>=1:yield tx,ty,c
def _surface_kind_material(tags):
 n=str(tags.get("natural","")).casefold();l=str(tags.get("leisure","")).casefold();lu=str(tags.get("landuse","")).casefold();h=str(tags.get("highway","")).casefold();a=str(tags.get("amenity","")).casefold();r=str(tags.get("railway","")).casefold();p=str(tags.get("place","")).casefold();s=_road_surface(tags)
 if n=="water" or str(tags.get("waterway","")).casefold()=="riverbank":return "water","water"
 if l in {"park","garden"}:return "park","grass"
 if lu in {"grass","meadow","recreation_ground","village_green"}:return "grass","grass"
 if a=="parking":return "parking","asphalt" if s=="asphalt" else ("paving" if s in {"paving","sett","cobblestone"} else "unknown")
 if h=="pedestrian" and str(tags.get("area","")).casefold() in {"yes","1","true"}:return "pedestrian","paving"
 if p=="square":return "plaza","paving"
 if r=="platform":return "railway","paving"
 return None
class OverpassClient:
 def __init__(self,timeout=60.,retries=2):self.timeout=timeout;self.retries=retries
 def fetch(self,bbox):
  west,south,east,north=bbox;bb=f"{south},{west},{north},{east}";q=f'''[out:json][timeout:{max(20,int(self.timeout))}];(way["building"]({bb});relation["building"]({bb});way["highway"]({bb});way["railway"~"^(tram|rail|light_rail|subway|narrow_gauge|platform)$"]({bb});node["natural"="tree"]({bb});way["natural"="water"]({bb});relation["natural"="water"]({bb});way["waterway"="riverbank"]({bb});relation["waterway"="riverbank"]({bb});way["leisure"~"^(park|garden)$"]({bb});relation["leisure"~"^(park|garden)$"]({bb});way["landuse"~"^(grass|meadow|recreation_ground|village_green)$"]({bb});relation["landuse"~"^(grass|meadow|recreation_ground|village_green)$"]({bb});way["amenity"="parking"]({bb});relation["amenity"="parking"]({bb});way["highway"="pedestrian"]["area"="yes"]({bb});way["place"="square"]({bb});relation["place"="square"]({bb}););out body geom;''';encoded=urlencode({"data":q}).encode();fails=[]
  for endpoint in OVERPASS_ENDPOINTS:
   for attempt in range(self.retries):
    try:
     req=Request(endpoint,data=encoded,headers={"Accept":"application/json","Content-Type":"application/x-www-form-urlencoded","User-Agent":"BerlinWorldUnity/0.3 (+https://github.com/alexlanderzander/MAP)"})
     with urlopen(req,timeout=self.timeout) as r:payload=json.loads(r.read())
     if not isinstance(payload.get("elements"),list):raise OsmError("Overpass response has no elements array")
     return endpoint,payload
    except (HTTPError,URLError,TimeoutError,OSError,json.JSONDecodeError,OsmError) as ex:
     fails.append(f"{endpoint}: {ex}")
     if attempt+1<self.retries:time.sleep(min(5*(attempt+1),15))
  raise OsmError("All Overpass endpoints failed: "+" | ".join(fails))
def normalize_osm(payload,bbox_utm,tile_size=500):
 buildings=[];roads=[];trees=[];surfaces=[];seen_b=set();seen_r=set();seen_s=set()
 for e in payload.get("elements") or []:
  et=e.get("type");eid=e.get("id");tags=e.get("tags") or {};sid=f"osm:{et}/{eid}";poly=None
  if et in {"way","relation"} and (tags.get("building") or _surface_kind_material(tags)):poly=_utm_geometry(e.get("geometry") or []) if et=="way" else _stitch_outer_relation(e)
  if tags.get("building") and et in {"way","relation"} and poly and len(poly)>=3:
   ring=poly[:-1] if poly[0]==poly[-1] else poly;cx,cy=_centroid(ring)
   if len(ring)>=3 and _inside(cx,cy,bbox_utm) and sid not in seen_b:seen_b.add(sid);buildings.append({"type":"Feature","id":sid,"properties":_building_properties(tags),"geometry":{"type":"Polygon","coordinates":[ring+[ring[0]]]}})
  rail=str(tags.get("railway","")).casefold() in {"tram","rail","light_rail","subway","narrow_gauge"}
  if et=="way" and (tags.get("highway") or rail):
   if not (str(tags.get("area","")).casefold()=="yes" and str(tags.get("highway","")).casefold()=="pedestrian"):
    pts=_utm_geometry(e.get("geometry") or [])
    if len(pts)>=2:
     cls=_road_class(tags);width=_number(tags.get("width"),ROAD_WIDTHS[cls]);lanes=int(max(1,min(255,_number(tags.get("lanes"),1 if cls in {"footway","cycleway","service","tram","rail","platform"} else 2))));part_no=0
     for clipped in clip_line(pts,bbox_utm):
      for (tx,ty),part in split_line_to_tiles(clipped,tile_size):
       pid=f"{sid}:{tx}:{ty}:{part_no}"
       if pid not in seen_r:seen_r.add(pid);roads.append({"type":"Feature","id":pid,"properties":{"width":round(width,2),"lanes":lanes,"class":cls,"surface":_road_surface(tags),"sidewalk_mask":_sidewalk_mask(tags),"flags":_road_flags(tags),"layer":int(max(-128,min(127,_number(tags.get("layer"),0)))),"source":"OpenStreetMap"},"geometry":{"type":"LineString","coordinates":part}})
       part_no+=1
  if et=="node" and tags.get("natural")=="tree" and "lon" in e and "lat" in e:
   x,y=wgs84_to_utm33(float(e["lon"]),float(e["lat"]))
   if _inside(x,y,bbox_utm):
    h=max(1.5,_number(tags.get("height"),8));c=max(.8,_number(tags.get("diameter_crown"),4));sp=tags.get("species") or tags.get("genus") or tags.get("taxon") or "unknown";trees.append({"type":"Feature","id":sid,"properties":{"height":round(h,2),"crown":round(c,2),"species_code":stable_id(sp)&0xffff,"source":"OpenStreetMap"},"geometry":{"type":"Point","coordinates":[x,y]}})
  info=_surface_kind_material(tags)
  if info and et in {"way","relation"} and poly and len(poly)>=3:
   kind,mat=info;ring=poly[:-1] if poly[0]==poly[-1] else poly;part_no=0
   for tx,ty,part in _split_polygon_to_tiles(ring,bbox_utm,tile_size):
    pid=f"{sid}:surface:{tx}:{ty}:{part_no}"
    if pid not in seen_s:seen_s.add(pid);surfaces.append({"type":"Feature","id":pid,"properties":{"kind":kind,"material":mat,"source":"OpenStreetMap"},"geometry":{"type":"Polygon","coordinates":[part+[part[0]]]}})
    part_no+=1
 return {"buildings":{"type":"FeatureCollection","features":buildings},"roads":{"type":"FeatureCollection","features":roads},"trees":{"type":"FeatureCollection","features":trees},"surfaces":{"type":"FeatureCollection","features":surfaces}}
