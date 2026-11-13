; Inno Setup Skript fuer R3E Cockpit (Vorlage: pitboss-r3e/installer/setup.iss)
; Baut aus dist\R3ECockpit\ einen Windows-Installer.
; Version kommt aus der Umgebungsvariable APP_VERSION (in CI aus dem Git-Tag).
#define AppName "R3E Cockpit"
#ifndef AppVer
  #define AppVer GetEnv("APP_VERSION")
#endif
#if AppVer == ""
  #define AppVer "0.0.0"
#endif

[Setup]
AppName={#AppName}
AppVersion={#AppVer}
AppPublisher=R3E Cockpit
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName} {#AppVer}
OutputDir=Output
OutputBaseFilename=R3ECockpit-Setup-{#AppVer}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
WizardStyle=modern
PrivilegesRequired=lowest
SetupIconFile=..\assets\cockpit.ico
UninstallDisplayIcon={app}\R3ECockpit.exe

[Languages]
Name: "de"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "Desktop-Verknuepfung erstellen"; GroupDescription: "Zusaetzliche Symbole:"

[Files]
Source: "..\dist\R3ECockpit\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\R3ECockpit.exe"
Name: "{group}\{#AppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\R3ECockpit.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\R3ECockpit.exe"; Description: "{#AppName} starten"; Flags: nowait postinstall skipifsilent
