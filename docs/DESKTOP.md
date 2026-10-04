# Full desktop profile

The optional profile reproduces this Ubuntu desktop appearance: the island and Ink shell controls, light WhiteSur GTK3/GTK4 application surfaces, right-hand traffic lights, matching icons, Inter, a floating bottom Ubuntu Dock, the light wallpaper and Layerlight music-responsive waves. It also installs dedicated Netflix/YouTube web-player launchers and Netflix phone-remote source.

Supported target: **Ubuntu 24.04 / GNOME Shell 46 / Wayland**. The default installer still installs only the island, shell theme, compatibility overlays and assistant helpers.

```sh
sudo apt install python3 python3-gi gir1.2-gtk-3.0 gnome-shell-extensions \
  gnome-shell-extension-ubuntu-dock pipewire-bin fontconfig qrencode
python3 install.py install --desktop --dry-run
python3 install.py install --desktop
```

Save work and log out/back in afterward. No logout, OS upgrade, GDM modification or forced app restart is performed. `--no-activate` copies files without changing settings or starting services. Every replaced file, including `~/.config/gtk-4.0/gtk.css`, is backed up; original appearance settings are recorded. Restore with `python3 install.py restore /absolute/path/to/manifest.json`. Later per-key appearance choices are retained.

The dock keeps existing pinned apps. No developer's app list, disk mounts, browser accounts, AirPlay password or private network configuration is copied. GTK4's explicit CSS import selects the light application theme; custom drawing, confined apps and incompatible libadwaita versions can differ. Chrome may require selecting **GTK** in its Appearance settings. Traffic-light overlays support only the explicit application profiles listed in README.

## Live wallpaper

Layerlight analyzes **system playback** through a PipeWire sink monitor, four audio bands and estimated music features. It never records the microphone or saves raw sound. Only numeric features are written to private runtime JSON. The optional Laya assistant can suggest a scene; waves also work with the assistant OFF.

The top-panel moon icon chooses automatic/calm/energetic motion and intensity. Switching waves off stops their owned audio-monitor process. Disabling the extension removes its effects and stops the monitor. The shader applies only to bundled `WhiteSur-light.jpg`. Physical multi-monitor/scaling and prolonged GPU-load checks remain beta work.

## Netflix and YouTube desktop players

Install Google Chrome or Chromium separately. Launch **Netflix · desktop player** / **YouTube · desktop player** from Applications, or:

```sh
export PATH="$HOME/.local/bin:$PATH"
island-media netflix
island-media youtube
```

These are dedicated browser app windows with separate local profiles. Fresh profiles select GTK window controls; existing profiles are retained. Sign into your own accounts normally. Netflix DRM depends on the browser, codecs, subscription and service. No commercial content or DRM bypass is bundled. YouTube is an ordinary web player, not a Google Cast receiver.

The phone remote needs **Node.js 22+** on PATH, `qrencode`, GTK3 and a compatible browser. It starts OFF on a fresh install:

```sh
island-media remote-on --lan
island-media pair
island-media remote-off
```

Without `--lan`, the remote binds only to loopback. With it, the server accepts loopback or private IPv4 peers in a subnet of a local interface; Host and Origin checks apply. A fresh 192-bit pairing key gets private permissions. Scan the local QR on the same Wi-Fi. For multiple interfaces, choose Wi-Fi/Ethernet with `python3 ~/.local/share/netflix-remote/show-pairing.py --address YOUR_LOCAL_ADDRESS`.

The remote controls playback, volume, seeking, fullscreen, profiles and episodes through the dedicated browser's loopback debugging endpoint. It accepts fixed actions and Netflix URLs, with authentication and failed-authentication rate limiting. Browser debugging is never bound to the LAN. Netflix DOM changes can break actions; portable tests do not certify authenticated playback on another user's account.

Pair only on a trusted LAN: local HTTP does not encrypt pairing sessions. No firewall/router rules change. If needed, allow TCP 8765 from your actual subnet. Key, QR, browser account data and later media settings remain local and survive restore. Restore stops the remote service; an open player remains open.

## Phone music, screen mirroring and YouTube AirPlay video

Audio uses **Shairport Sync**; screen/video uses **UxPlay**. Optional setup builds pinned UxPlay 1.73.7 with the local HLS buffering/pause and repeated-screensaver-state fixes. Native receiver executables are not redistributed. Install Ubuntu dependencies:

```sh
sudo apt install shairport-sync avahi-daemon build-essential git cmake pkg-config \
  libssl-dev libplist-dev libavahi-compat-libdnssd-dev libdbus-1-dev libx11-dev \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav gstreamer1.0-x
python3 setup_receivers.py --dry-run
python3 setup_receivers.py
```

Ubuntu's Shairport package may start a system receiver automatically. Check `systemctl status shairport-sync`. The installer refuses to compete with an active system receiver. To choose this package's session receiver instead:

```sh
sudo systemctl disable --now shairport-sync.service
python3 install.py install --desktop --receivers --dry-run
python3 install.py install --desktop --receivers
```

`--receivers` explicitly installs/enables three user units: `ytmusic-airplay.service`, `airplay-screen.service`, `ytmusic-airplay-auto-pause.service`. Previous files/states are recorded in the restore manifest. Configuration discovers interfaces, uses PulseAudio/PipeWire and session D-Bus/MPRIS, with track artwork. Auto-pause pauses phone music when a browser MPRIS player starts; disable that helper if you prefer simultaneous playback.

On the phone select **Ubuntu PC** in the **audio AirPlay menu** for music, or **Ubuntu Screen** in **Screen Mirroring**. UxPlay's `-hls 2` also enables supported direct YouTube iOS AirPlay video; service/app changes can affect it. Protected Netflix iOS video through mirroring cannot be promised; use the desktop Netflix player with its phone remote.

The phone and PC need the same LAN and multicast discovery. No firewall rules change. If blocked, allow mDNS UDP 5353, audio TCP 5000 / UDP 6001–6010 and screen TCP+UDP 7100–7102 **from your actual subnet**. Physical fresh-machine setup, phone video routing and suspend/resume remain beta checks.

## Asset provenance

`desktop/assets.zip` is a checksummed, deduplicated blob store mapped by `desktop/ASSETS.json`. The installer validates every blob/path before copying and uses local hard links for identical assets. It does not extract unchecked archive paths or download appearance assets during install.

- [WhiteSur GTK](https://github.com/vinceliuice/WhiteSur-gtk-theme), revision `d5782652d412137e26fb8ff55b55a5572e4c6995`, light/solid/blue plus local Chrome caption spacing. MIT; inherited GNOME notices retained.
- [WhiteSur icons](https://github.com/vinceliuice/WhiteSur-icon-theme), revision `73d8040da51a9ed74e47c7366e7e9ff437601a5c`, GPL-3.0 with authors.
- [WhiteSur wallpapers](https://github.com/vinceliuice/WhiteSur-wallpapers), revision `5c1d7ca20b8de0a7efe443792c19e49277262e02`, MIT, Copyright 2022 Vince.
- Original Inter Regular/Medium/SemiBold/Bold/Italic from Ubuntu fonts-inter, unmodified OFL-1.1 with notices.
- [UxPlay](https://github.com/FDH2/UxPlay), revision `df67c212a433cf6dda3676dd40c097900d24e645`, GPL-3.0; local changes in `receivers/uxplay.patch`.
- Netflix phone UI Tabler SVG icons retain their MIT notice in `desktop/netflix-remote/THIRD-PARTY-LICENSES.txt`.
