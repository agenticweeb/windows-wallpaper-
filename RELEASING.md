# Releasing

1. Update the version in `pyproject.toml`, `VERSION`, and `src/windows_wallpaper/__init__.py`.
2. Run `python -m pytest` and `python -m windows_wallpaper --self-test`.
3. Commit the release and create an annotated tag such as `v0.1.0`.
4. GitHub Actions builds on `windows-2022`, runs the self-test, creates a portable ZIP and a per-user Inno Setup installer, and publishes SHA-256 checksums.
5. Before a public release, test install, launch, wallpaper change, pause/resume, restart, upgrade, and uninstall on a clean Windows 10/11 x64 machine.

This repository does not contain a code-signing certificate. Release binaries are unsigned until a trusted Authenticode signing process is configured. Do not claim SmartScreen trust until signed artifacts have been verified.
