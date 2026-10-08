# Fairy Lagoon V7 for Windows

V7 is the larger organic island installed and tested in Lively on 8 October 2026. Three companions have their own scattered nooks, with open sand between them. The earlier chair/laptop row was an abandoned prototype.

Pip has a mint chair on the west side; the Codex companion has a violet chair beneath the eastern palm; the app companion uses the low cream nook on the front beach. There is one original work desk, a shared western daybed and a tea table on the front right.

## Install independently

1. Install Lively Wallpaper from its official Microsoft Store page.
2. Extract `fairy-lagoon-v7-wallpaper-windows.zip`.
3. Open `FairyLagoon-V7-Windows/Start-Wallpaper.cmd`.

The package includes Python 3.13.14, psutil 7.2.2 and Lively CLI 2.0.4.0; system Python and a first-launch CLI download are not required. Lively is external. Keep the package folder in place because its local host serves the assets to the wallpaper.

The full Windows bundle contains the same runtime wallpaper and starts it from `Start-Desktop.cmd`. The independent package does not need the top island/dock or an AirPlay receiver.

## Scene and controls

All three companions can sit, drink, lie belly-up, scratch their bellies, brew tea and return to their task positions. Shared furniture is reserved, and route/body clearance is checked against the actual scene. Tea reaches the mouth with a small head tilt. Eating and facial mouth/eyelid animation are not implemented.

The water uses seamless 12-second, 30fps pre-rendered loops. Morning, day, evening and night change by the PC clock, with a gradual transition. Choose automatic or fixed lighting, water on/off and available quality settings from Lively's wallpaper properties. The integrated island also exposes these controls when it detects the current primary wallpaper and saved properties.

Color/depth atlases provide the character animation and scene occlusion. There is no live Blender renderer. Pausing stops water and character motion; reduced-motion and visibility conditions are handled by the player/host. Physical lock and exclusive fullscreen behavior still require broader machine testing.

## What the characters observe

The host uses coarse local foreground/process activity and three separate channels: Claude, Codex and other apps. Optional Claude Code hooks can publish explicit starting/editing/testing/permission/done states; enabling those hooks is an explicit action, not a prerequisite:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Wallpaper.ps1 -InstallHooks
```

In the full bundle, use `start-desktop.ps1 -InstallHooks` instead.

Codex and other application activity is inferred where explicit hooks are absent. The companions do not read AI thoughts, prompts, tool output, source-file contents or keystrokes. No cloud model API is required for the wallpaper. Keep technical logs private until inspected.

## Stop and removal

Open `Restore-Wallpaper.cmd` to close this active entry, stop its owned host and restore the captured previous Lively layout. In the full bundle, `Stop-Desktop.cmd` does the corresponding cleanup for its components. Without a captured layout, the ordinary Windows wallpaper is restored. Neither action globally terminates Lively. You can also select another wallpaper from Lively. Disable any startup you enabled before deleting the extracted files.

## Editable source

The separate `fairy-lagoon-v7-blender-sources.zip` contains `FairyLagoon-V7-Blender` with:

- `resort-v7.blend`: final terrain, house and organic furniture layout.
- `resort-v7-actions.blend`: stand, sit, drink, lie, scratch, brew, recline and rise actions with props.
- Geometry/probe, bake, render and package scripts and asset notices.

The editable archive is not duplicated in the full runtime bundle. Open the supplied scenes in Blender to make changes; repeat the supplied bake/render pipeline to produce compatible runtime assets. See [asset provenance](../art/ASSET_SOURCES.md) and the archive's instructions before replacing third-party assets.

Public Blender files have had private authoring paths removed. Their semantic contents and packed textures were verified unchanged after reopening; byte hashes differ from the original render inputs recorded in asset metadata. The [integrity receipt](evidence/windows-release/blender-integrity.json) records the published source hashes.

## Verification boundary

The installed metadata passed terrain/contact, furniture, all-three-body and event-return gates. Native Lively WebView2 was observed decoding about 29.94fps at 1920×1080 in a short post-initialization measurement, with the three channels active. This is a measured run, not a frame-rate guarantee for every PC.

A clean browser preview uses the same assets but does not substitute for native desktop evidence. Source tests, native playback and manual device checks are listed in [release verification](RELEASE_VALIDATION.md).
