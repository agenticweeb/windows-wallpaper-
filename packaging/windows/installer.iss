#define AppName "Windows Wallpaper"
#define AppPublisher "Windows Wallpaper contributors"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define AppExeName "WindowsWallpaper.exe"

[Setup]
AppId={{B1A3B91D-28E2-4CE0-BF73-2F2C6D2B1E9C}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\WindowsWallpaper
DefaultGroupName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=lowest
OutputDir=..\..\dist\installer
OutputBaseFilename=windows-wallpaper-{#AppVersion}-win-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
; The application owns its close behavior (close hides the window), so the
; installer performs a graceful --quit and targeted fallback in PrepareToInstall.
CloseApplications=no
RestartApplications=no

[Files]
Source: "..\..\dist\WindowsWallpaper\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  ResultCode: Integer;
  ExistingExe: String;
begin
  Result := '';
  NeedsRestart := False;
  ExistingExe := ExpandConstant('{app}\{#AppExeName}');
  if not FileExists(ExistingExe) then
    exit;

  { Ask the running app to close through its authenticated local command path. }
  Exec(ExistingExe, '--quit', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);

  { Older builds or a crashed UI may not answer. Only target our exact process. }
  Exec(ExpandConstant('{sys}\taskkill.exe'), '/F /T /IM {#AppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);
end;
