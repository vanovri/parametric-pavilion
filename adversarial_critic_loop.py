"""Accept only a real external review bound to the current GLBs and render hashes.

The builder/reviewer loop is orchestrated by the coding session, not a pretend
LLM call in this file. Rejected reviews stop publication and require a new pass.
"""
import argparse,hashlib,json
from pathlib import Path
from verify_model import verify

def gate(root,review_file):
    review=json.loads(review_file.read_text())
    score=review.get('subjective_score')
    if type(score) not in (float,int) or not 0<=score<=10:raise ValueError('missing valid subjective score')
    if review.get('approve') is not True or score<9:raise ValueError('independent visual review rejected')
    for name in ('pagoda','pavilion'):
        report=verify(root/'assets'/name)
        if review['inspected_glb_sha256'][name]!=report['glb_sha256']:raise ValueError('review refers to old GLB')
        hashes=review['inspected_render_sha256'][name]
        for view in ('iso','front','top'):
            digest=hashlib.sha256((root/'assets'/name/f'{view}.png').read_bytes()).hexdigest()
            if hashes[view]!=digest:raise ValueError('review refers to old render')
    return dict(visual_review='accepted',score=score,score_is_subjective=True,mechanical_gates='pass')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--review',type=Path,default=Path('docs/critic-review.json'))
    a=p.parse_args();print(json.dumps(gate(Path('.'),a.review),indent=2))
