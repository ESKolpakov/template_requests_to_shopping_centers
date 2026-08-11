# PyInstaller spec — сборка приложения в единый .exe без требования
# устанавливать Python на компьютер пользователя (см. ТЗ, раздел 1).
#
# Запуск (из корня репозитория, в окружении со всеми зависимостями из
# requirements-dev.txt, на Windows):
#   pyinstaller scripts/build_exe.spec
# Результат — dist/UKTCLetters/UKTCLetters.exe (или dist/UKTCLetters.exe
# при отключении --onedir в пользу --onefile — см. параметры ниже).

import sys
from pathlib import Path

block_cipher = None

# pymorphy3-dicts-ru хранит словари как пакетные данные — PyInstaller не
# подхватывает их автоматически без явного hiddenimport/collect_data_files.
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = []
datas += collect_data_files("pymorphy3_dicts_ru")
hiddenimports = collect_submodules("pymorphy3_dicts_ru")

# В .spec-файлах PyInstaller выполняет код через exec(), поэтому обычной
# переменной __file__ здесь нет — вместо неё PyInstaller сам подставляет
# в глобальное пространство имён SPECPATH (папка, где лежит .spec).
repo_root = Path(SPECPATH).resolve().parent
entry_point = str(repo_root / "src" / "uktc_letters" / "main.py")

a = Analysis(
    [entry_point],
    pathex=[str(repo_root / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
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
    name="UKTCLetters",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="UKTCLetters",
)
