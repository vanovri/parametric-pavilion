"""Nominal-metre geometry for original, stylized architectural studies."""
import math

DEFAULTS = dict(mode='pagoda', tiers=5, base_width=7.2, tier_height=2.1,
                taper=.82, overhang=1.48, upturn=.48, roof_gap=0., lantern_emission=5.)

def validate(params):
    p=DEFAULTS | params
    if p['mode'] not in ('pagoda','pavilion'): raise ValueError('unknown mode')
    if type(p['tiers']) is not int or not 1<=p['tiers']<=6: raise ValueError('tiers: integer 1..6')
    for k,lo,hi in [('base_width',4,10),('tier_height',1.8,3),('taper',.74,.94),
                    ('overhang',1.25,1.65),('upturn',.1,.7),('roof_gap',0,.7),('lantern_emission',0,10)]:
        v=p[k]
        if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or not lo<=v<=hi:
            raise ValueError(f'invalid {k}')
    if p['mode']=='pavilion' and p['tiers']!=1: raise ValueError('pavilion has one open tier')
    return p

def height(r,theta,upturn):
    # Hip slope transitions into raised square corners, rather than a flat cone.
    corner=abs(math.sin(2*theta))**6
    return 1.05*(1-r)**2 + upturn*r**8*(.2+.8*corner)

def roof_mesh(width,upturn,rings=16,sides=64,thickness=.10):
    """Closed two-sided hip roof with square radial rings and raised corners."""
    if rings<3 or sides<8 or sides%8: raise ValueError('invalid resolution')
    vertices=[];faces=[]
    for layer in (0,1):
        vertices.append((0.,0.,1.05-layer*thickness))
        for ring in range(1,rings+1):
            r=ring/rings
            for i in range(sides):
                a=2*math.pi*i/sides;c=math.cos(a);s=math.sin(a);scale=max(abs(c),abs(s))
                vertices.append((width*.5*r*c/scale,width*.5*r*s/scale,height(r,a,upturn)-layer*thickness))
    n=1+rings*sides
    for layer in (0,1):
        off=layer*n
        for i in range(sides):
            face=(off,off+1+i,off+1+(i+1)%sides)
            faces.append(face if layer==0 else face[::-1])
        for ring in range(rings-1):
            for i in range(sides):
                a=off+1+ring*sides+i;b=off+1+ring*sides+(i+1)%sides
                face=(a,a+sides,b+sides,b)
                faces.append(face if layer==0 else face[::-1])
    for i in range(sides):
        a=1+(rings-1)*sides+i;b=1+(rings-1)*sides+(i+1)%sides
        faces.append((b,a,a+n,b+n))
    return vertices,faces

def tiers(params):
    p=validate(params);z=1.05;rows=[]
    for i in range(p['tiers']):
        width=p['base_width']*p['taper']**i
        roof_z=z+p['tier_height']-.17+p['roof_gap']
        contact=roof_z+height(1/p['overhang'],math.pi/4,p['upturn'])-.05
        rows.append(dict(index=i+1,width=width,bottom=z,roof_z=roof_z,contact=contact))
        z=roof_z+.93
    return rows
