; installer.iss - скрипт установщика PumpTestApp (Inno Setup)
;
; Собирается ПОСЛЕ того, как PyInstaller уже создал папку dist\PumpTestApp
; (см. PumpTestApp.spec) - установщик просто упаковывает эту готовую
; папку, ничего сам не собирает.
;
; Запуск сборки установщика - не напрямую, а через build_installer.py
; (тот сам генерирует build_config.iss с версией/организацией/паролем
; перед вызовом ISCC.exe).

#define MyAppName "PumpTestApp"
; Версия, название организации и основной пароль (для проверки на
; экране резервного пароля) подставляются автоматически при сборке -
; см. installer/build_installer.py, который перед вызовом ISCC.exe
; генерирует installer/build_config.iss с соответствующими #define
#include "build_config.iss"
#define MyAppExeName "PumpTestApp.exe"
#define MyAppIcon "..\gur_pump_icon.ico"

; Путь к сетевой базе, показываемый в поле установщика ПОДСКАЗКОЙ
; (серым текстом-placeholder, а не готовым предзаполненным значением) -
; поменять на актуальный перед сборкой конкретного релиза, если он
; известен заранее. Пустая строка - поле будет без подсказки вообще.
#define DefaultNetworkPath ""

[Setup]
AppId={{96933B00-DE55-45A9-B91B-A80A158AF384}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\PumpTestApp
DisableProgramGroupPage=yes
; Ни один файл программы не идёт в Меню Пуск - см. секцию [Icons], там
; только ярлык на рабочий стол
PrivilegesRequired=lowest
OutputDir=output
OutputBaseFilename=PumpTestApp_Setup_v{#MyAppVersion}
SetupIconFile={#MyAppIcon}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
; Обновление поверх уже установленной версии - без лишних вопросов о
; переустановке, файлы программы просто заменяются (см. также [Files] -
; пользовательские данные в data\ этим не затрагиваются)
DisableWelcomePage=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительные значки:"; Flags: checkedonce

[Files]
; Вся папка сборки PyInstaller целиком - код, библиотеки, ресурсы.
; ВАЖНО: dist\PumpTestApp НЕ должна содержать никакой папки data - её
; заполняет сам установщик (см. ниже), отдельно от кода программы
Source: "..\dist\PumpTestApp\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Предзаполненная реальными данными база - копируется ТОЛЬКО если её
; там ещё нет (onlyifdoesntexist) - при обновлении поверх уже
; установленной версии реальная, наработанная пользователем база НЕ
; затирается заново предзаполненной
Source: "prefilled_data\pumps.db"; DestDir: "{app}\data"; Flags: onlyifdoesntexist

[Dirs]
; Пустая папка для резервных копий - создаётся, если её ещё нет
Name: "{app}\data\backups"

[Icons]
; Только рабочий стол - в Меню Пуск ничего не добавляется вовсе
Name: "{userdesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Запустить {#MyAppName}"; Flags: nowait postinstall skipifsilent

[Registry]
; Записывается в ТОЧНО то же место реестра, куда сама программа пишет
; через QSettings("PumpTestApp", "MainSettings") - при первом запуске
; программа увидит эти значения уже готовыми, как будто пользователь
; сам зашёл в настройки и всё указал
Root: HKCU; Subkey: "Software\PumpTestApp\MainSettings"; ValueType: string; ValueName: "db_mode"; ValueData: "network"; Flags: uninsdeletevalue; Check: NetworkPathProvided
Root: HKCU; Subkey: "Software\PumpTestApp\MainSettings"; ValueType: string; ValueName: "network_db_path"; ValueData: "{code:GetEnteredNetworkPath}"; Flags: uninsdeletevalue; Check: NetworkPathProvided

[Code]
var
  MainPasswordPage: TInputQueryWizardPage;
  PasswordPage: TInputQueryWizardPage;
  NetworkPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  { Проверка основного пароля - от неё зависит, покажется ли вообще
    следующий экран (настройка резервного пароля). Не каждый, кто
    устанавливает программу, должен иметь возможность задать себе
    резервный пароль - только тот, кто знает основной. Поле можно
    оставить пустым - тогда резервный пароль просто не настраивается
    сейчас (экран резервного пароля будет пропущен), без ошибки. }
  MainPasswordPage := CreateInputQueryPage(wpSelectDir,
    'Основной пароль', 'Подтверждение доступа к настройке резервного пароля',
    'Чтобы задать резервный пароль для этого компьютера, введите ' +
    'основной пароль программы. Если вы его не знаете или не хотите ' +
    'настраивать резервный пароль сейчас - просто оставьте поле пустым ' +
    'и нажмите "Далее".');
  MainPasswordPage.Add('Основной пароль (необязательно):', True);

  { Резервный (аварийный) пароль - показывается только тем, кто верно
    ввёл основной пароль на предыдущем экране (см. ShouldSkipPage) }
  PasswordPage := CreateInputQueryPage(MainPasswordPage.ID,
    'Резервный пароль', 'Необязательный аварийный пароль для этого компьютера',
    'Резервный пароль работает НАРЯДУ с основным (не заменяет его) - ' +
    'пригодится, если основной пароль забудется. Можно оставить поле ' +
    'пустым и настроить это позже, при необходимости.');
  PasswordPage.Add('Резервный пароль (необязательно):', True);

  { Путь к сетевой базе - предзаполнен значением по умолчанию, заданным
    при сборке установщика (DefaultNetworkPath выше). Если оставить
    поле пустым - сетевой режим просто не будет включён, программа
    будет работать с локальной базой (это можно будет включить позже
    через настройки самой программы) }
  NetworkPage := CreateInputQueryPage(PasswordPage.ID,
    'Общая сетевая база данных', 'Расположение общего файла базы (если используется)',
    'Если несколько человек работают с одной общей базой по сети - ' +
    'укажите путь к общему файлу здесь. Если программа будет ' +
    'использоваться только на этом компьютере - сотрите значение поля.');
  NetworkPage.Add('Путь к сетевой базе (необязательно):', False);
  NetworkPage.Values[0] := '{#DefaultNetworkPath}';
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := False;
  { Экран резервного пароля пропускается целиком, если основной пароль
    не был введён верно на предыдущем шаге (в том числе если поле
    оставили пустым) }
  if PageID = PasswordPage.ID then
    Result := Trim(MainPasswordPage.Values[0]) <> '{#MainPasswordPlain}';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Entered: String;
begin
  Result := True;
  if CurPageID = MainPasswordPage.ID then
  begin
    Entered := Trim(MainPasswordPage.Values[0]);
    { Пустое поле - это осознанный отказ от настройки резервного
      пароля сейчас, а не ошибка - пропускаем дальше молча. А вот если
      что-то ВВЕДЕНО, но неверно - сообщаем об этом явно, а не тихо
      пропускаем экран резервного пароля, оставляя человека в
      недоумении, почему его вообще не показали }
    if (Entered <> '') and (Entered <> '{#MainPasswordPlain}') then
    begin
      MsgBox('Основной пароль введён неверно.' + #13#10 +
             'Оставьте поле пустым, если не хотите настраивать резервный пароль сейчас.',
             mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function GetEnteredPassword(): String;
begin
  Result := Trim(PasswordPage.Values[0]);
end;

function GetEnteredNetworkPath(Param: String): String;
begin
  Result := Trim(NetworkPage.Values[0]);
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  SysDir: String;
  PendingFile: String;
begin
  if CurStep = ssPostInstall then
  begin
    { Резервный пароль - пишем ОТКРЫТЫМ ТЕКСТОМ во временный файл;
      сама программа при первом запуске хеширует его и сразу удаляет
      этот временный файл (см. auth.process_pending_password) - таким
      образом реальное хеширование делает Python, а не Pascal Script
      установщика }
    if GetEnteredPassword() <> '' then
    begin
      SysDir := ExpandConstant('{app}\.pumpapp_sys');
      if not DirExists(SysDir) then
        CreateDir(SysDir);
      PendingFile := SysDir + '\pending_password.txt';
      SaveStringToFile(PendingFile, GetEnteredPassword(), False);
    end;
  end;
end;

function NetworkPathProvided(): Boolean;
begin
  Result := GetEnteredNetworkPath('') <> '';
end;
