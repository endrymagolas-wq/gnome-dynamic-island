# Dynamic Island for GNOME

A floating **Dynamic Island for Linux and Ubuntu**, built as a native **GNOME Shell 46 extension**. Media controls through **MPRIS**, optional **AirPlay** integration, an **Ink** quick-settings theme, volume indicators and an optional offline **Laya system monitor**.

**First public beta: 0.1.0-beta.1.** Tested on Ubuntu 24.04.5 / GNOME 46 / Wayland. This is a separate desktop project. The interface currently uses Ukrainian labels.

## What it does

- A centered clock becomes a compact media island with rounded album art and animated playback indicators. Track controls wait 0.3 seconds before sending previous/next commands.
- The top bar reveals after a 300 ms ceiling hover above the island or empty desktop. Hover over another window's titlebar stays quiet; Shift at the top edge or continued pointer pressure explicitly reveals the bar. Window dragging and fullscreen suppress it.
- Horizontal phone-volume feedback below the island and a draggable vertical desktop-volume HUD. Native quick settings retain normal slider interactions, with an Ink palette and wide rounded tracks.
- Optional traffic-light overlays for the configured Codex/ChatGPT, Claude and Antigravity custom titlebars. This is an explicit compatibility list, not universal support for every application.
- Focus timer, per-application audio controls, manual resource diagnosis, notification history and category muting.
- Optional CPU-only Laya classification for observed downloads, long tasks, service failures, disk space, network changes and sustained CPU/RAM pressure. Fixed short messages, fullscreen/focus suppression and a maximum of three notices per five minutes.

The assistant recommends actions. It does not close applications, kill other processes, delete files or run commands chosen by a model. Its economic mode releases the owned model process after 60 seconds idle. Full OFF disables the assistant service and monitoring. Manual diagnosis and media controls remain available.

## Install

Check `gnome-shell --version` first. GNOME **46 only** is supported in this beta; do not disable GNOME's version validation. KDE, Hyprland and other shells are unsupported.

On Ubuntu 24.04, install the standard dependencies if absent:

```sh
sudo apt install git python3 python3-venv gnome-shell-extensions
```

Download the [release archive](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases) and extract it, or clone:

```sh
git clone https://github.com/endrymagolas-wq/gnome-dynamic-island.git
cd gnome-dynamic-island
python3 install.py install --dry-run
python3 install.py install
```

The installer copies files into your own home, enables the two bundled extensions and GNOME User Themes, and selects Island-Ink. It prints a recovery manifest before you log out. Save your work, then **log out and back in** to load the new JavaScript. It never logs you out automatically. Disable conflicting top-bar/autohide extensions such as Hide Top Bar before testing.

`--no-activate` copies files without changing desktop settings or services. The package does not install receivers, wallpapers, docks, GTK application themes or a Netflix phone remote. It does not modify application vendor files or upgrade Ubuntu. Existing receiver units are discovered; absent units are hidden.

## Optional offline assistant

The assistant starts **OFF on a fresh install**. Existing preferences are retained when reinstalling.

```sh
python3 setup_assistant.py
export PATH="$HOME/.local/bin:$PATH"
island-assistant on
island-assistant status
island-assistant off
```

Setup explicitly downloads CPU Python dependencies, a pinned [Laya multilingual checkpoint](https://huggingface.co/convaiinnovations/laya), and its tokenizer/configuration files. Internet is needed during setup; normal inference runs offline. The model weights alone are about 644 MB; allow several GB of disk space for Python dependencies and around 2 GB RAM for the loaded model. The lightweight collector uses substantially less memory when Laya sleeps. CPU and memory limits apply to the owned assistant service.

Python 3.10+ is required for model setup; Python 3.11 was used for the actual inference checks. `python3 setup_assistant.py --python /path/to/python3.11` selects another interpreter. The full tested runtime freeze is in `assistant/requirements.lock`; the installer pins the principal SDK/runtime versions. It is not a promise that every future dependency combination works.

Open the island, then its desktop controls, for assistant settings, category muting, diagnosis, history and application audio. `island-assistant diagnose` works with the assistant OFF. The actual service is `island-assistant.service`:

```sh
systemctl --user status island-assistant.service
journalctl --user -u island-assistant.service -n 30
```

## AirPlay and media players

Ordinary MPRIS players do not require the assistant or AirPlay. Receiver support is integration with separately installed software: [Shairport Sync](https://github.com/mikebrady/shairport-sync) for audio and [UxPlay](https://github.com/FDH2/UxPlay) for screen mirroring. Follow their upstream installation instructions. The phone and receiver must be on the same LAN.

This beta recognizes existing user units named `ytmusic-airplay.service` (audio) and `airplay-screen.service` (screen). Shairport needs its D-Bus/MPRIS metadata support for phone track data, artwork and volume. A phone audio receiver is selected in the phone's audio AirPlay menu; screen mirroring uses a separate receiver. No firewall rules or network configuration are changed by this installer.

## Restore / remove

Use the exact manifest path printed during installation:

```sh
python3 install.py restore /absolute/path/to/manifest.json
```

Original files are restored, newly installed package files removed, and unchanged desktop settings reverted. Modified source files cause restore to stop before overwriting them. Later assistant preference changes and personal history/model caches are preserved. Save work and log out/back in after restoring. To switch off quickly, disable `airplay-island@avalon.local` and `island-window-controls@avalon.local` in GNOME Extensions, then run `island-assistant off`.

If upgrading the earlier local prototype, the installer disables its old window-controls UUID to avoid duplicate overlays. Existing old prototype assistant files/services are not migrated automatically: switch the old assistant off before enabling this separate public version.

## Privacy and limits

Monitoring reads system metrics, same-user process names/PIDs/start times, coarse NetworkManager connectivity, the watched user services, and top-level download names/size/mtime to detect stable files. Download contents, screenshots, command lines, environment variables, keystrokes and browser histories are not collected. Some UI media artwork may be downloaded from the URL supplied by an MPRIS player. No analytics or cloud model API is included.

Status, preferences and the last 60 notices stay in `~/.local/share/island-desktop/assistant/` with private file permissions. Logs can contain local process or service names; inspect and redact them before filing a public issue. OFF stops the owned classifier and collector, not other applications or media receivers.

See [validation and known limitations](docs/VALIDATION.md). Physical sleep/resume/lock reliability and broad monitor, scaling and application compatibility remain open beta checks. Task disappearance does not prove successful completion. Per-process RSS may count shared pages more than once. Displayed advice is conservative and requires the user's own decision.

## Development

```sh
python3 tests/run.py
python3 -m compileall -q assistant install.py setup_assistant.py
find extensions -name '*.js' -exec node --check {} \;
```

Node is only needed for development tests. There are no npm runtime dependencies. Native rendering needs GNOME 46; portable tests do not stand in for compositor or physical-device verification.

Code is GPL-3.0-or-later; upstream theme notices are retained. See [third-party notices](THIRD_PARTY_NOTICES.md). This project is unofficial and is not affiliated with Apple, GNOME, Ubuntu or the Laya authors.
