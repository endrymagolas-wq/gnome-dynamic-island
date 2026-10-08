# Third-party notices

- Linux design and behavior: `endrymagolas-wq/gnome-dynamic-island`, commit `5adf521`.
  GPL-3.0-or-later; full license in `LICENSE`.
- NAudio 2.2.1 by Mark Heath and contributors: MIT.
  https://github.com/naudio/NAudio/tree/v2.2.1 The complete copyright/license
  notice is retained in `NAudio-LICENSE.txt` and applies to the bundled NAudio
  component assemblies.
- Microsoft .NET / Windows Desktop runtime 10.0.12: distributed in `runtime/`
  with its LICENSE.txt and ThirdPartyNotices.txt. https://github.com/dotnet/runtime
  https://github.com/dotnet/wpf
- Microsoft.Windows.SDK.NET.Ref 10.0.19041.57 supplies
  `Microsoft.Windows.SDK.NET.dll`. The package declares the Windows SDK terms:
  https://aka.ms/WinSDKLicenseURL. The unmodified license is retained in
  `licenses/Microsoft-Windows-SDK-LICENSE.rtf`; its redistributable-code terms
  apply to this SDK projection. This dependency is not relabeled MIT or GPL.
- `WinRT.Runtime.dll` 2.2.0 comes from C#/WinRT, Copyright Microsoft Corporation,
  MIT. Its full notice is `licenses/CsWinRT-LICENSE.txt`, from release
  `2.2.0.241111.1`, revision `8649ee3eeb2445ca2a36d80d878ef60b96a6c65d`:
  https://github.com/microsoft/CsWinRT/tree/8649ee3eeb2445ca2a36d80d878ef60b96a6c65d.
  Microsoft distinguishes the SDK projection and C#/WinRT runtime terms here:
  https://github.com/microsoft/WindowsAppSDK/discussions/4368.
- UxPlay 1.74, FDH2 and contributors, GPL-3.0-or-later. Pinned Windows implementation:
  https://github.com/FDH2/UxPlay/tree/3dbf7ceee65932154e85a2f83963d53520a799fa
  Full upstream archive and all local native changes are in `receiver/source/`;
  `receiver/LICENSE-UxPlay` contains its license. The patch adds managed callbacks,
  local player controls, Windows UDP and reverse-HTTP fixes, metadata bounds and
  buffer handling. No user pairing keys, stored phone credentials or captured
  phone media are redistributed. Public upstream cryptographic self-test
  constants keep their original source/license; they are not user credentials.
- GStreamer 1.28.7 and its bundled plugins: primarily LGPL-2.1-or-later.
  https://gstreamer.freedesktop.org/ The exact shipped libraries, plugins and hashes
  are listed in `receiver/manifest.json`. Package-specific full license texts are
  in `receiver/share/licenses/`; those texts govern each dependency.
- FFmpeg 9.0.2 from MSYS2 UCRT64: this build enables GPL components and version 3,
  so the FFmpeg libraries are distributed under GPL-3.0-or-later.
  https://ffmpeg.org/legal.html
- GLib 2.90.1 / glib-networking 2.90.0 and GnuTLS 3.8.13 provide the GIO HTTPS backend;
  libsoup 3.8.0 provides HTTP, libplist 2.7.0 handles property lists, and OpenSSL
  3.6.5 supports UxPlay authentication. Licenses and additional dependencies are
  included in `receiver/share/licenses/`.
- Exact MSYS2 UCRT64 dependency sources and package recipes are supplied as
  `cortiva-airplay-native-corresponding-sources-0.4.0-beta.1.zip` alongside the
  binary downloads. See `licenses/CORRESPONDING-SOURCE.md` for the direct release
  link, exact source inventory, hashes and build directions. All 175 shipped
  native files map to 99 exact package versions; 96 unique source archives cover
  them. `receiver-build/toolchain-packages.txt` also records the original complete
  installed build environment. MSYS2 itself and the compiler executables are not
  installed with the application.
- The wallpaper/full packages include portable CPython 3.13.14 and psutil 7.2.2.
  Python retains its PSF license and bundled component notices in the Python
  runtime's `LICENSE.txt`: https://docs.python.org/3/license.html.
  psutil retains its BSD-3-Clause notice in its wheel's dist-info license files:
  https://github.com/giampaolo/psutil. They keep their own terms; the code's GPL
  does not relabel these dependencies.
- Lively Wallpaper is an external installed application, licensed GPL-3.0:
  https://github.com/rocksdanister/lively. Its executable is not bundled. The
  wallpaper package detects an existing installation; its install guide links
  the publisher's official release for users who need Lively. That external
  download retains Lively's own license. The bundled Lively community command
  utility 2.0.4.0 retains its GPL license and tagged upstream source/provenance.
- The V7 wallpaper and full package do redistribute the project-authored scene
  render, animations and water loop. Imported meshes, textures and rig components
  retain their own terms documented in `art/ASSET_SOURCES.md` (or the package's
  asset credits). Poly Haven/Yughues/Quaternius/Kenney components are CC0.
  Archived Snow rig sources are CC-BY-4.0, with attribution **Snow Rig © Blender
  Foundation / studio.blender.org**. The generated Pip mesh is not claimed as
  CC0: its Stable Fast 3D provenance and generator output terms are retained in
  `art/thirdparty/pip-sf3d/`. Powered by Stability AI. No model weights from Pip's
  generator are distributed.

The optional native media fixture generates its own silent PCM WAV and synthetic
metadata. No commercial music, browser credentials or user media are bundled.
