"""Read embedded glTF triangle positions directly. No Blender telemetry dependency."""
from collections import Counter
import json,math,struct

def triangle_models(raw):
    length,kind=struct.unpack_from('<I4s',raw,12)
    if kind!=b'JSON':raise ValueError('JSON chunk required')
    gltf=json.loads(raw[20:20+length]);offset=20+length
    size,kind=struct.unpack_from('<I4s',raw,offset)
    if kind!=b'BIN\0':raise ValueError('embedded binary required')
    binary=raw[offset+8:offset+8+size]
    def accessor(index):
        a=gltf['accessors'][index];v=gltf['bufferViews'][a['bufferView']]
        fmt={5126:'f',5125:'I',5123:'H'}[a['componentType']];count={'SCALAR':1,'VEC3':3}[a['type']]
        stride=v.get('byteStride',struct.calcsize('<'+fmt)*count);start=v.get('byteOffset',0)+a.get('byteOffset',0)
        if a.get('sparse') or v.get('buffer',0)!=0:raise ValueError('unsupported accessor')
        return [struct.unpack_from('<'+fmt*count,binary,start+i*stride) for i in range(a['count'])]
    def transform(v,node):
        if 'matrix' in node:
            m=node['matrix'];return tuple(sum(m[r+4*c]*v[c] for c in range(3))+m[r+12] for r in range(3))
        v=[a*b for a,b in zip(v,node.get('scale',[1,1,1]))]
        x,y,z,w=node.get('rotation',[0,0,0,1]);q=(x,y,z)
        cross=lambda a,b:(a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])
        u=cross(q,v);uu=cross(q,u);t=node.get('translation',[0,0,0])
        return tuple(v[i]+2*(w*u[i]+uu[i])+t[i] for i in range(3))
    models={}
    def visit(index,parents):
        node=gltf['nodes'][index];chain=[node]+parents
        if 'mesh' in node:
            triangles=[]
            for primitive in gltf['meshes'][node['mesh']]['primitives']:
                if primitive.get('mode',4)!=4:raise ValueError('triangles required')
                positions=accessor(primitive['attributes']['POSITION']);indices=[x[0] for x in accessor(primitive['indices'])]
                transformed=[]
                for p in positions:
                    for n in chain:p=transform(p,n)
                    if not all(math.isfinite(v) for v in p):raise ValueError('non-finite GLB position')
                    transformed.append(p)
                triangles.extend(tuple(transformed[j] for j in indices[i:i+3]) for i in range(0,len(indices),3))
            models[node['name']]=triangles
        for child in node.get('children',[]):visit(child,chain)
    for index in gltf['scenes'][gltf.get('scene',0)]['nodes']:visit(index,[])
    return models

def validate_topology(models):
    for name,triangles in models.items():
        edges=Counter()
        for triangle in triangles:
            points=[tuple(round(x,5) for x in v) for v in triangle]
            if len(set(points))!=3:raise ValueError('degenerate triangle '+name)
            for a,b in zip(points,points[1:]+points[:1]):edges[a,b]+=1
        if any(n!=1 or edges[b,a]!=1 for (a,b),n in edges.items()):raise ValueError('open or inconsistently oriented GLB component '+name)

def vertical_surface(triangles,x,z):
    hits=[]
    for a,b,c in triangles:
        denominator=(b[2]-c[2])*(a[0]-c[0])+(c[0]-b[0])*(a[2]-c[2])
        if abs(denominator)<1e-10:continue
        u=((b[2]-c[2])*(x-c[0])+(c[0]-b[0])*(z-c[2]))/denominator
        v=((c[2]-a[2])*(x-c[0])+(a[0]-c[0])*(z-c[2]))/denominator
        if u>=-1e-6 and v>=-1e-6 and u+v<=1+1e-6:hits.append(u*a[1]+v*b[1]+(1-u-v)*c[1])
    if len(hits)<2:raise ValueError('no local roof intersection')
    return min(hits),max(hits)

def validate_supports(models,tiers):
    if sum(name.endswith(' roof') for name in models)!=tiers:raise ValueError('wrong roof count')
    if sum(' column ' in name for name in models)!=4*tiers:raise ValueError('wrong column count')
    checks=0
    for tier in range(1,tiers+1):
        roof=models[f'Tier {tier} roof']
        for name,triangles in models.items():
            if not name.startswith(f'Tier {tier} '):continue
            if ' column ' not in name and ' lintel' not in name:continue
            points=[v for t in triangles for v in t];bounds=[(min(v[a] for v in points),max(v[a] for v in points)) for a in range(3)]
            top=bounds[1][1]
            if ' column ' in name:
                for theta in range(16):
                    a=theta*math.pi/8;x=sum(bounds[0])/2+math.cos(a)*(bounds[0][1]-bounds[0][0])*.5
                    z=sum(bounds[2])/2+math.sin(a)*(bounds[2][1]-bounds[2][0])*.5
                    lower,upper=vertical_surface(roof,x,z)
                    if top>upper-.015 or top<lower-.06:raise ValueError('column/roof contact violation '+name)
                    checks+=1
            else:
                for k in range(17):
                    t=k/16
                    x=bounds[0][0]+t*(bounds[0][1]-bounds[0][0]) if 'lintelX' in name else sum(bounds[0])/2
                    z=bounds[2][0]+t*(bounds[2][1]-bounds[2][0]) if 'lintelY' in name else sum(bounds[2])/2
                    lower,upper=vertical_surface(roof,x,z)
                    if top>lower+.005:raise ValueError('lintel penetrates roof '+name)
                    checks+=1
    return checks
