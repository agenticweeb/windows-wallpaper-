# Windows Wallpaper

A lightweight Windows wallpaper manager inspired by the workflow and spirit of Variety. It rotates wallpapers from local folders, keeps history and favorites, supports pause/resume and manual navigation, and can download wallpapers from several online sources with optional quote overlays.

## Status

This repository is the first Windows-native release line. The application is designed to remain small and dependable: local rotation works offline, remote providers are isolated from the rotation loop, and the catalog is stored in a transactional SQLite database.

## Features

- Recursive local-folder sources.
- Timed rotation with pause/resume, next, previous, and fast manual selection.
- Favorites copied into a dedicated user folder.
- Persistent history and current wallpaper across restarts.
- Basic filters: minimum dimensions, landscape preference, and filename pattern.
- Atomic downloads with image-content validation.
- Online wallpaper sources: Bing Photo of the Day, Wallhaven search, and Reddit image communities.
- Anime-ready presets: search Wallhaven for `anime` or enter a different query, and use communities such as `Animewallpaper` on Reddit.
- Quote overlays rendered onto a cache copy, with Quotable, ZenQuotes, Goodreads-imported quotes, funny quotes, built-in fallback quotes, and editable local files.
- Quote Studio uses arrow-key spinboxes for live font size, panel opacity, text width, and horizontal/vertical placement preview.
- Independent quote rotation: select multiple providers, choose the seconds per quote, fetch the next quote, and apply the active quote directly to the desktop.
- Windows 10/11 wallpaper setting through the native Unicode Windows API.
- Per-user configuration and data directories; no administrator permission required for normal use.
- Portable mode with `--portable` or a `portable.flag` beside the executable.
- No telemetry and no analytics.

## Development

```powershell
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
python -m pip install -e .[dev]
python -m pytest
python -m windows_wallpaper --self-test
```

The development entry point also works on non-Windows systems for catalog and configuration tests, but actually changing the desktop requires Windows.

## Running

```powershell
windows-wallpaper
windows-wallpaper --add-folder "C:\Users\me\Pictures\Wallpapers"
windows-wallpaper --next
windows-wallpaper --previous
windows-wallpaper --pause
windows-wallpaper --resume
windows-wallpaper --version
```

The first launch opens the settings window. Add one or more folders, choose an interval, uncheck **Pause rotation**, and press **Next** once to verify Windows integration. Closing the window hides it while rotation continues; launching Windows Wallpaper again restores the existing window. The CLI controls `--next`, `--previous`, `--pause`, and `--resume` are sent to that same running instance. Use the **Quit** button to exit completely. User data is stored under `%LOCALAPPDATA%\WindowsWallpaper` when installed. Portable mode stores data under `data` beside the executable.

In **Quote Studio**, select one or more providers and set **Rotation time**. Quotable and ZenQuotes use their public endpoints. Goodreads does not provide a supported public quotes API, so the Goodreads option reads an import file at `%LOCALAPPDATA%\WindowsWallpaper\config\quotes_goodreads.txt`; use one quote per line as `quote | author`. The **Funny quotes** and **Built-in fallback** options work offline. Enable the overlay, use the arrow buttons to position and size it while watching the preview, then choose **Apply to desktop now**. Once enabled, the quote worker re-renders the current wallpaper at the selected quote interval even when wallpaper rotation is paused.

## Building the Windows release

Windows binaries are built on a Windows GitHub Actions runner; PyInstaller is not a cross-compiler. The release workflow produces a portable ZIP and a per-user Inno Setup installer from the same `onedir` build. Create a tag matching the version in `pyproject.toml`, such as `v0.3.2`, to start a release build.

Upgrades stop the running app through `--quit` before replacing files. If an older or unresponsive process does not respond, the installer targets only `WindowsWallpaper.exe` as a fallback.

Unsigned artifacts are suitable for testing. Production signing requires an Authenticode certificate and is intentionally not configured in this public repository.

## Privacy and safety

The app does not collect telemetry. Network access is used only when the user explicitly starts an online source or quote fetch. Downloads accept HTTP(S) only, follow a bounded number of redirects, validate the decoded image, use atomic writes, and never execute downloaded content. Original wallpaper files are not modified; quote text is rendered into a separate cache copy before Windows displays it.

## License

This project is licensed under the GNU General Public License v3.0 only. See [LICENSE](LICENSE).
