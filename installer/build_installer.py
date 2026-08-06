# -*- coding: utf-8 -*-
"""
build_installer.py - полная сборка установщика одной командой:
запрос параметров сборки -> PyInstaller -> Inno Setup.

Запуск (из корня проекта, там же, где run.py и PumpTestApp.spec):
    .venv\\Scripts\\python.exe installer\\build_installer.py

Требования перед первым запуском:
    - PyInstaller должен быть установлен в .venv:
      .venv\\Scripts\\python.exe -m pip install pyinstaller --break-system-packages
    - Inno Setup должен быть установлен в системе (скачивается отдельно,
      с официального сайта jrsoftware.org) - ISCC.exe ищется автоматически
      по нескольким типичным путям установки (см. find_iscc() ниже); если
      не найдётся ни по одному - добавьте свой реальный путь в список
      candidates внутри этой функции.
    - Файл installer/prefilled_data/pumps.db должен существовать -
      это готовая, наполненная реальными данными база, которая будет
      установлена как локальная база по умолчанию при первой установке
      программы (при обновлении поверх уже установленной версии эта
      база НЕ перезаписывает то, что уже наработал пользователь).

ВАЖНО: этот скрипт СПРАШИВАЕТ основной пароль программы и ЗАПИСЫВАЕТ
его прямо в src/auth.py (DEFAULT_PASSWORD) перед сборкой - то есть
реально ИЗМЕНЯЕТ исходный файл на диске, не только временный артефакт
сборки. Это осознанно - основной пароль должен быть одним и тем же на
всех копиях конкретного релиза, и самый надёжный способ гарантировать
это - задавать его как часть самого процесса сборки, а не полагаться на
то, что кто-то не забудет отредактировать файл вручную заранее.
"""
import os
import re
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTALLER_DIR = os.path.dirname(os.path.abspath(__file__))
AUTH_PY_PATH = os.path.join(PROJECT_ROOT, 'src', 'auth.py')


def find_iscc():
    """Ищет ISCC.exe (компилятор Inno Setup) по нескольким типичным
    местам установки - обычной (с правами администратора, в Program
    Files) и без прав администратора (в профиль текущего пользователя -
    именно так Inno Setup обычно ставится, если во время его
    собственной установки отказаться от повышения прав)."""
    candidates = [
        r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        r"C:\Program Files\Inno Setup 6\ISCC.exe",
        os.path.expandvars(r"%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def get_current_main_password():
    """Читает ТЕКУЩЕЕ значение DEFAULT_PASSWORD из src/auth.py - чтобы
    предложить его как вариант "оставить как есть" при запросе пароля
    для новой сборки, вместо того чтобы каждый раз вводить заново."""
    with open(AUTH_PY_PATH, encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'DEFAULT_PASSWORD = "(.*)"', content)
    return match.group(1) if match else None


def apply_main_password(main_password):
    """Записывает основной пароль прямо в src/auth.py - единственное
    место в коде программы, откуда берётся DEFAULT_PASSWORD."""
    with open(AUTH_PY_PATH, encoding='utf-8') as f:
        content = f.read()
    new_content, count = re.subn(
        r'DEFAULT_PASSWORD = ".*"',
        f'DEFAULT_PASSWORD = "{main_password}"',
        content,
        count=1,
    )
    if count == 0:
        print("ОШИБКА: не удалось найти строку DEFAULT_PASSWORD в src/auth.py")
        print("Пароль не изменён - проверьте файл вручную.")
        sys.exit(1)
    with open(AUTH_PY_PATH, 'w', encoding='utf-8') as f:
        f.write(new_content)


def prompt_build_config():
    """Запрашивает параметры конкретной сборки - основной пароль
    (одинаковый на всех копиях этого релиза) и название организации
    (показывается пользователю на экране установки)."""
    print("=== Параметры сборки ===")

    current_password = get_current_main_password()
    if current_password:
        prompt = f"Основной пароль программы [сейчас: {current_password}, Enter - оставить как есть]: "
    else:
        prompt = "Основной пароль программы: "
    entered = input(prompt).strip()
    main_password = entered if entered else current_password
    if not main_password:
        print("Основной пароль не может быть пустым.")
        sys.exit(1)

    publisher = input("Название организации (показывается при установке) [NAMI]: ").strip() or "NAMI"

    print()
    return main_password, publisher


def generate_build_config_iss(app_version, publisher, main_password):
    """Пишет installer/build_config.iss, который подключается в
    installer.iss через #include - одно место правды для версии,
    названия организации и основного пароля (нужен установщику для
    проверки на экране резервного пароля - см. installer.iss), без
    ручного дублирования между кодом программы и установщиком."""
    build_config_path = os.path.join(INSTALLER_DIR, 'build_config.iss')
    with open(build_config_path, 'w', encoding='utf-8') as f:
        f.write(f'#define MyAppVersion "{app_version}"\n')
        f.write(f'#define MyAppPublisher "{publisher}"\n')
        f.write(f'#define MainPasswordPlain "{main_password}"\n')
    print(f"[1/3] Версия: {app_version} | Организация: {publisher}")


def get_app_version():
    version_ns = {}
    version_py = os.path.join(PROJECT_ROOT, 'src', 'version.py')
    with open(version_py, encoding='utf-8') as f:
        exec(f.read(), version_ns)
    return version_ns['VERSION']


def check_prefilled_database():
    """Проверяет, что предзаполненная база есть на месте - без неё
    установщик соберётся, но при первой установке программы база
    окажется пустой, что почти наверняка не то, что нужно."""
    db_path = os.path.join(INSTALLER_DIR, 'prefilled_data', 'pumps.db')
    if not os.path.exists(db_path):
        print(f"ВНИМАНИЕ: не найдена предзаполненная база данных: {db_path}")
        print("Установщик соберётся, но при первой установке локальная")
        print("база окажется пустой. Если это ожидаемо - можно продолжать.")
        answer = input("Продолжить сборку без предзаполненной базы? (yes/нет): ")
        if answer.strip().lower() != 'yes':
            print("Сборка отменена.")
            sys.exit(1)


def run_pyinstaller():
    print("[2/3] Сборка PyInstaller (может занять несколько минут)...")
    spec_path = os.path.join(PROJECT_ROOT, 'PumpTestApp.spec')
    result = subprocess.run(
        [sys.executable, '-m', 'PyInstaller', spec_path, '--noconfirm'],
        cwd=PROJECT_ROOT,
    )
    if result.returncode != 0:
        print("Сборка PyInstaller завершилась с ошибкой - установщик собирать не буду.")
        sys.exit(1)


def run_inno_setup():
    print("[3/3] Сборка установщика Inno Setup...")
    iscc_path = find_iscc()
    if not iscc_path:
        print("Не найден ISCC.exe ни по одному из типичных путей установки Inno Setup.")
        print("Добавьте реальный путь в список candidates внутри функции find_iscc().")
        sys.exit(1)
    print(f"      Используется: {iscc_path}")
    iss_path = os.path.join(INSTALLER_DIR, 'installer.iss')
    result = subprocess.run([iscc_path, iss_path])
    if result.returncode != 0:
        print("Сборка установщика завершилась с ошибкой.")
        sys.exit(1)


if __name__ == "__main__":
    main_password, publisher = prompt_build_config()
    apply_main_password(main_password)
    app_version = get_app_version()
    generate_build_config_iss(app_version, publisher, main_password)
    check_prefilled_database()
    run_pyinstaller()
    run_inno_setup()
    print("\nГотово! Установщик - в installer/output/")