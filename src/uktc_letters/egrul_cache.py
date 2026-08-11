"""Локальный кэш результатов проверки по ЕГРЮЛ (ТЗ, п.6, шаг 6: "чтобы при
следующей генерации по этому же адресу запрос не повторялся").

Хранится отдельным JSON-файлом в пользовательском каталоге данных
(см. paths.py) — сознательно НЕ пишется напрямую в файл справочника УК/ТЦ
пользователя (риск повредить формат/данные реального Excel-файла при
автоматической правке); при следующей загрузке справочника кэш
подмешивается в сопоставление на уровне приложения.
"""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .egrul_parser import EgrulData
from .paths import app_data_dir

__all__ = ["egrul_cache_path", "load_egrul_cache", "save_egrul_cache"]


def egrul_cache_path() -> Path:
    return app_data_dir() / "egrul_cache.json"


def load_egrul_cache(path: Path | None = None) -> dict[str, EgrulData]:
    path = path or egrul_cache_path()
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    result = {}
    field_names = {f.name for f in dataclasses.fields(EgrulData)}
    for key, value in raw.items():
        filtered = {k: v for k, v in value.items() if k in field_names}
        result[key] = EgrulData(**filtered)
    return result


def save_egrul_cache(cache: dict[str, EgrulData], path: Path | None = None) -> None:
    path = path or egrul_cache_path()
    raw = {key: dataclasses.asdict(value) for key, value in cache.items()}
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
