"""Independent mechanical gates. This does not assign aesthetic scores."""
import argparse,hashlib,json,math,struct
from pathlib import Path
from glb_geometry import triangle_models,validate_topology,validate_supports

def verify(root):
    data=json.loads((root/'scene_telemetry.json').read_text())
    raw=(root/'model.glb').read_bytes()
    if len(raw)<20 or struct.unpack('<4sII',raw[:12])!=(b'glTF',2,len(raw)):raise ValueError('invalid GLB header')
    n,kind=struct.unpack('<I4s',raw[12:20]);gltf=json.loads(raw[20:20+n])
    if kind!=b'JSON':raise ValueError('missing GLB JSON')
    if any('uri' in b for b in gltf.get('buffers',[])):raise ValueError('external buffer')
    if hashlib.sha256(raw).hexdigest()!=data['glb_sha256']:raise ValueError('changed GLB')
    source=Path(__file__).resolve().parent
    for filename,key in [('generate_pagoda_bpy.py','generator_sha256'),('geometry.py','geometry_sha256')]:
        if hashlib.sha256((source/filename).read_bytes()).hexdigest()!=data[key]:raise ValueError('generator source differs from build evidence')
    if data['nonmanifold_edges']:raise ValueError('open component mesh')
    models=triangle_models(raw);validate_topology(models)
    support_checks=validate_supports(models,data['params']['tiers'])
    p=data['params'];objects={o['name']:o for o in data['objects']}
    if set(models)!=set(objects):raise ValueError('telemetry component list differs from GLB')
    if p['roof_gap']!=0:raise ValueError('roof gap parameter must be zero')
    if p['tiers']>1 and not .74<=p['taper']<=.88:raise ValueError('tier taper outside study limits')
    if p['lantern_emission']<3:raise ValueError('lantern emission below study gate')
    for row in data['tiers']:
        i=row['index'];roof=objects[f'Tier {i} roof']['bounds']
        if roof[2][1]-roof[2][0]<.8:raise ValueError('flat roof')
        for x in (-1,1):
            for y in (-1,1):
                c=objects[f'Tier {i} column {x} {y}']['bounds']
                if abs(c[2][0]-row['bottom'])>1e-4:raise ValueError('floating column')
                if c[2][1]<roof[2][0]-.05:raise ValueError('column ends below roof range')
    emissions=[m.get('extensions',{}).get('KHR_materials_emissive_strength',{}).get('emissiveStrength',1)
               for m in gltf['materials'] if m.get('emissiveFactor',[0,0,0])!=[0,0,0]]
    if not emissions or max(emissions)<3:raise ValueError('GLB lost lantern emission')
    for view in ('iso','front','top'):
        png=(root/f'{view}.png').read_bytes()
        if png[:8]!=b'\x89PNG\r\n\x1a\n' or len(png)<10000:raise ValueError('missing actual render')
        if hashlib.sha256(png).hexdigest()!=data['render_sha256'][view]:raise ValueError('changed render')
    return dict(model=root.name,mesh_objects=len(gltf['meshes']),components=len(objects),
                nominal_height_m=max(o['bounds'][2][1] for o in objects.values()),
                actual_renders=3,local_roof_contact_samples=support_checks,glb_sha256=data['glb_sha256'],mechanical_gates='pass',aesthetic_score=None)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);a=p.parse_args();print(json.dumps(verify(a.root),indent=2))
