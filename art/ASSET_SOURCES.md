# Resort assets, provenance and credits

The editable `art/island/resort-v2.blend` packs the images and meshes used by
the current resort. Originals downloaded on 2026-10-05 remain in the local
`../asset-downloads/resort-v2/` cache. No paid asset was purchased.

| Asset used | Primary source | License / credit | Adaptation |
| --- | --- | --- | --- |
| Snow v2 character, CloudRig, skin and cloth | [Blender Studio Snow v2](https://studio.blender.org/characters/snow/v2/) | CC-BY-4.0; **Snow Rig © Blender Foundation / studio.blender.org** | Cream shirt, teal trousers, brown shortened crown hair, reduced texture sizes; original weights and controls retained; authored task poses |
| Feathered palms and UV maps | [Free Palm TreeZ v3, Yughues / Nobiax](https://opengameart.org/content/free-palm-treez-v3) | CC0 1.0; optional credit Yughues / Nobiax | Scale, placement and foliage grading; alpha and normal maps retained |
| Boulder 01 | [Poly Haven Boulder 01](https://polyhaven.com/a/boulder_01) | CC0 1.0; optional credit Rico Cilliers / Poly Haven | Six instances with warm limestone grading |
| Outdoor table | [Poly Haven Wooden Table 02](https://polyhaven.com/a/wooden_table_02) | CC0 1.0; optional credit Poly Haven | Resized for the laptop working height |
| Coastal sand | [Poly Haven Coast Sand 01](https://polyhaven.com/a/coast_sand_01) | CC0 1.0 | Albedo graded toward pale tropical sand |
| Stucco | [Poly Haven White Stucco](https://polyhaven.com/a/white_stucco) | CC0 1.0 | Cottage walls and porch |
| Deck wood | [Poly Haven Wood Floor Deck](https://polyhaven.com/a/wood_floor_deck) | CC0 1.0 | Decking and bench |

[Poly Haven's asset license](https://polyhaven.com/license) covers asset files.
Its website previews have a different license and are not used in the wallpaper.
The source caches retain original readmes where supplied. Snow attribution is
retained for the archived V3 source and in `wallpaper/LivelyInfo.json`.

The cottage, terrace details, beach mesh, water geometry/material, foam and
render/runtime tooling are project work. Imported asset licenses remain
applicable to those components; the code's GPL does not relabel Snow.

## Generated references

`references/resort-v2-nanobanana.jpg` and `references/character-v2-turnaround.jpg`
were generated in Google Flow with **Nano Banana 2**, using the user's existing
account on 2026-10-05. They guide composition, palette and character adaptation.
They are not claimed as CC0 models. The turnaround supplies no mesh or rig:
the V3 worker used the credited Snow mesh and rig above. The island image
is not used as a distorted water background. Flow's two sand generations failed;
the actual sand shader uses the licensed PBR scan.

## Current V5 mascot: Pip

V5 uses a new image-reconstructed mesh from the accepted cute fantasy creature
reference, with a large rounded head, floppy ears and hibiscus swim shorts.
The GPT-generated front reference is `references/pip-v5-front.png`.
Antigravity obtained actual GLB outputs through the official free
[Stable Fast 3D Space](https://huggingface.co/spaces/stabilityai/stable-fast-3d),
without paid API credits or local GPU inference. Original outputs and generator
license are retained in `thirdparty/pip-sf3d/`; see its README for parameters,
ownership-of-outputs terms and precise provenance. Powered by Stability AI.
The generated mesh is not relabeled as Quaternius CC0.

Blender MCP was used to inspect/import the mesh, clean its geometry/normals,
adapt the existing 43-bone rig, bind skin weights, render closeups and save
editable task actions. Original T-pose bones do not automatically match the
generated A-pose: `island/rig_pip_v5.py` records the explicit joint adaptation.
The 2048px HQ output is used in the current V5 source. Its surface is triangulated,
and it has no facial rig; limb/gesture animation is baked offline.

## Archived V4 mascot and reused Quaternius rig

Pip is adapted from **BlueDemon**, Quaternius' [Ultimate Monsters](https://quaternius.com/packs/ultimatemonsters.html),
released October 2022, licensed **CC0 1.0**. The official page links to the
[author's public asset folder](https://drive.google.com/drive/folders/18m4KpzpEzhC9wl7jzr6dUc0N8Jozr79C).
The downloaded originals are shipped in `thirdparty/quaternius-pip/`:
`BlueDemon.blend`, `Atlas_Monsters.png`, and `License.txt`. Credit is appreciated
but not required by CC0. The publisher's License.txt has an older “Ultimate
Platformer Pack” heading; its CC0 dedication agrees with this pack's official
CC0 badge. No paid source kit was purchased.

Verified directly in Blender 4.5: **43 bones**, weighted arms/fingers, two leg IK
constraints and **14 original actions**, including Walk, Wave, Idle, Yes and No.
There are no separate ear or facial-control bones. Ten task actions are saved
separately. Pip retains the original weighted mesh and skeleton; customization
removes the bat and loincloth, rounds the silhouette, folds the ear tips,
shortens the existing arm bones, adds friendly eyes/smile/nose/freckles, paints
yellow swim shorts and brightens the skin. Walk and breathing reuse authored
motions. Typing, inspection, coffee and permission gestures adapt the same rig.

`references/pip-v4-turnaround.png` was generated using Codex's built-in image
generator on 2026-10-05 under the user's authorization. It is a design reference,
not a downloaded CC0 asset or an automatically generated 3D mesh. The adapted
mesh has its own stylization; it is not claimed to reproduce every detail of the
reference. No generated photograph is used as animated water.

The earlier Snow and rejected prototype sources remain available in their
original `.blend` files. `resort-v4.blend` contains only the current four scenes
and packs the used model images. Antigravity located models and downloaded the
author's palette/license; actual rig and render validation was done through MCP.

## Earlier rejected prototype

The preserved `resort.blend` and `art/thirdparty/` contain the earlier CC0
[Kenney Nature Kit](https://kenney.nl/assets/nature-kit) and
[Animated Characters Protagonists](https://kenney.nl/assets/animated-characters-protagonists).
Their `License.txt` files are retained. That worker and those palms are
superseded in the current wallpaper; old review images are not validation of
the new scene. Nobiax palm v2 and Coast Rocks were evaluated and replaced.
