"""Native executable entry point used by PyInstaller.

This file must import the package entry point rather than executing
windows_wallpaper/__main__.py as a standalone script. That preserves the
package context required by its relative imports.
"""

from windows_wallpaper.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
