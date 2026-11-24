; Inno Setup Script for YTDownloader (AliCH Edition)
#define MyAppName "YTDownloader (AliCH Edition)"
#define MyAppVersion "2.5"
#define MyAppPublisher "AliCH"
#define MyAppExeName "YTDownloader.exe"

[Setup]
AppId={{D37E881B-8714-4A3C-9E21-72901AFB448C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL=https://github.com/yt-dlp/yt-dlp
AppSupportURL=https://github.com/yt-dlp/yt-dlp
AppUpdatesURL=https://github.com/yt-dlp/yt-dlp
DefaultDirName={localappdata}\YTDownloader
DisableProgramGroupPage=yes
DefaultGroupName={#MyAppName}
OutputDir=C:\Users\AliCH\Desktop
OutputBaseFilename=YTDownloader_Setup_by_AliCH
SetupIconFile=C:\Users\AliCH\yt-dlp-gui\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayIcon={app}\app_icon.ico
VersionInfoVersion=2.5.0.0
VersionInfoCompany=AliCH
VersionInfoDescription=YTDownloader Installer by AliCH
VersionInfoCopyright=Copyright (C) 2026 AliCH

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "C:\Users\AliCH\yt-dlp-gui\dist\YTDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Install Peyda fonts directly to Windows Fonts directory
Source: "C:\Users\AliCH\yt-dlp-gui\dist\YTDownloader\fonts\*.ttf"; DestDir: "{autofonts}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Comment: "YTDownloader - Packaged by AliCH"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\YTDownloader"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "YTDownloader - Packaged by AliCH"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,YTDownloader}"; Flags: nowait postinstall skipifsilent
