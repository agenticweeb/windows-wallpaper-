# Windows Wallpaper product rebuild

## Direction
Build a lightweight, Windows-native static wallpaper manager that combines the strongest ideas from Variety, Lively, Superpaper, Rainmeter, and Waypaper without importing their platform-heavy dependencies. Keep Python, Pillow, SQLite, requests, and Tkinter as the core stack; make pystray optional.

## Product shape
The UI is organized into five surfaces:

- **Now Playing**: current wallpaper preview, source/attribution, next/previous/favorite/pause controls, and rotation status.
- **Library**: folders, downloaded images, filters, thumbnails, favorites, and history.
- **Sources**: explicit Bing, Wallhaven, Reddit, and local source actions with progress/errors.
- **Quotes**: automatic quote providers, custom local quotes, live overlay preview, typography and positioning.
- **Settings**: interval, startup/background behavior, cache, privacy, and diagnostics.

## Architecture
`WallpaperApp` remains the coordinator. Add clear service boundaries for paths, Windows wallpaper target, source/download normalization, rendering, scheduling, and persistence. UI actions call app methods instead of mutating internal state directly. All network and image work remains off the Tkinter thread. Originals are immutable; effects and overlays render to cache copies.

## Scope for this release
Repair the package and install metadata; provide a polished dark desktop UI; add preview/history/source metadata; make quote fetching and rendering reliable offline-first; add basic effects and cache cleanup; preserve existing CLI/IPC behavior; validate with tests and focused review agents; publish a Windows release.

## Deferred
Video/executable wallpapers, browser runtimes, cloud sync, arbitrary plugin execution, and independent per-monitor rotation are deferred until the static-wallpaper product is stable. Multi-monitor capability should be detected and reported rather than falsely promised.
