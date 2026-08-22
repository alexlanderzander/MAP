from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import hashlib
import io
import math
import struct

MAGIC = b"BWT1"
VERSION = 2
QUANT_CM = 2
MAX_Q = 32767
MIN_Q = -32768
HEADER = struct.Struct("<4sHHHHii2dIII")
BUILDING_V1 = struct.Struct("<QHHBBH")
BUILDING_V2 = struct.Struct("<QHHBBHBBHHH")
ROAD_V1 = struct.Struct("<QBBHH")
ROAD_V2 = struct.Struct("<QBBHHBBBb")
SURFACE_V2 = struct.Struct("<QBBH")
TREE = struct.Struct("<QhhHHH")
POINT = struct.Struct("<hh")

BUILDING_CLASSES = {"unknown": 0, "residential": 1, "commercial": 2, "industrial": 3, "public": 4, "historic": 5}
ROOF_TYPES = {"flat": 0, "gabled": 1, "hipped": 2, "mansard": 3, "shed": 4, "pyramidal": 5, "dome": 6}
FACADE_TYPES = {"unknown": 0, "plaster": 1, "brick": 2, "glass": 3, "concrete": 4, "stone": 5, "metal": 6, "timber": 7}
ROAD_CLASSES = {"unknown": 0, "motorway": 1, "trunk": 2, "primary": 3, "secondary": 4, "tertiary": 5, "residential": 6, "service": 7, "footway": 8, "cycleway": 9, "tram": 10, "rail": 11, "platform": 12}
ROAD_SURFACES = {"unknown": 0, "asphalt": 1, "paving": 2, "sett": 3, "cobblestone": 4, "concrete": 5, "gravel": 6, "unpaved": 7, "grass": 8}
SURFACE_KINDS = {"unknown": 0, "water": 1, "grass": 2, "park": 3, "pedestrian": 4, "plaza": 5, "parking": 6, "railway": 7, "building_courtyard": 8}
SURFACE_MATERIALS = {"unknown": 0, "water": 1, "grass": 2, "paving": 3, "asphalt": 4, "gravel": 5, "sand": 6, "concrete": 7}

ROAD_FLAG_BRIDGE = 1 << 0
ROAD_FLAG_TUNNEL = 1 << 1
ROAD_FLAG_TRAM = 1 << 2
ROAD_FLAG_RAIL = 1 << 3
ROAD_FLAG_STEPS = 1 << 4


def stable_id(value: object) -> int:
    if isinstance(value, int): return value & 0xFFFFFFFFFFFFFFFF
    return int.from_bytes(hashlib.blake2b(str(value).encode("utf-8"), digest_size=8).digest(), "little")


def enum_value(value: object, mapping: dict[str, int]) -> int:
    if isinstance(value, int):
        if 0 <= value <= 255: return value
        raise ValueError(f"enum integer out of byte range: {value}")
    return mapping.get(str(value).lower(), 0)


def q_meters(value_m: float) -> int:
    q = int(round(value_m * 100.0 / QUANT_CM))
    if not MIN_Q <= q <= MAX_Q: raise ValueError(f"coordinate delta {value_m:.2f} m exceeds BWT quantization range")
    return q


def uq_meters(value_m: float) -> int:
    q = int(round(max(0.0, value_m) * 100.0 / QUANT_CM))
    if q > 65535: raise ValueError(f"value {value_m:.2f} m exceeds BWT uint16 range")
    return q


def rgb565(value: object, fallback: int = 0) -> int:
    if isinstance(value, int): return max(0, min(65535, value))
    if value in (None, ""): return fallback
    text = str(value).strip().lower()
    names = {"white":"#f1eee7","grey":"#aaa7a1","gray":"#aaa7a1","beige":"#d7c9a7","brown":"#8a6847","red":"#a65b4d","yellow":"#d8c77c","black":"#343331","cream":"#e5dcc4","green":"#78806a","blue":"#71899a","orange":"#b9794d"}
    text = names.get(text, text)
    if text.startswith("#"):
        h = text[1:]
        if len(h) == 3: h = "".join(ch * 2 for ch in h)
        if len(h) == 6:
            try:
                r,g,b = int(h[0:2],16),int(h[2:4],16),int(h[4:6],16)
                packed = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
                return packed or 1
            except ValueError: pass
    return fallback

@dataclass(slots=True)
class Building:
    feature_id:int; footprint:list[tuple[float,float]]; height_m:float; min_height_m:float=0.0; roof_type:int=0; building_class:int=0; levels:int=0; facade_type:int=0; roof_height_m:float=0.0; facade_color:int=0; roof_color:int=0
@dataclass(slots=True)
class Road:
    feature_id:int; points:list[tuple[float,float]]; width_m:float; lanes:int=1; road_class:int=0; surface_type:int=0; sidewalk_mask:int=0; flags:int=0; layer:int=0
@dataclass(slots=True)
class Tree:
    feature_id:int; x_m:float; z_m:float; height_m:float=8.0; crown_m:float=4.0; species_code:int=0
@dataclass(slots=True)
class Surface:
    feature_id:int; footprint:list[tuple[float,float]]; kind:int=0; material:int=0
@dataclass(slots=True)
class Tile:
    tile_x:int; tile_z:int; tile_size_m:int; center_easting_m:float; center_northing_m:float; buildings:list[Building]=field(default_factory=list); roads:list[Road]=field(default_factory=list); trees:list[Tree]=field(default_factory=list); surfaces:list[Surface]=field(default_factory=list)

def _pack_local_point(buf:io.BytesIO,x_m:float,z_m:float,tile:Tile)->None:
    buf.write(POINT.pack(q_meters(x_m-tile.center_easting_m),q_meters(z_m-tile.center_northing_m)))

def encode_tile(tile:Tile,version:int=VERSION)->bytes:
    if version != 2: raise ValueError("encoder writes BWT version 2 only")
    if not 1 <= tile.tile_size_m <= 600: raise ValueError("tile size must be 1..600 m")
    if len(tile.surfaces)>65535: raise ValueError("too many surfaces in one tile")
    buf=io.BytesIO(); buf.write(HEADER.pack(MAGIC,version,QUANT_CM,tile.tile_size_m,len(tile.surfaces),tile.tile_x,tile.tile_z,tile.center_easting_m,tile.center_northing_m,len(tile.buildings),len(tile.roads),len(tile.trees)))
    for b in tile.buildings:
        if len(b.footprint)<3 or len(b.footprint)>65535: raise ValueError("building footprint must contain 3..65535 vertices")
        buf.write(BUILDING_V2.pack(b.feature_id,uq_meters(b.height_m),uq_meters(b.min_height_m),b.roof_type,b.building_class,len(b.footprint),max(0,min(255,int(b.levels))),max(0,min(255,int(b.facade_type))),uq_meters(b.roof_height_m),max(0,min(65535,int(b.facade_color))),max(0,min(65535,int(b.roof_color)))))
        for x,z in b.footprint:_pack_local_point(buf,x,z,tile)
    for r in tile.roads:
        if len(r.points)<2 or len(r.points)>65535: raise ValueError("road must contain 2..65535 points")
        buf.write(ROAD_V2.pack(r.feature_id,r.road_class,max(0,min(255,int(r.lanes))),uq_meters(r.width_m),len(r.points),max(0,min(255,int(r.surface_type))),max(0,min(255,int(r.sidewalk_mask))),max(0,min(255,int(r.flags))),max(-128,min(127,int(r.layer)))))
        for x,z in r.points:_pack_local_point(buf,x,z,tile)
    for t in tile.trees: buf.write(TREE.pack(t.feature_id,q_meters(t.x_m-tile.center_easting_m),q_meters(t.z_m-tile.center_northing_m),uq_meters(t.height_m),uq_meters(t.crown_m),max(0,min(65535,int(t.species_code)))))
    for s in tile.surfaces:
        if len(s.footprint)<3 or len(s.footprint)>65535: raise ValueError("surface footprint must contain 3..65535 vertices")
        buf.write(SURFACE_V2.pack(s.feature_id,max(0,min(255,int(s.kind))),max(0,min(255,int(s.material))),len(s.footprint)))
        for x,z in s.footprint:_pack_local_point(buf,x,z,tile)
    return buf.getvalue()

def encode_tile_gzip(tile:Tile,compresslevel:int=9)->bytes:return gzip.compress(encode_tile(tile),compresslevel=compresslevel,mtime=0)
def _read_exact(stream:io.BytesIO,size:int)->bytes:
    data=stream.read(size)
    if len(data)!=size:raise ValueError("truncated BWT tile")
    return data

def decode_tile(data:bytes)->Tile:
    stream=io.BytesIO(data); magic,version,quant_cm,tile_size,reserved,tx,tz,ce,cn,bc,rc,tc=HEADER.unpack(_read_exact(stream,HEADER.size))
    if magic!=MAGIC or version not in (1,2):raise ValueError("unsupported BWT tile")
    scale=quant_cm/100.0; tile=Tile(tx,tz,tile_size,ce,cn)
    for _ in range(bc):
        if version==1:
            fid,hq,mhq,roof,cls,count=BUILDING_V1.unpack(_read_exact(stream,BUILDING_V1.size)); levels=facade=roof_hq=facade_color=roof_color=0
        else: fid,hq,mhq,roof,cls,count,levels,facade,roof_hq,facade_color,roof_color=BUILDING_V2.unpack(_read_exact(stream,BUILDING_V2.size))
        pts=[]
        for _ in range(count):qx,qz=POINT.unpack(_read_exact(stream,POINT.size));pts.append((ce+qx*scale,cn+qz*scale))
        tile.buildings.append(Building(fid,pts,hq*scale,mhq*scale,roof,cls,levels,facade,roof_hq*scale,facade_color,roof_color))
    for _ in range(rc):
        if version==1:
            fid,cls,lanes,widthq,count=ROAD_V1.unpack(_read_exact(stream,ROAD_V1.size));surface=sidewalk=flags=layer=0
        else: fid,cls,lanes,widthq,count,surface,sidewalk,flags,layer=ROAD_V2.unpack(_read_exact(stream,ROAD_V2.size))
        pts=[]
        for _ in range(count):qx,qz=POINT.unpack(_read_exact(stream,POINT.size));pts.append((ce+qx*scale,cn+qz*scale))
        tile.roads.append(Road(fid,pts,widthq*scale,lanes,cls,surface,sidewalk,flags,layer))
    for _ in range(tc):
        fid,qx,qz,hq,cq,species=TREE.unpack(_read_exact(stream,TREE.size));tile.trees.append(Tree(fid,ce+qx*scale,cn+qz*scale,hq*scale,cq*scale,species))
    if version==2:
        for _ in range(reserved):
            fid,kind,material,count=SURFACE_V2.unpack(_read_exact(stream,SURFACE_V2.size));pts=[]
            for _ in range(count):qx,qz=POINT.unpack(_read_exact(stream,POINT.size));pts.append((ce+qx*scale,cn+qz*scale))
            tile.surfaces.append(Surface(fid,pts,kind,material))
    if stream.read(1):raise ValueError("unexpected trailing bytes in BWT tile")
    return tile

def decode_tile_gzip(data:bytes)->Tile:return decode_tile(gzip.decompress(data))
def tile_index(x_m:float,z_m:float,tile_size_m:int)->tuple[int,int]:return math.floor(x_m/tile_size_m),math.floor(z_m/tile_size_m)
def tile_center(tx:int,tz:int,tile_size_m:int)->tuple[float,float]:return (tx+0.5)*tile_size_m,(tz+0.5)*tile_size_m
