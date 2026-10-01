; Buttcrack -- Windows installer (Inno Setup 6)
;
; Turns dist\Buttcrack\ (built by buttcrack.spec) into a single
; buttcrack-setup-<version>.exe that a person can download from any web server
; and double-click.  No Python, no git, no package manager, no GitHub account.
;
; Build it with packaging\windows\build.ps1, or on its own:
;
;     iscc packaging\windows\buttcrack.iss
;     iscc /DAppVersion=1.1.0 packaging\windows\buttcrack.iss   ; if ISPP cannot read the exe
;
; Design notes that are easy to get wrong and annoying to discover later:
;
; * PrivilegesRequired=lowest.  This installs per-user into %LOCALAPPDATA%, so
;   there is no UAC prompt at all.  For a free tool someone found on a web page
;   that is the difference between "installed" and "closed the tab".  Anyone who
;   wants it machine-wide can still choose that in the first dialog.
; * No file associations and no autostart.  A cipher solver has no business
;   claiming extensions or running at boot.
; * The PATH entry is opt-in and per-user, written to HKCU\Environment.

#define AppName       "Buttcrack"
#define AppPublisher  "ahardkore"
#define AppExeName    "Buttcrack.exe"
#define CliExeName    "buttcrack.exe"
#define AppUrl        "https://ahardkore.github.io/Buttcrack---Cipher-Breaker/"
#define SourceDir     "..\..\dist\Buttcrack"

; One source of truth for the version: the VERSIONINFO resource that
; buttcrack.spec stamped into the exe, which it took from buttcrack/__init__.py.
; Override with /DAppVersion=... if you are packaging a build you did not make.
#ifndef AppVersion
  #define AppVersion GetStringFileInfo(SourceDir + "\" + AppExeName, "FileVersion")
  #if AppVersion == ""
    #error Could not read the version from the built exe. Build it first (packaging\windows\build.ps1), or pass /DAppVersion=x.y.z
  #endif
#endif

[Setup]
; Never change AppId: it is what makes the next installer an upgrade of this
; one instead of a second copy in Add/Remove Programs.
AppId={{4D7F05D7-7C77-50B8-B538-219DED0C01B5}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppUrl}
AppSupportURL={#AppUrl}
AppUpdatesURL={#AppUrl}
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppName} setup

DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
DisableDirPage=auto
LicenseFile=..\..\LICENSE

PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0

OutputDir=..\..\dist\installer
OutputBaseFilename=buttcrack-setup-{#AppVersion}
SetupIconFile=assets\buttcrack.ico
WizardStyle=modern
WizardSmallImageFile=assets\wizard-small.bmp
WizardImageFile=assets\wizard-large.bmp
Compression=lzma2/max
SolidCompression=yes
LZMANumBlockThreads=4

UninstallDisplayName={#AppName} {#AppVersion}
UninstallDisplayIcon={app}\{#AppExeName}
; The app is a local web server; an upgrade over a running copy would fail on a
; locked exe.  Let Setup find it and offer to close it.
CloseApplications=yes
RestartApplications=no
; The PATH task edits the environment, so tell Explorer to re-read it.
ChangesEnvironment=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Shortcuts:"
Name: "addtopath"; Description: "Add the &command line (buttcrack) to my PATH"; \
    GroupDescription: "Command line:"; Flags: unchecked

[Files]
; The whole PyInstaller output tree, Python runtime and language model included.
Source: "{#SourceDir}\{#AppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\{#CliExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#SourceDir}\_internal\*"; DestDir: "{app}\_internal"; \
    Flags: ignoreversion recursesubdirs createallsubdirs
; Opens a prompt with {app} on PATH, so the CLI is reachable even when the
; user declined the PATH task.
Source: "buttcrack-prompt.cmd"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; \
    Comment: "Break ciphers on this machine -- nothing is uploaded"
Name: "{group}\{#AppName} command line"; Filename: "{app}\buttcrack-prompt.cmd"; \
    IconFilename: "{app}\{#CliExeName}"; \
    Comment: "A command prompt with buttcrack on PATH"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
; Per-user PATH.  {olddata} keeps whatever was already there; the Check stops
; a reinstall appending a second copy.
Root: HKCU; Subkey: "Environment"; ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}"; Tasks: addtopath; Check: NeedsAddPath(ExpandConstant('{app}'))

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Start {#AppName} now"; \
    Flags: nowait postinstall skipifsilent

[UninstallDelete]
; __pycache__ and anything else the runtime dropped next to the bundle.
Type: filesandordirs; Name: "{app}\_internal"
Type: dirifempty; Name: "{app}"

[Code]
function NeedsAddPath(Param: string): Boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
  begin
    Result := True;
    exit;
  end;
  { Semicolon-pad both sides so "C:\Foo" does not match inside "C:\FooBar". }
  Result := Pos(';' + Lowercase(Param) + ';', ';' + Lowercase(OrigPath) + ';') = 0;
end;

procedure RemoveFromPath(Param: string);
var
  OrigPath: string;
  Position: Integer;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath) then
    exit;
  Position := Pos(';' + Lowercase(Param), ';' + Lowercase(OrigPath));
  if Position = 0 then
    exit;
  Delete(OrigPath, Position, Length(Param) + 1);
  RegWriteExpandStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  { Leaving a dead directory on PATH slows down every command the user types
    afterwards, so clean up after ourselves. }
  if CurUninstallStep = usPostUninstall then
    RemoveFromPath(ExpandConstant('{app}'));
end;
