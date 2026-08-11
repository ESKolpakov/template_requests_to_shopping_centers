"""Настройки приложения (ТЗ, раздел 7) — хранятся в JSON-файле в
пользовательском каталоге данных (см. paths.py), не в репозитории.

Важно про значения по умолчанию: ТЗ приводит в качестве примера значений
по умолчанию реальные ФИО и телефон конкретного сотрудника-исполнителя.
Эти значения — персональные данные конкретного человека, поэтому в код
(публикуемый в открытом репозитории) они НЕ зашиваются: поля
"Исполнитель", "Телефон исполнителя" и "Подписант" по умолчанию пустые и
заполняются пользователем один раз при первом запуске в разделе
«Настройки» — дальше сохраняются локально в config.json и никуда не
публикуются.
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from dataclasses import dataclass, field

from .dates import DEFAULT_DEADLINE_DAYS, default_holidays
from .paths import config_file_path

__all__ = ["Settings", "load_settings", "save_settings"]


@dataclass
class Settings:
    deadline_days: int = DEFAULT_DEADLINE_DAYS
    holidays: list[str] = field(default_factory=list)  # "YYYY-MM-DD"

    executor_name: str = ""
    executor_phone: str = ""
    signatory_name: str = ""

    template_path: str = ""
    objects_source_path: str = ""
    contacts_source_path: str = ""
    downloads_dir: str = ""  # папка загрузок браузера — для поиска PDF ЕГРЮЛ

    def holiday_dates(self) -> list[datetime.date]:
        result = []
        for s in self.holidays:
            try:
                result.append(datetime.date.fromisoformat(s))
            except ValueError:
                continue
        return result

    def ensure_default_holidays(self, years: list[int] | None = None) -> None:
        """Добавить базовый набор фиксированных праздников РФ (ТЗ п.4.3)
        для указанных лет, если их там ещё нет. По умолчанию — для
        текущего и следующего года (чтобы приложение не "ломалось" на
        стыке лет). Список остаётся полностью редактируемым пользователем
        в интерфейсе."""
        years = years or [datetime.date.today().year, datetime.date.today().year + 1]
        existing = set(self.holidays)
        for year in years:
            for d in default_holidays(year):
                iso = d.isoformat()
                if iso not in existing:
                    self.holidays.append(iso)
                    existing.add(iso)
        self.holidays.sort()


def load_settings(path=None) -> Settings:
    path = path or config_file_path()
    if not path.exists():
        settings = Settings()
        settings.ensure_default_holidays()
        return settings
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        settings = Settings()
        settings.ensure_default_holidays()
        return settings
    field_names = {f.name for f in dataclasses.fields(Settings)}
    filtered = {k: v for k, v in raw.items() if k in field_names}
    settings = Settings(**filtered)
    if not settings.holidays:
        settings.ensure_default_holidays()
    return settings


def save_settings(settings: Settings, path=None) -> None:
    path = path or config_file_path()
    path.write_text(
        json.dumps(dataclasses.asdict(settings), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
