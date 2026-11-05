$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$root = Resolve-Path (Join-Path $PSScriptRoot '..')
Set-Location $root
$version = (Get-Content VERSION -Raw).Trim()
$python = (Get-Command py -ErrorAction Stop).Source

Remove-Item -Recurse -Force build, dist -ErrorAction SilentlyContinue
& $python -3.12 -m venv .venv
$venvPython = Join-Path $root '.venv\Scripts\python.exe'
& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -e . pyinstaller==6.11.1
& $venvPython -m PyInstaller packaging/windows/windows-wallpaper.spec --noconfirm --clean
$exe = Join-Path $root 'dist\WindowsWallpaper\WindowsWallpaper.exe'
if (-not (Test-Path $exe)) { throw 'PyInstaller did not produce the expected executable' }
if (-not (Test-Path (Join-Path $root 'dist\WindowsWallpaper\_internal'))) { throw 'PyInstaller output is incomplete' }
Set-Content (Join-Path $root 'dist\version.txt') $version -Encoding utf8
$smoke = Start-Process -FilePath $exe -ArgumentList '--self-test' -Wait -PassThru -WindowStyle Hidden
if ($smoke.ExitCode -ne 0) { throw "Packaged executable self-test failed with exit code $($smoke.ExitCode)" }
Compress-Archive -Path (Join-Path $root 'dist\WindowsWallpaper') -DestinationPath (Join-Path $root "dist\windows-wallpaper-$version-win-x64-portable.zip") -Force
$iscc = Get-Command iscc.exe -ErrorAction Stop
& $iscc.Source "/Q" "/DAppVersion=$version" (Join-Path $root 'packaging\windows\installer.iss')
$checksumFile = Join-Path $root 'dist\SHA256SUMS.txt'
Get-ChildItem (Join-Path $root 'dist') -Recurse -File | Where-Object { $_.FullName -ne $checksumFile } | Get-FileHash -Algorithm SHA256 | ForEach-Object { "$($_.Hash)  $($_.Path.Substring($root.Path.Length + 1))" } | Set-Content $checksumFile
Write-Host "Built Windows Wallpaper $version"
