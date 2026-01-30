; Water Intake Tracker - Inno Setup Script
; Instalador profissional para Windows
;
; Requer: Inno Setup 6.x (https://jrsoftware.org/isinfo.php)
;
; Para compilar:
;   1. Instale o Inno Setup
;   2. Abra este arquivo no Inno Setup Compiler
;   3. Clique em Build > Compile
;   Ou via linha de comando: iscc installer.iss

#define MyAppName "Water Intake Tracker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "AI Drink Water"
#define MyAppURL "https://github.com/seu-usuario/AI-drink-water"
#define MyAppExeName "WaterIntakeTracker.exe"
#define MyAppDescription "Acompanhe sua hidratacao com inteligencia artificial"

[Setup]
; Identificador unico do app (NAO ALTERE depois de publicar!)
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}

; Diretorios de instalacao
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}

; Arquivos de saida
OutputDir=installer_output
OutputBaseFilename=WaterIntakeTracker_Setup_{#MyAppVersion}

; Icone e visual
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; Compressao
Compression=lzma2/ultra64
SolidCompression=yes
LZMAUseSeparateProcess=yes

; Permissoes (nao precisa de admin para instalar em AppData)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Visual do instalador
WizardStyle=modern
WizardSizePercent=100
DisableProgramGroupPage=yes
DisableWelcomePage=no

; Info adicional
VersionInfoVersion={#MyAppVersion}
VersionInfoDescription={#MyAppDescription}

[Languages]
Name: "brazilianportuguese"; MessagesFile: "compiler:Languages\BrazilianPortuguese.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Iniciar automaticamente com o Windows"; GroupDescription: "Opcoes adicionais:"

[Files]
; Executavel principal
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; Icone
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion

; Pastas de recursos
Source: "sounds\*"; DestDir: "{app}\sounds"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "mascots\*"; DestDir: "{app}\mascots"; Flags: ignoreversion recursesubdirs createallsubdirs; Excludes: "*.md,README*"
Source: "personalities\*"; DestDir: "{app}\personalities"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "models\*"; DestDir: "{app}\models"; Flags: ignoreversion recursesubdirs createallsubdirs

; Pasta de dados (vazia inicialmente, criada pelo app)
Source: "data\*"; DestDir: "{app}\data"; Flags: ignoreversion recursesubdirs createallsubdirs onlyifdoesntexist

; Config padrao (so copia se nao existir - preserva config do usuario)
Source: "user_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist

[Icons]
; Menu Iniciar
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Comment: "{#MyAppDescription}"
Name: "{group}\Desinstalar {#MyAppName}"; Filename: "{uninstallexe}"; IconFilename: "{app}\icon.ico"

; Desktop (opcional)
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon; Comment: "{#MyAppDescription}"

; Startup (opcional)
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startupicon; Comment: "Iniciar Water Intake Tracker com o Windows"

[Run]
; Executar apos instalacao (opcional)
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Limpar arquivos gerados pelo app na desinstalacao
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files; Name: "{app}\user_config.json"

[Code]
// Verificar se o app ja esta rodando antes de instalar/desinstalar
function IsAppRunning(): Boolean;
var
  ResultCode: Integer;
begin
  Result := False;
  if Exec('tasklist', '/FI "IMAGENAME eq {#MyAppExeName}" /NH', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // Se encontrou o processo, retorna True
    Result := (ResultCode = 0);
  end;
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Aviso se o app estiver rodando
  if IsAppRunning() then
  begin
    if MsgBox('O Water Intake Tracker parece estar em execucao.' + #13#10 + #13#10 +
              'Por favor, feche o aplicativo antes de continuar.' + #13#10 + #13#10 +
              'Deseja continuar mesmo assim?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      Result := False;
    end;
  end;
end;

function InitializeUninstall(): Boolean;
begin
  Result := True;
  if IsAppRunning() then
  begin
    MsgBox('O Water Intake Tracker esta em execucao.' + #13#10 + #13#10 +
           'Por favor, feche o aplicativo (clique com botao direito no icone da bandeja e selecione "Sair") antes de desinstalar.',
           mbError, MB_OK);
    Result := False;
  end;
end;
