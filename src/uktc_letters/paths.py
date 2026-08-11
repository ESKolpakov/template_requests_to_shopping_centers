"""Расположение пользовательских данных приложения на диске.

Всё, что приложение сохраняет между запусками (настройки, путь к
последнему шаблону, реестр результатов генерации, сохранённые правки
справочника УК/ТЦ), хранится в стандартной пользовательской папке
конфигурации ОС — НЕ в каталоге установки/исходников приложения. Это
особенно важно, т.к. каталог исходников этого приложения выложен в
открытый Git-репозиторий: реальные адреса, ИНН, ФИО и файлы конкретных
писем/выписок ЕГРЮЛ пользователя никогда не должны туда попадать.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIR_NAME = "UKTCLetters"


def app_data_dir() -> Path:
    """Каталог для хранения конфигурации/реестра/шаблонов пользователя."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        path = Path(base) / APP_DIR_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        path = Path(base) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_file_path() -> Path:
    return app_data_dir() / "config.json"


def registry_db_path() -> Path:
    return app_data_dir() / "registry.sqlite3"


def default_templates_dir() -> Path:
    d = app_data_dir() / "templates"
    d.mkdir(parents=True, exist_ok=True)
    return d


def default_output_dir() -> Path:
    d = app_data_dir() / "letters"
    d.mkdir(parents=True, exist_ok=True)
    return d
