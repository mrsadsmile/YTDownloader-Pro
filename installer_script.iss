; Inno Setup Script for YTDownloader Pro
#define MyAppName "YTDownloader Pro"
#define MyAppVersion "2.9.0"
#define MyAppPublisher "YTDownloader Community"
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
OutputBaseFilename=YTDownloader_Setup
SetupIconFile=C:\Users\AliCH\yt-dlp-gui\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\app_icon.ico
VersionInfoVersion=2.9.0.0
VersionInfoCompany=YTDownloader Community
VersionInfoDescription=YTDownloader Pro Standalone Installer
VersionInfoCopyright=Powered by yt-dlp & FFmpeg

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce

[Files]
Source: "C:\Users\AliCH\yt-dlp-gui\dist\YTDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; Fonts (optional fallback to system UI fonts)
; Source: "C:\Users\AliCH\yt-dlp-gui\dist\YTDownloader\fonts\*.ttf"; DestDir: "{autofonts}"; Flags: onlyifdoesntexist uninsneveruninstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Comment: "YTDownloader Pro - Powered by yt-dlp"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\YTDownloader"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\app_icon.ico"; Tasks: desktopicon; Comment: "YTDownloader Pro - Powered by yt-dlp"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,YTDownloader}"; Flags: nowait postinstall skipifsilent
