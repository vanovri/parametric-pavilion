import copy,json,math,tempfile,unittest
from collections import Counter
from pathlib import Path
from geometry import validate,roof_mesh,tiers,height
from verify_model import verify
from glb_geometry import triangle_models,validate_topology,validate_supports

class GeometryTests(unittest.TestCase):
    def test_closed_consistent_roof(self):
        for upturn in (.1,.48,.7):
            vertices,faces=roof_mesh(10,upturn);edges=Counter()
            for f in faces:
                for a,b in zip(f,f[1:]+f[:1]):edges[a,b]+=1
            self.assertTrue(all(v==edges[b,a]==1 for (a,b),v in edges.items()))
            self.assertTrue(all(math.isfinite(v) for xyz in vertices for v in xyz))
            self.assertEqual(len(vertices)-len(edges)//2+len(faces),2)
    def test_raised_corners_and_taper(self):
        self.assertGreater(height(1,math.pi/4,.48),height(.8,math.pi/4,.48))
        rows=tiers({});self.assertEqual(len(rows),5)
        for a,b in zip(rows,rows[1:]):self.assertAlmostEqual(b['width']/a['width'],.82)
    def test_invalid_params(self):
        for p in ({'tiers':True},{'tiers':7},{'base_width':float('nan')},{'mode':'pavilion','tiers':2},{'mode':'other'}):
            with self.assertRaises(ValueError):validate(p)
    def test_render_and_glb_evidence(self):
        for model in ('pagoda','pavilion'):
            self.assertEqual(verify(Path('assets')/model)['mechanical_gates'],'pass')
    def test_tampered_export_rejected(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);shutil.copytree('assets/pavilion',root,dirs_exist_ok=True)
            (root/'model.glb').write_bytes((root/'model.glb').read_bytes()+b'x')
            with self.assertRaises(ValueError):verify(root)
    def test_actual_glb_open_component_rejected(self):
        models=triangle_models(Path('assets/pavilion/model.glb').read_bytes())
        models['Tier 1 roof'].pop()
        with self.assertRaisesRegex(ValueError,'open or inconsistently'):validate_topology(models)
    def test_local_lintel_intrusion_rejected(self):
        models=triangle_models(Path('assets/pavilion/model.glb').read_bytes())
        name='Tier 1 lintelX -1'
        models[name]=[tuple((x,y+.3,z) for x,y,z in t) for t in models[name]]
        with self.assertRaisesRegex(ValueError,'lintel penetrates roof'):validate_supports(models,1)
    def test_floating_column_rejected(self):
        models=triangle_models(Path('assets/pavilion/model.glb').read_bytes())
        name='Tier 1 column -1 -1'
        models[name]=[tuple((x,y-.3,z) for x,y,z in t) for t in models[name]]
        with self.assertRaisesRegex(ValueError,'contact violation'):validate_supports(models,1)

if __name__=='__main__':unittest.main()
