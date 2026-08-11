"""Разбор справочника контактов УК/ТЦ (см. ТЗ п.3.2) и сопоставление его
записей с адресом здания из выгрузки объектов торговли.

Файл — перезагружаемый пользователем в любой момент (см. ТЗ), поэтому
парсер ищет нужные столбцы ПО ЗАГОЛОВКУ (с допуском на переносы строк/
лишние пробелы в заголовке), а не по фиксированному номеру колонки, и не
требует конкретного количества строк.

Ключевые допущения, зафиксированные ТЗ (раздел 9 — то, что НЕ
автоматизируется):
  - если для одного адреса найдено НЕСКОЛЬКО строк справочника — это
    считается неоднозначностью и помечается как "требует ручной проверки",
    без попытки алгоритмически выбрать "правильную" запись (в т.ч. если
    одна из строк — запись-примечание об "отменённой" УК, см. пример
    "ООО «Амистад» не является управляющей компанией ТЦ «Вектор»");
  - если в поле ИНН одной строки указано два и более ИНН (пример:
    Варшавское шоссе, 26с7 — 7718784153 и 7714469866) — строка тоже
    помечается как "требует ручной проверки".
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import openpyxl

from .addresses import building_key

__all__ = [
    "ContactRecord",
    "MatchStatus",
    "MatchResult",
    "load_contacts",
    "ContactsIndex",
]


def _norm_header(text) -> str:
    if text is None:
        return ""
    return re.sub(r"\s+", " ", str(text)).strip().lower()


# (канонический ключ, список возможных префиксов заголовка, в порядке
# убывания специфичности — важно проверять более длинные/специфичные
# варианты раньше общих, иначе, например, "инн управляющей компании"
# перехватится как "инн ...").
_HEADER_RULES: list[tuple[str, list[str]]] = [
    ("address", ["адрес/иные ориентиры", "адрес"]),
    ("district", ["район"]),
    ("okrug", ["административный округ"]),
    ("tc_name", ["наименование тц", "наименование тс", "наименование то"]),
    ("approx_count", ["предполагаемое количество"]),
    ("opf", ["организационно-правовая форма"]),
    ("management_company", ["управляющая компания"]),
    ("inn", ["инн управляющей компании", "инн"]),
    ("director_name", ["руководитель управляющей компании", "руководитель"]),
    ("phone", ["телефон управляющей компании", "телефон"]),
    ("email", ["email управляющей компании", "email", "e-mail"]),
    ("extra_info", ["дополнительная информация"]),
    ("response", ["ответ"]),
]

def extract_inn_tokens(raw: str) -> list[str]:
    """Найти в строке все похожие на ИНН числа (10 или 12 цифр)."""
    if not raw:
        return []
    return re.findall(r"\d{10,12}", str(raw))


@dataclass
class ContactRecord:
    row_number: int  # номер строки в исходном файле (для отображения/навигации)
    address_raw: str
    tc_name: str
    opf: str
    management_company: str
    inn_raw: str
    director_name: str
    phone: str
    email: str
    extra_info: str

    @property
    def inn_tokens(self) -> list[str]:
        return extract_inn_tokens(self.inn_raw)

    @property
    def has_multiple_inn(self) -> bool:
        return len(set(self.inn_tokens)) > 1

    @property
    def is_substantive(self) -> bool:
        """Есть ли в записи хоть какие-то положительные данные об УК (а не
        только адрес/примечание)."""
        return bool(
            (self.management_company or "").strip()
            or (self.inn_raw or "").strip()
            or (self.director_name or "").strip()
        )


def _cell_str(value) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def load_contacts(path: str, sheet_name: str | None = None) -> list[ContactRecord]:
    """Загрузить справочник контактов УК/ТЦ.

    Ищет лист "Лист 1" (как в образце); если не найден — берёт первый лист.
    Заголовки ожидаются в первой строке.
    """
    wb = openpyxl.load_workbook(path, data_only=True)
    if sheet_name and sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
    elif "Лист 1" in wb.sheetnames:
        ws = wb["Лист 1"]
    elif "Лист1" in wb.sheetnames:
        ws = wb["Лист1"]
    else:
        ws = wb.worksheets[0]

    col_by_key: dict[str, int] = {}
    for c in range(1, ws.max_column + 1):
        header = _norm_header(ws.cell(row=1, column=c).value)
        if not header:
            continue
        for key, prefixes in _HEADER_RULES:
            if key in col_by_key:
                continue
            if any(header.startswith(p) for p in prefixes):
                col_by_key[key] = c
                break

    if "address" not in col_by_key:
        raise ValueError(
            "В справочнике УК/ТЦ не найден столбец с адресом торгового "
            "объекта (заголовок должен начинаться с «Адрес»)."
        )

    def get(row: int, key: str) -> str:
        c = col_by_key.get(key)
        if not c:
            return ""
        return _cell_str(ws.cell(row=row, column=c).value)

    records: list[ContactRecord] = []
    for r in range(2, ws.max_row + 1):
        address_raw = get(r, "address")
        tc_name = get(r, "tc_name")
        extra_info = get(r, "extra_info")
        if not address_raw and not tc_name and not extra_info:
            continue
        records.append(
            ContactRecord(
                row_number=r,
                address_raw=address_raw,
                tc_name=tc_name,
                opf=get(r, "opf"),
                management_company=get(r, "management_company"),
                inn_raw=get(r, "inn"),
                director_name=get(r, "director_name"),
                phone=get(r, "phone"),
                email=get(r, "email"),
                extra_info=extra_info,
            )
        )
    return records


class MatchStatus(str, Enum):
    NOT_FOUND = "not_found"  # в справочнике нет записи с таким адресом
    OK = "ok"  # найдена ровно одна запись, всё однозначно
    AMBIGUOUS = "ambiguous"  # несколько разных строк на один адрес
    MULTIPLE_INN = "multiple_inn"  # в одной строке указано >1 ИНН


@dataclass
class MatchResult:
    status: MatchStatus
    records: list[ContactRecord] = field(default_factory=list)
    reason: str = ""

    @property
    def record(self) -> ContactRecord | None:
        """Единственная запись — только когда status == OK."""
        return self.records[0] if self.status == MatchStatus.OK and self.records else None


class ContactsIndex:
    """Индекс справочника УК/ТЦ по нормализованному адресу для быстрого
    поиска при генерации писем."""

    def __init__(self, records: list[ContactRecord]):
        self._by_address: dict[str, list[ContactRecord]] = {}
        for rec in records:
            key = building_key(rec.address_raw)
            if not key:
                continue
            self._by_address.setdefault(key, []).append(rec)

    def match(self, building_address: str) -> MatchResult:
        key = building_key(building_address)
        candidates = self._by_address.get(key, [])
        if not candidates:
            return MatchResult(status=MatchStatus.NOT_FOUND)

        if len(candidates) > 1:
            # ТЗ, раздел 9: автоматическое разрешение противоречивых/
            # неоднозначных записей (в т.ч. записей-примечаний об
            # "отменённой" УК) не реализуется — только пометка на ручную
            # проверку, независимо от того, что записи могут выглядеть
            # "явно одной актуальной + одной отменённой".
            return MatchResult(
                status=MatchStatus.AMBIGUOUS,
                records=candidates,
                reason=(
                    f"По адресу найдено {len(candidates)} строк(и) в "
                    "справочнике УК/ТЦ — требуется ручная проверка."
                ),
            )

        record = candidates[0]
        if record.has_multiple_inn:
            return MatchResult(
                status=MatchStatus.MULTIPLE_INN,
                records=[record],
                reason=(
                    "В строке справочника указано несколько ИНН "
                    f"({', '.join(sorted(set(record.inn_tokens)))}) — "
                    "требуется ручная проверка."
                ),
            )

        return MatchResult(status=MatchStatus.OK, records=[record])
