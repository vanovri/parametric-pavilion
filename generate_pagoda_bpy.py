"""Run with Blender: blender -b -t 4 -P generate_pagoda_bpy.py -- params.json output/"""
import hashlib,json,math,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import validate,roof_mesh,tiers
import bpy,bmesh
from mathutils import Vector

def main():
    param_path,out=map(Path,sys.argv[sys.argv.index('--')+1:]);out.mkdir(parents=True,exist_ok=True)
    p=validate(json.loads(param_path.read_text())); rows=tiers(p)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    materials={}
    for name,color,metal,rough,emission in [
        ('Stone',(.35,.32,.26,1),0,.85,0),('Timber',(.34,.045,.025,1),0,.48,0),
        ('Roof',(.035,.095,.095,1),.18,.4,0),('Gold',(.7,.4,.07,1),.7,.3,0),
        ('Lantern',(1,.35,.055,1),0,.5,p['lantern_emission']),('Plaster',(.65,.48,.3,1),0,.8,0)]:
        m=bpy.data.materials.new(name);m.use_nodes=True;b=m.node_tree.nodes.get('Principled BSDF')
        b.inputs['Base Color'].default_value=color;b.inputs['Metallic'].default_value=metal
        b.inputs['Roughness'].default_value=rough;b.inputs['Emission Color'].default_value=color
        b.inputs['Emission Strength'].default_value=emission;materials[name]=m
    model=[]
    def finish(name,mat):
        obj=bpy.context.object;obj.name=name;obj.data.materials.append(materials[mat]);model.append(obj);return obj
    def box(name,loc,scale,mat):
        bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=finish(name,mat);o.scale=scale
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        bevel=o.modifiers.new('Small softened edges','BEVEL');bevel.width=.025;bevel.segments=2
        o.modifiers.new('Weighted normals','WEIGHTED_NORMAL');return o
    def cylinder(name,loc,radius,depth,mat):
        bpy.ops.mesh.primitive_cylinder_add(vertices=16,radius=radius,depth=depth,location=loc)
        return finish(name,mat)
    w=p['base_width']
    box('Podium lower',(0,0,.28),(w*1.65,w*1.65,.56),'Stone')
    box('Podium upper',(0,0,.79),(w*1.38,w*1.38,.46),'Stone')
    # Three entry steps touch the podium and one another.
    for j in range(3):box(f'Entry step {j}',(0,-w*.75-.65+j*.23,.12+j*.14),(w*.48,.72,.24+j*.28),'Stone')
    for row in rows:
        i=row['index'];w=row['width'];z=row['bottom'];rz=row['roof_z'];c=row['contact']
        box(f'Tier {i} floor',(0,0,z-.05),(w*1.1,w*1.1,.16),'Stone')
        if p['mode']=='pagoda':
            core_top=rz+height_at(.63/p['overhang'],math.pi/4,p)-.08
            box(f'Tier {i} core',(0,0,(z+core_top)/2),(w*.63,w*.63,core_top-z),'Plaster')
            # Vertical timber lattice, all bars terminate at floor/lintel.
            for side in (-1,1):
                for k in range(-3,4):
                    box(f'Tier {i} latticeX {side} {k}',(k*w*.085,side*w*.322,(z+rz)/2),(.055,.065,rz-z),'Timber')
                    box(f'Tier {i} latticeY {side} {k}',(side*w*.322,k*w*.085,(z+rz)/2),(.065,.055,rz-z),'Timber')
        for x in (-1,1):
            for y in (-1,1):
                cylinder(f'Tier {i} column {x} {y}',(x*w*.47,y*w*.47,(z+c)/2),w*.026,c-z,'Timber')
        # Four lintels bridge the columns and meet the roof underside.
        for side in (-1,1):
            box(f'Tier {i} lintelX {side}',(0,side*w*.47,rz-.12),(w*1.02,.16,.20),'Timber')
            box(f'Tier {i} lintelY {side}',(side*w*.47,0,rz-.12),(.16,w*1.02,.20),'Timber')
        verts,faces=roof_mesh(w*p['overhang'],p['upturn'])
        mesh=bpy.data.meshes.new(f'Curved roof {i}');mesh.from_pydata(verts,[],faces);mesh.update()
        roof=bpy.data.objects.new(f'Tier {i} roof',mesh);bpy.context.collection.objects.link(roof)
        roof.location.z=rz;roof.data.materials.append(materials['Roof']);model.append(roof)
        for poly in mesh.polygons:poly.use_smooth=True
        # Gold ribs are surface-following curves, tied into the roof at each endpoint.
        for k in range(4):
            a=math.pi/4+k*math.pi/2;curve=bpy.data.curves.new('Hip ridge','CURVE');curve.dimensions='3D'
            curve.bevel_depth=.022;curve.bevel_resolution=2;curve.use_fill_caps=True;s=curve.splines.new('POLY');s.points.add(20)
            for j,point in enumerate(s.points):
                r=j/20;point.co=(w*p['overhang']*.5*r*(1 if math.cos(a)>0 else -1),w*p['overhang']*.5*r*(1 if math.sin(a)>0 else -1),rz+height_at(r,a,p)+.025,1)
            ob=bpy.data.objects.new(f'Tier {i} ridge {k}',curve);bpy.context.collection.objects.link(ob);ob.data.materials.append(materials['Gold']);model.append(ob)
        for x in (-1,1):
            for y in (-1,1):
                offset=w*.59; r=offset/(w*p['overhang']*.5);attach=rz+height_at(r,math.pi/4,p)-.08
                cylinder(f'Tier {i} lantern hanger {x} {y}',(x*offset,y*offset,attach-.19),.025,.40,'Gold')
                bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.14,location=(x*offset,y*offset,attach-.43))
                o=finish(f'Tier {i} lantern {x} {y}','Lantern');o.scale=(1,1,1.3)
                cylinder(f'Tier {i} lantern cap {x} {y}',(x*offset,y*offset,attach-.27),.15,.06,'Gold')
    top=rows[-1]['roof_z']+1.02
    cylinder('Finial shaft',(0,0,top+.8),.07,1.7,'Gold')
    for j in range(5):
        bpy.ops.mesh.primitive_torus_add(major_segments=24,minor_segments=8,location=(0,0,top+.22+j*.27),major_radius=.28-j*.035,minor_radius=.035)
        finish(f'Finial ring {j}','Gold')
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=8,radius=.14,location=(0,0,top+1.7));finish('Finial tip','Gold')
    # Export model only. Ground, render camera and lights do not pollute GLB.
    bpy.ops.object.select_all(action='DESELECT')
    for o in model:o.select_set(True)
    # Curve end caps contain coincident but separate boundary vertices in Blender.
    # Weld the actual converted mesh, rather than hiding open edges in telemetry.
    for o in model:
        if o.type=='CURVE':
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
            bpy.ops.object.convert(target='MESH')
            bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
            bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
    bpy.ops.object.select_all(action='DESELECT')
    for o in model:o.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(out/'model.glb'),export_format='GLB',use_selection=True,export_yup=True)
    deps=bpy.context.evaluated_depsgraph_get();tele=[];nonmanifold=0
    for o in model:
        evaluated=o.evaluated_get(deps);mesh=evaluated.to_mesh()
        if mesh:
            bm=bmesh.new();bm.from_mesh(mesh);bad=sum(not e.is_manifold for e in bm.edges);nonmanifold+=bad;bm.free()
            coords=[o.matrix_world@v.co for v in mesh.vertices]
            tele.append(dict(name=o.name,vertices=len(mesh.vertices),polygons=len(mesh.polygons),nonmanifold_edges=bad,
                             bounds=[[min(v[a] for v in coords),max(v[a] for v in coords)] for a in range(3)]))
            evaluated.to_mesh_clear()
    report=dict(engine='Blender '+bpy.app.version_string,units='nominal metres',params=p,tiers=rows,objects=tele,
                nonmanifold_edges=nonmanifold,assembly='separate closed overlapping components, not a single watertight solid',
                glb_sha256=hashlib.sha256((out/'model.glb').read_bytes()).hexdigest())
    # Actual CPU Cycles renders. No metadata-only fallback.
    bpy.ops.mesh.primitive_plane_add(size=20000);ground=bpy.context.object;ground.name='Render ground';ground.data.materials.append(materials['Stone'])
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=64
    scene.cycles.use_denoising=True;scene.render.resolution_x=640;scene.render.resolution_y=800;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('World');scene.world.use_nodes=True;scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.16,.20,.22,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
    h=top+1.9
    for name,location,power,size in [('Key',(12,-15,24),4200,10),('Fill',(-12,-3,12),1800,8),('Rim',(5,10,20),3000,8)]:
        light=bpy.data.lights.new(name,'AREA');light.energy=power;light.shape='DISK';light.size=size
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=location;ob.rotation_euler=(Vector((0,0,h*.45))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('Camera');ob=bpy.data.objects.new('Camera',camera);scene.collection.objects.link(ob);scene.camera=ob;camera.type='ORTHO';camera.ortho_scale=max(h*1.21,p['base_width']*2)
    camera.clip_end=2000
    for name,location in [('iso',(21,-28,h*.95)),('front',(0,-32,h*.55)),('top',(0,-.01,40))]:
        ob.location=location;ob.rotation_euler=(Vector((0,0,h*.45))-ob.location).to_track_quat('-Z','Y').to_euler()
        bpy.context.view_layer.update()
        inverse=ob.matrix_world.inverted()
        points=[inverse@(part.matrix_world@Vector(corner)) for part in model for corner in part.bound_box]
        xmin,xmax=min(v.x for v in points),max(v.x for v in points)
        ymin,ymax=min(v.y for v in points),max(v.y for v in points)
        # Fit portrait aspect and projected diagonal, including roof tips and entry steps.
        camera.ortho_scale=max(ymax-ymin,(xmax-xmin)/(640/800))*1.12
        shift=ob.rotation_euler.to_quaternion()@Vector(((xmin+xmax)/2,(ymin+ymax)/2,0))
        ob.location+=shift
        # Fit actual orthographic frustum ray origins above the floor. A fixed
        # retreat fails at shallow front angles even when the model is in frame.
        bpy.context.view_layer.update()
        frame=[ob.matrix_world@corner for corner in camera.view_frame(scene=scene)]
        backward=ob.rotation_euler.to_quaternion()@Vector((0,0,1))
        retreat=max(50.,(5.-min(v.z for v in frame))/max(backward.z,1e-4))
        ob.location+=backward*retreat;camera.clip_end=retreat+2000
        scene.render.filepath=str(out/f'{name}.png');bpy.ops.render.render(write_still=True)
    report['render_sha256']={name:hashlib.sha256((out/f'{name}.png').read_bytes()).hexdigest() for name in ('iso','front','top')}
    report['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    report['geometry_sha256']=hashlib.sha256((Path(__file__).parent/'geometry.py').read_bytes()).hexdigest()
    (out/'scene_telemetry.json').write_text(json.dumps(report,indent=2)+'\n')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'scene.blend'))

def height_at(r,a,p):
    from geometry import height
    return height(r,a,p['upturn'])

if __name__=='__main__':main()
