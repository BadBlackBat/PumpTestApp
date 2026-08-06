# -*- mode: python ; coding: utf-8 -*-
"""
PumpTestApp.spec - файл сборки PyInstaller (режим --onedir, с папкой).

Запуск сборки (из корня проекта, где лежат run.py и эта папка src):
    .venv\\Scripts\\python.exe -m PyInstaller PumpTestApp.spec --noconfirm

Результат появится в dist\\PumpTestApp\\ - именно эту папку целиком
Inno Setup дальше упаковывает в установщик (см. installer\\installer.iss).

ПРИМЕЧАНИЕ О hiddenimports: pandas/openpyxl используют часть модулей
через динамический импорт, который статический анализ PyInstaller не
всегда обнаруживает сам. Ниже - список того, что обычно требуется для
такого набора библиотек по опыту типичных сборок; если после первой
сборки при запуске появится ModuleNotFoundError на что-то ещё - нужно
будет просто добавить недостающее имя в этот список и пересобрать.
Заранее гарантировать полноту этого списка без реальной сборки на
Windows-машине невозможно.
"""
import os

block_cipher = None

# Версия читается из src/version.py автоматически - одно место правды,
# то же самое, что видит пользователь в настройках программы
_version_ns = {}
with open(os.path.join('src', 'version.py'), encoding='utf-8') as f:
    exec(f.read(), _version_ns)
APP_VERSION = _version_ns['VERSION']

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/resources', 'resources'),
    ],
    hiddenimports=[
        # pandas - чтение Excel-файлов в excel_importer.py
        'pandas._libs.tslibs.timedeltas',
        'pandas._libs.tslibs.np_datetime',
        'pandas._libs.tslibs.nattype',
        'pandas._libs.skiplist',
        'pandas._libs.tslibs.base',
        # openpyxl - движок pandas для чтения .xlsx
        'openpyxl.cell._writer',
        # matplotlib - явный бэкенд, используемый в right_panel.py
        'matplotlib.backends.backend_qt5agg',
        'matplotlib.backends.backend_agg',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PumpTestApp',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # GUI-приложение - без окна консоли на заднем плане
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='gur_pump_icon.ico',
    version=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PumpTestApp',
)
