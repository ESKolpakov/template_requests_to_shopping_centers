"""Мелкое форматирование текстовых полей для адресного блока письма:
разбор ФИО, приведение названия организации и юридического адреса к
"человеческому" виду (как в образцах писем), а не как они хранятся в
выписке ЕГРЮЛ (КАПС) или в справочнике (произвольный регистр/формат).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "split_fio",
    "format_company_name",
    "format_legal_address",
    "DirectorField",
    "parse_director_field",
    "clean_tc_name",
]

_LEGAL_FORM_ABBR = [
    (re.compile(r"^публичное акционерное общество\b", re.IGNORECASE), "ПАО"),
    (re.compile(r"^закрытое акционерное общество\b", re.IGNORECASE), "ЗАО"),
    (re.compile(r"^открытое акционерное общество\b", re.IGNORECASE), "ОАО"),
    (re.compile(r"^акционерное общество\b", re.IGNORECASE), "АО"),
    (re.compile(r"^общество с ограниченной ответственностью\b", re.IGNORECASE), "ООО"),
    (re.compile(r"^государственное бюджетное учреждение\b", re.IGNORECASE), "ГБУ"),
    (re.compile(r"^индивидуальный предприниматель\b", re.IGNORECASE), "ИП"),
]

_QUOTED_RE = re.compile(r'["«]([^"»]+)["»]')


def split_fio(full_name: str) -> tuple[str, str, str] | None:
    """Разбить "Фамилия Имя Отчество" на 3 части. Возвращает None, если
    строка не раскладывается ровно на 3 слова (например, это название
    организации, а не ФИО физлица, либо отчество не указано) — в таком
    случае персональный вариант адресата строить не из чего, см.
    letters.py."""
    if not full_name:
        return None
    parts = full_name.split()
    if len(parts) != 3:
        return None
    return parts[0], parts[1], parts[2]


_ORG_REPRESENTATIVE_RE = re.compile(
    r"^(управляющ\w*\s+организаци\w*|УК)\s*[:\-—]\s*(?P<org>.+)$", re.IGNORECASE
)

_POSITION_PREFIX_RE = re.compile(
    r"^(?P<pos>генеральный\s+директор|исполнительный\s+директор|"
    r"директор|управляющ\w+|президент|председатель\s+правления|"
    r"руководитель)\s*[:\n]?\s*",
    re.IGNORECASE,
)


@dataclass
class DirectorField:
    position_raw: str | None = None
    fio: str | None = None  # "Фамилия Имя Отчество", если распозналось
    organization_name: str | None = None  # если это не физлицо, а организация


def parse_director_field(raw: str) -> "DirectorField":
    """Разобрать поле "Руководитель управляющей компании" справочника
    УК/ТЦ — на практике оно неоднородно (ТЗ п.3.2: "заполненность полей
    неоднородна"): просто "Фамилия Имя Отчество", "ДОЛЖНОСТЬ: Фамилия Имя
    Отчество" (в одну строку или через перенос), "Управляющая
    организация: ООО «Х»" (лицо, действующее от имени УК, — само
    организация, не физлицо), либо непригодный для разбора текст
    (примечание вида "объект закрыт")."""
    raw = (raw or "").strip()
    if not raw:
        return DirectorField()

    m = _ORG_REPRESENTATIVE_RE.match(raw)
    if m:
        return DirectorField(organization_name=m.group("org").strip())

    position_raw = None
    rest = raw
    m = _POSITION_PREFIX_RE.match(raw)
    if m:
        position_raw = m.group("pos").strip()
        rest = raw[m.end() :].strip()

    fio_tuple = split_fio(rest)
    if fio_tuple is None:
        return DirectorField(position_raw=position_raw)
    return DirectorField(position_raw=position_raw, fio=" ".join(fio_tuple))


def format_company_name(raw_name: str, opf_hint: str | None = None) -> str:
    """Привести название организации к виду «ООО «Название»» (как в
    образцах писем), независимо от того, пришло ли оно полной формой из
    ЕГРЮЛ/справочника («ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "Х"») или
    просто как голое название с известной организационно-правовой формой
    из соседнего столбца справочника."""
    raw_name = (raw_name or "").strip()
    if not raw_name:
        return ""

    for pattern, abbr in _LEGAL_FORM_ABBR:
        if pattern.search(raw_name):
            rest = pattern.sub("", raw_name).strip()
            m = _QUOTED_RE.search(rest)
            bare = m.group(1) if m else rest
            return f"{abbr} «{bare}»"

    m = _QUOTED_RE.search(raw_name)
    if m:
        prefix = raw_name[: m.start()].strip()
        bare = m.group(1)
        if prefix:
            return f"{prefix} «{bare}»"
        if opf_hint:
            return f"{opf_hint.strip()} «{bare}»"
        return f"«{bare}»"

    # Голое название без кавычек и без ОПФ в самой строке.
    if opf_hint:
        return f"{opf_hint.strip()} «{raw_name}»"
    return raw_name


_NUMERIC_TOKEN_RE = re.compile(r"^\d")
_LOWERCASE_WORDS = {"область", "район", "край", "город"}


_TC_PREFIX_RE = re.compile(
    r"^(ТРЦ|ТРК|ТЦ|ТК|Торгово-развлекательный\s+центр|Торговый\s+центр)\.?\s+",
    re.IGNORECASE,
)
_TC_QUOTES_RE = re.compile(r'^["«\'“](.+)["»\'”]$')


def clean_tc_name(raw_tc_name: str) -> str:
    """Убрать из названия ТЦ служебный префикс ("ТЦ"/"ТК"/"Торговый
    центр") и обрамляющие кавычки — в справочнике название хранится
    по-разному ("ТК Фили", "ТЦ Фили", просто "Европолис"), а в тексте
    письма и в имени файла используется голое название (плейсхолдер
    {{TC_NAME}} в шаблоне уже стоит в контексте "в торговом центре
    «...»", а имя файла собирает свой префикс "ТЦ" самостоятельно —
    см. naming.py)."""
    name = (raw_tc_name or "").strip()
    if not name:
        return ""
    name = _TC_PREFIX_RE.sub("", name).strip()
    m = _TC_QUOTES_RE.match(name)
    if m:
        name = m.group(1).strip()
    return name


def format_legal_address(raw: str) -> str:
    """Причесать адрес из выписки ЕГРЮЛ (обычно КАПСОМ) в читаемый вид:
    "г. Видное, ул. Ольховая, д. 9" вместо "Г. ВИДНОЕ, УЛ. ОЛЬХОВАЯ, Д. 9".
    Косметическая функция, не влияет на сопоставление/группировку адресов."""
    if not raw:
        return ""
    segments = [s.strip() for s in raw.split(",") if s.strip()]
    out_segments = []
    for seg in segments:
        words = seg.split()
        new_words = []
        for w in words:
            if _NUMERIC_TOKEN_RE.match(w):
                new_words.append(w)
            elif w.endswith(".") or w.lower() in _LOWERCASE_WORDS:
                new_words.append(w.lower())
            else:
                new_words.append(w.capitalize())
        out_segments.append(" ".join(new_words))
    return ", ".join(out_segments)
