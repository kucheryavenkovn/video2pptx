; Inno Setup script for Video2PPTX
; Requires Inno Setup 6+ (https://jrsoftware.org/isdl.php)
; Build: ISCC packaging/windows/installer/video2pptx.iss
; Source layout: dist/windows/Video2PPTX/*

#define MyAppName "Video2PPTX"
#define MyAppVersion GetEnv("VERSION")
#define MyAppPublisher "kucheryavenkovn"
#define MyAppURL "https://github.com/kucheryavenkovn/video2pptx"
#define MyAppExeName "Video2PPTX.exe"

[Setup]
AppId={{B8F4A3D1-2C5E-4A7B-9F6D-1E3A5B7C9D0E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\..\dist\windows
OutputBaseFilename=Video2PPTX-{#MyAppVersion}-Setup-x64
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\..\..\dist\windows\Video2PPTX\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:ProgramOnTheWeb,{#MyAppName}}"; Filename: "{#MyAppURL}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup: Boolean;
begin
  Result := True;
end;
