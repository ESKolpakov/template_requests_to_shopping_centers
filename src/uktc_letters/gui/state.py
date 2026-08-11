"""Общее состояние GUI-приложения между вкладками."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import Settings, load_settings, save_settings
from ..contacts_source import ContactRecord, ContactsIndex
from ..egrul_cache import load_egrul_cache, save_egrul_cache
from ..egrul_parser import EgrulData
from ..objects_source import BuildingGroup, TradeObjectRow
from ..registry import Registry


@dataclass
class AppState:
    settings: Settings = field(default_factory=load_settings)
    registry: Registry = field(default_factory=Registry)

    template_path: str = ""

    objects_rows: list[TradeObjectRow] = field(default_factory=list)
    building_groups: list[BuildingGroup] = field(default_factory=list)

    contact_records: list[ContactRecord] = field(default_factory=list)
    contacts_index: ContactsIndex | None = None

    # Результаты проверки по ЕГРЮЛ: нормализованный адрес -> разобранные
    # данные (ТЗ, раздел 6). Подгружаются из локального кэша при старте
    # (см. egrul_cache.py), чтобы при следующей генерации по этому же
    # адресу запрос не повторялся.
    egrul_overrides: dict[str, EgrulData] = field(default_factory=load_egrul_cache)

    def __post_init__(self) -> None:
        if not self.template_path:
            self.template_path = self.settings.template_path

    def save_settings(self) -> None:
        save_settings(self.settings)

    def confirm_egrul_result(self, address_key: str, data: EgrulData) -> None:
        self.egrul_overrides[address_key] = data
        save_egrul_cache(self.egrul_overrides)
