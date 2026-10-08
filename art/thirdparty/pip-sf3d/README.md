# Pip V5 generated mesh

Input: `art/references/pip-v5-front.png`, generated from the project's accepted character reference with the built-in image generator. No paid third-party assets were purchased.

Original output: `pip-original.glb`, 1,203,196 bytes, 19,431 exported vertices / 25,108 triangles, one material with albedo and normal textures. Retrieved through the official [Stable Fast 3D Space](https://huggingface.co/spaces/stabilityai/stable-fast-3d) using an isolated Python environment. The service returned a real downloadable GLB. No local GPU inference was used.

Generator: [Stability AI Stable Fast 3D](https://github.com/Stability-AI/stable-fast-3d). The generator's [Community License](https://huggingface.co/stabilityai/stable-fast-3d/blob/main/LICENSE.md) is retained as `GENERATOR-LICENSE.md` for provenance. Its ownership-of-outputs clause applies to generated outputs; its definition of Derivative Works explicitly excludes model outputs. We do not redistribute generator weights or claim this mesh is Quaternius CC0. Powered by Stability AI.

Blender adaptation: rotate generated front toward -Y, scale 2.8, place soles at Z=0, weld duplicate geometry at UV boundaries while retaining corner UVs, clear split normals, remove a degenerate face and disable the noisy generated normal map. The original GLB is retained unchanged. The working file is `art/island/resort-v5.blend` with packed textures.

The 43-bone rig is copied from Quaternius BlueDemon (CC0; original files and license under `art/thirdparty/quaternius-pip`). The original rig is T-posed and does **not** match the generated mesh's A-pose. `art/island/rig_pip_v5.py` adapts joint positions before automatic skinning; upper head/ear vertices are assigned to Head to prevent arm motion pulling the ears. Existing source actions are retained; task gestures and foot timing are adapted in `pip_v5_poses.py`.

This is an image-reconstructed mesh, not production quad topology or a facial rig. V5 validation must check animation deformation and occlusion before promotion.

The final V5 source uses the second, higher-quality export `pip-hq-original.glb` (2,339,736 bytes): texture size 2048, remeshing Quad, target vertex count 20000, foreground ratio 0.85. Exported UV seams give 35,608 GLB vertices; after welding Blender has 19,980 vertices and 39,956 triangular faces. The Space's Quad option still exports triangulated faces; we do not claim this is a quad production rig. Both exports are preserved unchanged. The HQ mesh uses smooth normals without a subdivision modifier or the noisy normal map.

For a deterministic local rebuild, open the retained `art/island/resort-v4.blend`, execute `tools/build_pip_v5.py` through Blender MCP (set `__file__` to its absolute path), then render `tools/render_resort_v5.py` from the resulting V5 source. This reuses the saved generated output; online generation does not have to be repeated.
