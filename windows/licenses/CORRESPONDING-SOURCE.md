# Exact Windows native corresponding source

This release's receiver is UxPlay 1.74 at revision
`3dbf7ceee65932154e85a2f83963d53520a799fa`. The receiver package includes the
complete upstream archive and all local native changes in `receiver/source/`.
The public tag includes the Windows managed application, receiver build scripts,
native patch, package lock file and runtime packager:

- [Windows source at the exact release tag](https://github.com/endrymagolas-wq/gnome-dynamic-island/tree/windows-v0.4.0-beta.1/windows)
- [Complete exact native dependency source archive](https://github.com/endrymagolas-wq/gnome-dynamic-island/releases/download/windows-v0.4.0-beta.1/cortiva-airplay-native-corresponding-sources-0.4.0-beta.1.zip)

The native dependency source ZIP contains the official versioned MSYS2 source
archives for every installed package that owns a shipped native binary. Shared
source archives are included once. `native-package-source-inventory.json` maps
all 175 shipped native files to their 99 exact package versions, source URLs,
upstream licenses and build provenance. `source-download-manifest.json` records
the downloaded archives' measured SHA-256 and sizes. Downloading the source ZIP
does not install or run software.

MSYS2 `.src.tar.zst` source archives contain the corresponding package's
`PKGBUILD`, local patches and source inputs. Extract them with an archive tool
that supports Zstandard, and follow each recipe in an MSYS2 UCRT64 build
environment. For the locally modified receiver, follow
`receiver-build/README.md` and `receiver-build/build.sh`. The documented receiver
build disables `-march=native`, enables internal mDNS and uses the pinned native
patch. The exact existing binary library hashes are in `receiver/manifest.json`.
Changing toolchain/packages can produce different hashes.

The sources are provided beside the Windows binary downloads without charge.
The same official package-version archives are also linked individually in the
inventory. This release preserves applicable copyright notices and full GNU
license texts in `receiver/share/licenses/`. Independent compiler reproduction
is separate from the recorded source download/hash and dependency closure checks.

The Windows .NET/runtime, SDK projection, CsWinRT and NAudio notices are described
in `THIRD_PARTY_NOTICES.md`. They keep their own terms.
