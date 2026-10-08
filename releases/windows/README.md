# Portable Windows release build

`build_release.py` uses an allowlist for each component and refuses to overwrite
an existing stage. It does not operate on the running Windows install or Lively.
The current release tag is `windows-v0.4.0-beta.1`.

```powershell
python releases/windows/fetch_dependencies.py --out ../dependencies
python releases/windows/build_release.py --source . --receiver ../reviewed-receiver --dependencies ../dependencies --out ../packages
```

Inputs must already pass the public-source privacy and dependency gates. Build
`windows/build.ps1` with debug symbols disabled and sanitized source paths before
staging. Do not copy a user's settings, Windows taskbar backups, app state,
pairing/PIN/key files, media captures, caches, `obj`, source `bin`, or PDBs.
The native receiver manifest is hash-checked before inclusion; its corresponding
source ZIP is retained along with the local patch and build recipe. All exact
MSYS2 dependency sources are provided as a separate corresponding-source asset.

Archives extract to one named root. The core uses `app/` + `runtime/`, standalone
AirPlay uses `receiver/`, and the full package adds `wallpaper/`, `assistant/`,
`python/` and the bundled `tools/lively-cli/`. Lively Wallpaper is external.
No hooks or firewall rules are installed without explicit launcher options.
Use `--stage-only` for read-only QA before ZIP compression. Run each launcher
with `-Diagnose` to inspect dependencies without starting or changing the desktop.

The editable Blender source is separate. It contains only the accepted organic
V7 scene and action source plus its V6 base; the earlier rejected row layout is
not an asset in any runtime package. `build_resort_v7.py` is retained only for
primitive helper functions consumed by the organic builder.
