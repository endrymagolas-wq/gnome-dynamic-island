# V6: fairy lagoon, seated Pip and local time

Work in progress. The ordinary desktop is still V5 until all four final lighting
bundles have been rendered, checked and promoted together. Preview:
`http://127.0.0.1:18765/wallpaper/fairy-review.html`.

## Art direction and layers

The camera and dry-land geometry are retained. Painted coral/mint/lavender
surfaces replace photographic base color and normal detail. Original leaf alpha
is retained. The submerged drop is shallower, with a height-based sand-to-lagoon
transition. Cycles renders actual periodic geometric waves, reflection,
refraction and shoreline foam. A restrained compositor glow is baked offline.

The static plate uses RGB from the full beauty frame, including its glow, and
alpha from the water holdout/shore mask. This avoids combining a differently lit
holdout RGB with the full water beauty. Ground/foreground depth, animated Pip
depth and cabana depth are separate data renders with neutral color transforms.

Each lighting preset has its own beauty/transparent plate, water videos,
character, ambient and smoke atlases. Geometry, projection and depth are shared.
Morning/day/evening/night start at 06:00/09:00/18:00/21:00 in the PC's local time.
The fade lasts two minutes. A second video decoder is used only during a fade;
the old source is unloaded afterwards. This is a fixed local-clock schedule,
not an astronomical sunrise calculation. A fixed phase can be selected in
Lively or the preview controls. Pausing stops both videos and actor animation;
lighting assets are not refreshed while paused.

## Furniture regression

V5 routed through the cafe furniture and applied a sitting pose at ground level.
Navigation now uses measured Blender bounds expanded by a 0.30m actor clearance.
The actor walks to a clear approach point, then uses a separate 0.9s sit/stand
transition. The rig origin on the cushion is 0.64m; cushion top is 0.95m. Walking
continues on the measured beach surface. New events during the transition are
retained and routed after standing. The larger actor's stride is 0.5952m/s.

The regression first failed with `walks inside coffee seating`; the corrected
model passes 81 state pairs and 18,100 walking samples outside measured furniture.
Per-pixel animated depth replaces the old upright actor plane. The source retains
the generated V5 mesh, Quaternius rig and original actions; no model is relabeled
CC0. Existing provenance remains in `art/ASSET_SOURCES.md`.

Idle no longer freezes its first frame. Three six-second clips (16fps) cycle
through drinking, nodding and a hand-cover yawn gesture. The mesh has no facial
rig, so these clips do not animate the jaw or eyelids. Eating is not implemented.
Task events interrupt the rest cycle via standing and normal navigation.

## Offline reproduction

Blender 4.5.9, Cycles OptiX on RTX 3080; Python/Pillow and FFmpeg for packaging.
No Blender process is launched by the wallpaper. The following are offline
commands, run from the repository. Use the actual local Blender executable.

1. Inspect/edit `art/island/resort-v6.blend`, or rebuild from retained V5 with
   `blender --background --python tools/build_resort_v6.py -- C:/scratch/resort-v6.blend`.
   The builder refuses to overwrite an existing destination.
2. Run the sequential renderer:
   `python tools/render_resort_v6_batch.py --blender <absolute Blender.exe>`.
   It stages outputs in ignored `wallpaper/assets/v6-stage/`, skips complete
   stages and records progress/logs. Defaults to the shipped V6 source. Use
   `--source C:/scratch/resort-v6.blend` for a fresh protected rebuild, with a
   fresh staging directory so completion reports from another source are not reused.
3. Record the three editable ambient rig actions if rebuilding source:
   `blender --background C:/scratch/resort-v6.blend --python tools/render_resort_v6.py -- ambient-actions day`.
4. Package only after all stages complete:
   `python tools/package_resort_v6.py`.
   The packer checks sprite bounds and fully decoded water seams for every phase.
   `--preview` stages only a draft day bundle and cannot promote it.
5. Run the scene/navigation/depth checks against staged assets. After review,
   `python tools/package_resort_v6.py --promote` backs up V5 outside Git and
   promotes the coherent layer set. Reload through `wallpaper/launch.ps1`.
6. Prepare the format comparison with `python tools/prepare_resort_atlas.py`.
   Stop owned Blender workers, then run `tools/run_resort_v6_native.ps1`.
   It checks the real hook transport/native player and properties, compares
   video/atlas/still, measures coffee/editing/two-decoder fade/native pause,
   and restores ordinary pause policy and observer. Synthetic hooks execute
   no paid Claude tasks or test commands.

The source lighting recipes are in `art/island/resort_time_of_day.py`; the
palette is in `fairy_palette.py`, poses in `pip_v6_poses.py`, and ambient gestures
in `bake_pip_ambient.py`. Source rig actions remain editable in Blender.

Fast checks: `node tests/resort-lighting.mjs`,
`node tests/resort-lighting-runtime.mjs`, and
`powershell -NoProfile -File tests/resort-properties.ps1`.
For staged navigation/depth tests set `RESORT_TEST_ASSETS` to
`wallpaper/assets/v6-stage`. The native run also captures each rest gesture and
requires advancing atlas cells. Work/rest benchmarks wait for the actual desk
or seated target before measuring.

`launch.ps1` migrates both the library schema and this wallpaper's saved
per-monitor Lively properties. Existing water, quality and fixed-time values
are retained. Other wallpapers' properties are not touched.

Environment shadows/reflections are baked. The moving actor uses animated
per-pixel depth and a small contact shadow; arbitrary-position cast shadows and
reflections of the moving actor are not rendered at runtime.

Performance results will be added after the final native run. Physical lock,
exclusive fullscreen and multiple monitors remain manual checks; callback and
observer tests must not be described as physical lock/fullscreen proof.
