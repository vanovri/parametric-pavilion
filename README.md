# Parametric Pavilion

Two original architectural studies generated with Blender Python and shown as real GLB assets in Three.js: a five-tier pagoda and an open, single-tier pavilion. The forms are stylized studies, not replicas of a named historical building.

![Pagoda Cycles render](assets/pagoda/iso.png)

## Run the viewer

Node 22+ and Python 3.10+:

```sh
npm ci --ignore-scripts
npm run serve
```

Open http://127.0.0.1:8769. Select either study, orbit with a pointer, pinch/scroll to zoom, use arrow keys on the canvas, toggle wireframe, or reset the view. The static Blender render remains available if WebGL is unavailable. GLBs are downloadable without the viewer.

## Regenerate actual models

Verified locally with Blender 5.0.1 and Python 3.14 on Ubuntu 26.04 (WSL), including the Ubuntu `python3-numpy` package required by its glTF exporter:

```sh
blender -b -t 4 --python-exit-code 1 -P generate_pagoda_bpy.py -- params/pagoda.json assets/pagoda
blender -b -t 4 --python-exit-code 1 -P generate_pagoda_bpy.py -- params/pavilion.json assets/pavilion
python verify_model.py assets/pagoda
python verify_model.py assets/pavilion
python -m unittest discover -s tests -v
python adversarial_critic_loop.py
```

Each build exports a GLB, actual Cycles `iso.png`, `front.png`, `top.png`, a local `.blend` scene and evaluated-mesh telemetry. The `.blend` is excluded from Git because the generator is the reproducible source. Export failures stop the command. There is no metadata-only fallback.

The CI rebuild uses the official Blender 5.0.1 Linux runtime, pinned to SHA-256 `8019580ee1b7262e505f4196a00237ccf743c88d205b38d34201510676e60b09` from the [vendor checksum manifest](https://download.blender.org/release/Blender5.0/blender-5.0.1.sha256). Its bundled denoiser avoids the missing-OpenImageDenoiser failure in the runner's older distribution package.

## What is checked

- Parameters reject non-finite values, invalid ranges, unsupported modes and fractional tier counts.
- Roofs are closed two-sided meshes with consistently oriented faces, raised square corners and continuously varying hip slopes.
- Evaluated component meshes report open/nonmanifold edges, vertex counts and actual world-space bounds. An independent binary GLB reader welds split-normal positions and checks directed triangle-edge closure. Vertical intersections sample the local roof at column rims and along lintels. The verifier also checks support ranges, taper, GLB header/length/hash, embedded buffers, lantern emission and three actual render files.
- Regression tests remove an actual roof triangle, raise a lintel through the roof and lower a column away from its roof contact. These deliberately broken cases must be rejected. The first independent visual pass found framing and penetration defects despite the original broad-range checks; `docs/critic-review-01.json` preserves that rejection.
- Components intentionally overlap at structural joins. Closed individual components do not establish a single watertight building, collision-free interiors, structural safety, or printability.
- The independent visual review in `docs/critic-review.json` records actual observations and any revisions. A subjective score is a review opinion, not objective geometry proof. No canned scores or invented iteration history are displayed in the viewer.
- `adversarial_critic_loop.py` refuses a rejected review or one bound to different GLB/render hashes. The actual builder and independent subagent were orchestrated by the coding session. The script does not impersonate a vision model, generate its own score, or automatically approve parameter guesses.

## Provenance

Inspired by the user's procedural-modeling brief. All geometry, materials and example parameters were created for this repository with Codex assistance. No third-party model, Gemini invocation, autonomous visual-model API, or construction validation is claimed. Units are nominal metres, not a surveyed design. MIT project code; Three.js retains its own MIT license.
