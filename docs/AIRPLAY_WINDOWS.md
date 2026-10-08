# AirPlay on Windows

Cortiva Island receives phone music and supported direct YouTube video using a bundled, patched UxPlay/GStreamer runtime. Bonjour is not required; discovery uses the receiver's internal mDNS. This is an AirPlay receiver, not a Google Cast implementation.

## Standalone receiver

Extract `cortiva-airplay-windows-0.4.0-beta.1.zip`, then open:

```text
Cortiva-AirPlay-Windows/Start-AirPlay.cmd
```

The console displays the locally generated pairing PIN. Keep it open while receiving; close it to stop. The complete DLL/plugin set, notices, UxPlay source archive and local changes are included. Exact corresponding native-library sources are offered as a [separate release asset](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/cortiva-airplay-native-corresponding-sources-0.4.0-beta.1.zip); they are not duplicated in the runtime bundle. The standalone package does not require the island, .NET, Lively or Python.

## Integrated receiver

The full Windows desktop bundle includes the receiver. Start the bundle and enable it in **System → AirPlay**. Its PIN appears in the island. The request remains visible across the short protocol reconnects used during pairing.

The core island-only archive excludes the receiver. To add it, copy the standalone archive's complete `receiver/` folder into `IslandDesktop-Windows/receiver/`, then enable it from the island. This gives the island ownership of PIN and media controls. Keep the DLL/plugin/source subfolders together. Alternatively, use the full bundle or run the standalone package independently.

Do not run `Start-AirPlay.cmd` while the integrated receiver is enabled: only one receiver instance can own its ports. Standalone pairing data and console diagnostics use a separate local user-data location.

## Connect from iPhone or iPad

1. Connect phone and PC to the same local network. Guest/client isolation or blocked multicast can prevent discovery.
2. Start one receiver instance.
3. Choose **Cortiva Island** in the phone's output list and enter the displayed PIN when requested.

For **music**, choose it from the player's AirPlay audio output menu. For **YouTube**, use the video's cast button → **AirPlay / Bluetooth devices** → **Cortiva Island**. The supported direct-video path opens a separate video window on the PC.

Screen Mirroring is a different phone action and is not required for the tested YouTube player path. Protected/DRM video and other streaming applications are not guaranteed.

## Firewall

If Windows blocks reception, run `Enable-AirPlay-Firewall.ps1` at the extracted package root from an elevated PowerShell session. Use the full/standalone folder that owns the receiver:

```powershell
.\Enable-AirPlay-Firewall.ps1
```

It creates rules for that specific `receiver/bin/uxplay.exe`: TCP 7100–7102 and UDP 5353, 7100–7102, with the remote scope limited to **LocalSubnet**. It does not disable the firewall or alter general network profiles.

Moving the package changes the executable path; remove/recreate its rules if needed. Remove only its rules with:

```powershell
.\Enable-AirPlay-Firewall.ps1 -Remove
```

The launcher is at the extracted root in both full and standalone packages. For a receiver added to the core island, use its `airplay-firewall.ps1` beside `IslandDesktop.exe`. Administrator rights are for this firewall step, not ordinary playback.

## Controls and privacy

The integrated media panel displays artwork, track information and progress when the phone sends them. Music commands depend on DACP advertisement; video seeking depends on the stream providing a finite seekable range. Unsupported controls are disabled.

Integrated video options include aspect preservation/stretch, fullscreen via the panel or **Alt+Enter**, and a target buffer of **2 / 5 / 8 seconds**; default is five. This target does not guarantee end-to-end delay, which also depends on the phone, network and stream source.

Pairing keys and remembered devices stay in local user data; they are not included in the release. Technical diagnostics omit media URLs, authorization headers and cryptographic pairing proofs. Inspect logs before posting a public issue.

## Verified scope

A user with a real iPhone confirmed:

- Music is audible through the PC.
- Music remains audible after PIN pairing.
- YouTube video moves in the PC window and has sound.

Protocol checks, playback controls and independent readbacks are documented separately from those physical results. This does not certify every iOS version, player, DRM service, Screen Mirroring mode or network. See [release verification](RELEASE_VALIDATION.md).

Project code/UxPlay and runtime libraries retain their applicable licenses. The receiver source and local patch are included; see the package notices and [Windows notices](../windows/THIRD_PARTY_NOTICES.md).
