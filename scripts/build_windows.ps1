$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

python -m pip install --upgrade pip
python -m pip install -e '.[dev]' pyinstaller
python -m pytest -q
python -m windows_wallpaper --self-test

if (Test-Path dist) { Remove-Item dist -Recurse -Force }
python -m PyInstaller --noconfirm --clean packaging/windows/windows-wallpaper.spec

$version = (Get-Content VERSION -Raw).Trim()
$inno = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe'
if (-not (Test-Path $inno)) { throw "Inno Setup compiler not found at $inno" }
& $inno "/DAppVersion=$version" 'packaging/windows/installer.iss'

Compress-Archive -Path 'dist/WindowsWallpaper/*' -DestinationPath "dist/windows-wallpaper-$version-win-x64-portable.zip" -Force
Get-FileHash 'dist/installer/*.exe', 'dist/*.zip' -Algorithm SHA256 |
  ForEach-Object { "$($_.Hash)  $($_.Path | Split-Path -Leaf)" } |
  Set-Content 'dist/SHA256SUMS.txt'

Write-Host "Built Windows Wallpaper $version artifacts in dist/"
