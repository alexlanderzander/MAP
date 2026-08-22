from __future__ import annotations
import argparse,gzip,hashlib,json,math,os,shutil,struct,tempfile,zipfile
from pathlib import Path

BWM_MAGIC=b"BWM1";BWM_VERSION=1
BWM_HEADER=struct.Struct("<4sHHIIHH3d6f");BWM_VERTEX=struct.Struct("<5f3h");BWM_SUBMESH=struct.Struct("<HI")
BWT_HEADER=struct.Struct("<4sHHHHii2dIII");BWT_BUILDING_V1=struct.Struct("<QHHBBH");BWT_BUILDING_V2=struct.Struct("<QHHBBHBBHHH");BWT_POINT=struct.Struct("<hh")
IMAGE_SUFFIXES={".jpg",".jpeg",".png",".tif",".tiff",".bmp",".webp"};AREA_BBOX=(391000.,5820000.,392000.,5821000.);DEFAULT_ORIGIN=(391500.,5820500.)

def _f(v,d=0.):
    try:return float(v)
    except (TypeError,ValueError):return d

def _idx(v,n):
    i=int(v)
    if i==0:raise ValueError("OBJ index 0 is invalid")
    return i-1 if i>0 else n+i

def parse_obj(path):
    vs=[];uv=[];norm=[];faces=[];libs=[];mat="__default__"
    with Path(path).open(encoding="utf-8",errors="replace") as f:
        for raw in f:
            p=raw.strip().split()
            if not p or p[0].startswith("#"):continue
            k=p[0]
            if k=="v" and len(p)>=4:vs.append(tuple(_f(x) for x in p[1:4]))
            elif k=="vt" and len(p)>=3:uv.append((_f(p[1]),_f(p[2])))
            elif k=="vn" and len(p)>=4:norm.append(tuple(_f(x) for x in p[1:4]))
            elif k=="usemtl":mat=" ".join(p[1:]) or "__default__"
            elif k=="mtllib":libs+=p[1:]
            elif k=="f" and len(p)>=4:
                c=[]
                for token in p[1:]:
                    a=token.split("/");c.append((_idx(a[0],len(vs)),_idx(a[1],len(uv)) if len(a)>1 and a[1] else None,_idx(a[2],len(norm)) if len(a)>2 and a[2] else None))
                for i in range(1,len(c)-1):faces.append((mat,[c[0],c[i],c[i+1]]))
    if not vs or not faces:raise ValueError(f"{path} has no usable OBJ geometry")
    return {"vertices":vs,"texcoords":uv,"normals":norm,"faces":faces,"mtllibs":libs}

def parse_mtl(path):
    out={};name="__default__";color=(1.,1.,1.);tex=None;seen=False
    if not Path(path).exists():return out
    def put():out[name]={"color":color,"texture":tex}
    with Path(path).open(encoding="utf-8",errors="replace") as f:
        for raw in f:
            p=raw.strip().split()
            if not p or p[0].startswith("#"):continue
            if p[0]=="newmtl":
                if seen:put()
                name=" ".join(p[1:]) or "__default__";color=(1.,1.,1.);tex=None;seen=True
            elif p[0]=="Kd" and len(p)>=4:color=tuple(max(0.,min(1.,_f(x,1.))) for x in p[1:4])
            elif p[0].lower()=="map_kd" and len(p)>=2:tex=p[-1].strip('"')
    if seen:put()
    return out

def _axis_candidates():return {"xyz":(0,1,2),"xzy":(0,2,1),"yxz":(1,0,2),"yzx":(1,2,0),"zxy":(2,0,1),"zyx":(2,1,0)}

def detect_axis(vertices,bbox=AREA_BBOX):
    if not vertices:raise ValueError("cannot detect empty geometry")
    sample=vertices[::max(1,len(vertices)//20000)];ce=(bbox[0]+bbox[2])/2;cn=(bbox[1]+bbox[3])/2;best=None
    for name,(ei,ni,hi) in _axis_candidates().items():
        e=sum(p[ei] for p in sample)/len(sample);n=sum(p[ni] for p in sample)/len(sample);h=sorted(p[hi] for p in sample)[len(sample)//2]
        score=abs(e-ce)/1000+abs(n-cn)/1000;score=score*.1 if -100<=h<=500 else score+abs(h)/100
        if best is None or score<best[0]:best=(score,name)
    if best[0]>50:raise ValueError("OBJ is not georeferenced near Hackescher Markt; use explicit axis/input origins")
    return best[1]

def axis_winding_flipped(axis):
    e,n,h=_axis_candidates()[axis];p=(e,h,n);return sum(p[i]>p[j] for i in range(3) for j in range(i+1,3))%2==1

def transform_point(p,axis,origin_e,origin_n,base_elev,input_origin_e=None,input_origin_n=None):
    e,n,h=(_axis_candidates()[axis]);E=p[e]+(input_origin_e or 0);N=p[n]+(input_origin_n or 0);return (float(E-origin_e),float(p[h]-base_elev),float(N-origin_n))

def estimate_base_elevation(vertices,axis):
    h=_axis_candidates()[axis][2];a=sorted(float(p[h]) for p in vertices[::max(1,len(vertices)//100000)]);return round(a[min(len(a)-1,int(len(a)*.02))],3) if a else 0.

def _inside(x,z,p):
    inside=False;j=len(p)-1
    for i,(xi,zi) in enumerate(p):
        xj,zj=p[j]
        if (zi>z)!=(zj>z) and x<(xj-xi)*(z-zi)/(zj-zi)+xi:inside=not inside
        j=i
    return inside

def _seg2(px,pz,ax,az,bx,bz):
    dx=bx-ax;dz=bz-az;d=dx*dx+dz*dz
    if d<=1e-12:return (px-ax)**2+(pz-az)**2
    t=max(0.,min(1.,((px-ax)*dx+(pz-az)*dz)/d));return (px-(ax+t*dx))**2+(pz-(az+t*dz))**2

def read_bwt_buildings(path):
    import io
    s=io.BytesIO(gzip.decompress(Path(path).read_bytes()));H=s.read(BWT_HEADER.size)
    if len(H)!=BWT_HEADER.size:raise ValueError("truncated BWT")
    magic,v,q,_,_,_,_,ce,cn,bc,_,_=BWT_HEADER.unpack(H)
    if magic!=b"BWT1" or v not in (1,2):raise ValueError("unsupported BWT")
    scale=q/100.;out=[]
    for _ in range(bc):
        fmt=BWT_BUILDING_V2 if v==2 else BWT_BUILDING_V1;d=s.read(fmt.size)
        if len(d)!=fmt.size:raise ValueError("truncated BWT building")
        vals=fmt.unpack(d);fid=vals[0];count=vals[5];pts=[]
        for _ in range(count):
            d=s.read(BWT_POINT.size)
            if len(d)!=BWT_POINT.size:raise ValueError("truncated BWT points")
            x,z=BWT_POINT.unpack(d);pts.append((ce+x*scale,cn+z*scale))
        if len(pts)>=3:
            xs=[x for x,_ in pts];zs=[z for _,z in pts];out.append((fid,pts,min(xs),min(zs),max(xs),max(zs)))
    return out

def load_semantic_buildings(folder):
    if not folder or not Path(folder).exists():return []
    out=[]
    for p in sorted(Path(folder).glob("tile_*.bwt.gz")):out+=read_bwt_buildings(p)
    return out

class BuildingSpatialIndex:
    def __init__(self,buildings,cell=25.):
        self.cell=cell;self.grid={}
        for b in buildings:
            for x in range(math.floor((b[2]-1)/cell),math.floor((b[4]+1)/cell)+1):
                for z in range(math.floor((b[3]-1)/cell),math.floor((b[5]+1)/cell)+1):self.grid.setdefault((x,z),[]).append(b)
    def owner(self,e,n,h):
        if h<.65:return 0
        near=0;best=1.
        for b in self.grid.get((math.floor(e/self.cell),math.floor(n/self.cell)),()):
            if not(b[2]-1<=e<=b[4]+1 and b[3]-1<=n<=b[5]+1):continue
            if _inside(e,n,b[1]):return b[0]
            for i,(ax,az) in enumerate(b[1]):
                bx,bz=b[1][(i+1)%len(b[1])];d=_seg2(e,n,ax,az,bx,bz)
                if d<best:best=d;near=b[0]
        return near

def collect_sources(input_path,temp_root):
    p=Path(input_path)
    if p.is_dir() and list(p.rglob("*.obj")):return sorted(p.rglob("*.obj"))
    archives=[p] if p.is_file() and p.suffix.lower()==".zip" else sorted(p.rglob("*.zip")) if p.is_dir() else []
    if not archives:raise ValueError("--input must contain OBJ or ZIP files")
    out=[]
    for i,a in enumerate(archives):
        dest=Path(temp_root)/f"zip_{i:04d}";dest.mkdir(parents=True,exist_ok=True);root=str(dest.resolve())+os.sep
        with zipfile.ZipFile(a) as z:
            for m in z.infolist():
                target=(dest/m.filename).resolve()
                if not str(target).startswith(root):raise ValueError(f"unsafe path in ZIP: {m.filename}")
                if m.is_dir():target.mkdir(parents=True,exist_ok=True);continue
                target.parent.mkdir(parents=True,exist_ok=True)
                with z.open(m) as src,target.open("wb") as dst:shutil.copyfileobj(src,dst)
        out+=sorted(dest.rglob("*.obj"))
    if not out:raise ValueError("no OBJ files found")
    return out

def _copy_tex(src,dst):
    data=Path(src).read_bytes();h=hashlib.blake2b(data,digest_size=8).hexdigest();name=f"{Path(src).stem}_{h}{Path(src).suffix.lower()}";Path(dst).mkdir(parents=True,exist_ok=True);target=Path(dst)/name
    if not target.exists():target.write_bytes(data)
    return f"Textures/{name}"

def _n16(n):
    l=math.sqrt(sum(x*x for x in n))
    return (0,32767,0) if l<1e-12 else tuple(int(max(-32767,min(32767,round(x/l*32767)))) for x in n)

def process_obj(path,out,no,axis,origin_e,origin_n,base_elev,input_origin_e=None,input_origin_n=None,spatial=None):
    o=parse_obj(path);defs={"__default__":{"color":(1.,1.,1.),"texture":None}}
    for lib in o["mtllibs"]:defs.update(parse_mtl(Path(path).parent/lib))
    mats=[]
    for m,_ in o["faces"]:
        if m not in mats:mats.append(m)
    mi={m:i for i,m in enumerate(mats)};imap={};verts=[];indices=[[] for _ in mats];owners=[[] for _ in mats];owner_ids=[];owner_map={};mapping=_axis_candidates()[axis]
    def vertex(c):
        if c in imap:return imap[c]
        vi,ti,ni=c;x,y,z=transform_point(o["vertices"][vi],axis,origin_e,origin_n,base_elev,input_origin_e,input_origin_n);u,v=o["texcoords"][ti] if ti is not None else (0.,0.)
        nn=_n16((o["normals"][ni][mapping[0]],o["normals"][ni][mapping[2]],o["normals"][ni][mapping[1]])) if ni is not None else (0,0,0);i=len(verts);verts.append((x,y,z,u,v,*nn));imap[c]=i;return i
    for material,corners in o["faces"]:
        m=mi[material];idx=[vertex(c) for c in corners]
        if axis_winding_flipped(axis):idx[1],idx[2]=idx[2],idx[1]
        indices[m]+=idx;code=0
        if spatial:
            p=[verts[i] for i in idx];bid=spatial.owner(origin_e+sum(x[0] for x in p)/3,origin_n+sum(x[2] for x in p)/3,sum(x[1] for x in p)/3)
            if bid:
                code=owner_map.get(bid,0)
                if not code:owner_ids.append(bid);code=len(owner_ids);owner_map[bid]=code
        owners[m].append(code)
    if not verts:raise ValueError(f"no renderable vertices in {path}")
    if len(owner_ids)>65534:raise ValueError("too many building owners")
    xs=[v[0] for v in verts];ys=[v[1] for v in verts];zs=[v[2] for v in verts];bounds=(min(xs),min(ys),min(zs),max(xs),max(ys),max(zs));flags=int(all(v[5] or v[6] or v[7] for v in verts))
    raw=bytearray(BWM_HEADER.pack(BWM_MAGIC,1,flags,len(verts),len(mats),len(owner_ids),0,origin_e,origin_n,base_elev,*bounds))
    for v in verts:raw+=BWM_VERTEX.pack(*v)
    for b in owner_ids:raw+=struct.pack("<Q",b)
    for m,idx in enumerate(indices):
        raw+=BWM_SUBMESH.pack(m,len(idx));raw+=struct.pack(f"<{len(idx)}I",*idx) if idx else b"";raw+=struct.pack("<I",len(owners[m]));raw+=struct.pack(f"<{len(owners[m])}H",*owners[m]) if owners[m] else b""
    chunk=Path(out)/f"chunk_{no:04d}.bwm.gz";chunk.write_bytes(gzip.compress(bytes(raw),9,mtime=0));manifest=[]
    for m in mats:
        info=defs.get(m,defs["__default__"]);tex=None
        if info["texture"]:
            p=(Path(path).parent/info["texture"]).resolve()
            if p.exists() and p.suffix.lower() in IMAGE_SUFFIXES:tex=_copy_tex(p,Path(out)/"Textures")
        manifest.append({"name":m,"baseColor":list(info["color"]),"texture":tex})
    return {"file":chunk.name,"sourceObj":Path(path).name,"vertices":len(verts),"triangles":sum(len(x)//3 for x in indices),"owners":len(owner_ids),"boundsLocal":list(bounds),"materials":manifest,"compressedBytes":chunk.stat().st_size}

def build(a):
    inp=Path(a.input).expanduser().resolve();out=Path(a.out).expanduser().resolve()
    if out.exists() and a.clean:shutil.rmtree(out)
    out.mkdir(parents=True,exist_ok=True);buildings=load_semantic_buildings(Path(a.semantic_tiles).expanduser().resolve() if a.semantic_tiles else None);spatial=BuildingSpatialIndex(buildings) if buildings else None
    with tempfile.TemporaryDirectory(prefix="berlin-photo-") as td:
        objs=collect_sources(inp,Path(td));first=parse_obj(objs[0]);axis=detect_axis(first["vertices"],tuple(a.area_bbox)) if a.axis=="auto" else a.axis;base=a.base_elevation if a.base_elevation is not None else estimate_base_elevation(first["vertices"],axis)
        chunks=[process_obj(p,out,i,axis,a.origin_e,a.origin_n,base,a.input_origin_e,a.input_origin_n,spatial) for i,p in enumerate(objs)]
    m={"format":"BWM1","version":1,"source":"Berlin 3D Meshmodell / user-provided portal export","surveyDate":"2025-06-13","crs":"EPSG:25833","axisMapping":axis,"originEasting":a.origin_e,"originNorthing":a.origin_n,"baseElevation":base,"semanticBuildingOwners":len(buildings),"redistributionPolicy":"The packer never downloads Berlin portal data. Input must be a user-obtained export accepted under the provider terms; check those terms before redistributing packed geometry/textures.","fidelity":{"geometry":"source OBJ vertices preserved as float32 after local-origin translation","textures":"source texture bytes copied unchanged","destruction":"triangle owners bound to BWT semantic building IDs when --semantic-tiles is provided"},"chunks":chunks}
    (out/"photogrammetry_manifest.json").write_text(json.dumps(m,indent=2)+"\n",encoding="utf-8");print(f"Packed {len(chunks)} photogrammetry chunks, {sum(c['triangles'] for c in chunks):,} triangles, {sum(c['compressedBytes'] for c in chunks):,} compressed geometry bytes")
    if not buildings:print("WARNING: no semantic BWT tiles supplied; destructive cut-out ownership is disabled.")
    return 0

def main():
    p=argparse.ArgumentParser(description="Pack official Berlin 2025 textured OBJ tiles into Unity BWM1 chunks");p.add_argument("--input",required=True);p.add_argument("--out",required=True);p.add_argument("--semantic-tiles");p.add_argument("--axis",choices=("auto",*_axis_candidates()),default="auto");p.add_argument("--origin-e",type=float,default=DEFAULT_ORIGIN[0]);p.add_argument("--origin-n",type=float,default=DEFAULT_ORIGIN[1]);p.add_argument("--base-elevation",type=float);p.add_argument("--input-origin-e",type=float);p.add_argument("--input-origin-n",type=float);p.add_argument("--area-bbox",type=float,nargs=4,default=AREA_BBOX);p.add_argument("--clean",action="store_true");a=p.parse_args()
    try:return build(a)
    except (ValueError,OSError,zipfile.BadZipFile) as e:p.error(str(e));return 2
if __name__=="__main__":raise SystemExit(main())
