# Windows installation

This x64 beta was exercised on Windows 11 Pro, build 26200. The archives are portable folders: extract before launching and keep each folder's contents together. No .NET SDK, Blender, GStreamer installation or Bonjour service is needed to run the packaged components.

## Choose a package

| Archive | Extracted folder | Included runtime | External dependency |
| --- | --- | --- | --- |
| `island-desktop-windows-full-0.4.0-beta.1.zip` | `IslandDesktop-Windows-Full` | Island, AirPlay receiver, V7, .NET and Python | Lively Wallpaper for V7 |
| `island-desktop-windows-0.4.0-beta.1.zip` | `IslandDesktop-Windows` | Island, top bar, dock, media and .NET | None for core UI; receiver and wallpaper are separate |
| `cortiva-airplay-windows-0.4.0-beta.1.zip` | `Cortiva-AirPlay-Windows` | UxPlay, GStreamer, required DLLs, source and notices | Same LAN as the phone |
| `fairy-lagoon-v7-wallpaper-windows.zip` | `FairyLagoon-V7-Windows` | V7 assets, local host, Python and psutil | Lively Wallpaper |
| `fairy-lagoon-v7-blender-sources.zip` | `FairyLagoon-V7-Blender` | Editable scene/actions and production scripts | Blender for editing/rendering |

Download from the [release](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/tag/windows-v0.4.0-beta.1). Third-party applications shown in the dock are not included.

## Full desktop

1. Install Lively Wallpaper from its official Microsoft Store page.
2. Extract the full archive to a folder you intend to keep.
3. Open `Start-Desktop.cmd`. It uses paths relative to the extracted folder.
4. Use **System → AirPlay** in the island to enable the receiver when needed. See [phone setup](AIRPLAY_WINDOWS.md).

The full bundle includes the components, not a copy of Lively. Lively's command utility 2.0.4.0 is bundled under `tools/lively-cli/`; the launcher does not download it on first use. Startup is not enabled until you choose it. Optional Claude Code hooks require a separate explicit action.

All launchers are at the extracted root. The full bundle has `app/`, `runtime/`, `receiver/`, `wallpaper/`, `assistant/`, `python/` and `tools/lively-cli/`; retain these together.

## Island only

Open `IslandDesktop.exe` in `IslandDesktop-Windows`. The included .NET runtime is used automatically. Keep `app/` and `runtime/` beside the launcher. A second launch does not create a second island.

The core archive contains the top panel, dock, media and desktop controls. It does not contain the AirPlay receiver or wallpaper. To add integrated AirPlay, copy the complete `receiver/` folder from the standalone AirPlay archive into `IslandDesktop-Windows/receiver/`, then enable the receiver in the island. Do not run the standalone receiver at the same time. See the [AirPlay](AIRPLAY_WINDOWS.md) and [wallpaper](WALLPAPER_V7.md) guides.

## Everyday use

- Hover at the upper edge, away from the corners, to open the top bar. Click the capsule for the media panel; use its wheel to change volume.
- Click a dock icon to launch, focus or minimize an application. Right-click for its windows. Pins use applications present on your PC.
- The top arrow opens Explorer's hidden/background notification icons.
- Media buttons reflect the selected player's Windows SMTC support. Unsupported actions are disabled.
- The focus timer reports its end time; Windows Do Not Disturb remains a separate setting.

The dock hides the native taskbar while it is active. Closing the island restores the preceding taskbar configuration. Its launcher also restores it after the island process crashes. Notification Center opens on an explicit click and temporarily reveals the taskbar.

## Stop or remove

- Full bundle: open `Stop-Desktop.cmd`. It closes the island from that package, its owned wallpaper host and its active Lively entry. It restores the captured preceding Lively layout when present; otherwise, it returns to the ordinary Windows wallpaper. It does not kill Lively globally.
- Island-only: run `stop.ps1` or close the island from its menu.
- Standalone AirPlay: close its receiver console.
- Wallpaper: use `Restore-Wallpaper.cmd` to close its active entry, stop its owned host and restore the captured previous layout. You can also select another wallpaper in Lively.

Disable any startup entry you enabled, close the components, then remove the extracted folder. Settings and pairing data may be retained under the local user-data folders. Removal does not require resetting Windows or other applications.

## Optional Claude Code hooks

Install explicit task hooks only when you want them:

```powershell
# Independent wallpaper
powershell -NoProfile -ExecutionPolicy Bypass -File .\Start-Wallpaper.ps1 -InstallHooks

# Full bundle
powershell -NoProfile -ExecutionPolicy Bypass -File .\start-desktop.ps1 -InstallHooks
```

The hooks preserve the separate process/focus activity display and add bounded Claude task states.

## Limits

Windows 10, ARM64, physical suspend/resume/lock, exclusive fullscreen and all multi-monitor/DPI combinations have not received complete native validation. The wallpaper controls currently target the primary wallpaper entry. Browsers/sites decide which media metadata and actions they publish. DRM and subscription access remain with the service/browser.

The beta does not apply GNOME/GTK themes to arbitrary Windows programs or include Linux Laya and the Netflix phone remote. It does not globally disable every Windows or third-party popup. [Verification scopes](RELEASE_VALIDATION.md).
