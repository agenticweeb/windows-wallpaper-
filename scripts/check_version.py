from __future__ import annotations

import re
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
version = (root / "VERSION").read_text(encoding="utf-8").strip()
pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
package = (root / "src/windows_wallpaper/__init__.py").read_text(encoding="utf-8")
py_version = re.search(r'version\s*=\s*"([^"]+)"', pyproject).group(1)
package_version = re.search(r'__version__\s*=\s*"([^"]+)"', package).group(1)
expected_tag = f"v{version}"
actual_tag = sys.argv[1] if len(sys.argv) > 1 else expected_tag
if actual_tag != expected_tag or py_version != version or package_version != version:
    raise SystemExit(f"Version mismatch: tag={actual_tag}, VERSION={version}, pyproject={py_version}, package={package_version}")
print(version)
