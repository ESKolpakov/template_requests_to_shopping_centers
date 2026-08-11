"""Работа с адресами: нормализация для сопоставления/группировки и
формирование "красивого" отображаемого адреса для письма.

Все функции этого модуля переиспользуются в нескольких местах приложения
(группировка объектов торговли, сопоставление со справочником УК/ТЦ,
модуль проверки по ЕГРЮЛ) — поэтому их поведение зафиксировано юнит-тестами
в tests/test_addresses.py.

Особенность реальных данных (см. ТЗ, п.3.2): один и тот же адрес в выгрузке
АИС ОПН и в справочнике УК/ТЦ может быть записан в разном порядке слов
("улица Барклая" против "Вешняковская улица") и с разным набором
сокращений/префиксов ("дом 15А" против просто "15А"). Поэтому сопоставление
адресов реализовано не как сравнение нормализованных СТРОК, а как сравнение
НАБОРОВ значимых токенов (тип+номер дома/корпуса/строения и слова названия
улицы) — это устойчиво к перестановке слов и различиям в сокращениях.
"""

from __future__ import annotations

import re

__all__ = [
    "split_room",
    "normalize_address",
    "building_key",
    "format_address_for_letter",
]


_ROOM_SPLIT_RE = re.compile(r",\s*комнат[аы]?\b.*$", re.IGNORECASE | re.DOTALL)


def split_room(raw_address: str) -> tuple[str, str]:
    """Отделить хвост ", комната ..." от адреса здания.

    Возвращает (адрес_здания, часть_после_"комната"_или_пустая_строка).
    Часть после "комната" по ТЗ (п.3.1) не используется — дублирует
    столбец "№ квартиры (офиса)".
    """
    if raw_address is None:
        return "", ""
    text = str(raw_address).strip()
    m = _ROOM_SPLIT_RE.search(text)
    if not m:
        return text.strip(" ,"), ""
    building = text[: m.start()].strip(" ,")
    room = text[m.start() :].strip(" ,")
    return building, room


# Ведущие уточнения места (район/округ/город) отбрасываются ЦЕЛИКОМ вместе
# со своим содержимым (названием района и т.п.) — в двух источниках они
# пишутся по-разному или отсутствуют вовсе и не идентифицируют здание.
_LEADING_CLAUSE_PATTERNS = [
    re.compile(r"^\s*район\s+[^,]+,\s*", re.IGNORECASE),
    re.compile(r"^\s*(муниципальный\s+)?округ\s+[^,]+,\s*", re.IGNORECASE),
    re.compile(r"^\s*административный\s+округ[^,]*,\s*", re.IGNORECASE),
    re.compile(r"^\s*[а-яё]{2,6}ао,\s*", re.IGNORECASE),  # ВАО, ЗАО, ЗелАО...
    re.compile(r"^\s*г(?:ор(?:од)?)?\.?\s*москв[аы],\s*", re.IGNORECASE),
    re.compile(r"^\s*москв[аы],\s*", re.IGNORECASE),
    re.compile(r"^\s*зеленоград,\s*", re.IGNORECASE),
]

# Слова-указатели типа адресного объекта — отбрасываются целиком: они несут
# смысл только в паре с последующим числом, а само число уже уникально
# идентифицирует дом/корпус/строение в пределах улицы.
_TYPE_WORDS = {
    "улица", "ул", "проспект", "пр-т", "прт", "пр-кт", "проезд", "пр-д",
    "переулок", "пер", "шоссе", "ш", "площадь", "пл", "бульвар", "б-р", "бр",
    "набережная", "наб", "аллея", "тупик", "квартал", "мкр", "микрорайон",
    "дом", "д", "корпус", "корп", "кор", "к", "строение", "стр", "с",
    "владение", "вл", "литера", "лит",
    "помещение", "пом",
}

_WORD_RE = re.compile(r"[а-яёa-z0-9]+", re.IGNORECASE)


def _strip_leading_clauses(text: str) -> str:
    for _ in range(5):
        changed = False
        for pattern in _LEADING_CLAUSE_PATTERNS:
            new_text = pattern.sub("", text)
            if new_text != text:
                text = new_text
                changed = True
        if not changed:
            break
    return text


def _content_tokens(text: str) -> list[str]:
    text = text.lower().replace("ё", "е")
    text = _strip_leading_clauses(text)
    tokens = _WORD_RE.findall(text)
    return [t for t in tokens if t not in _TYPE_WORDS]


def normalize_address(raw_address: str) -> str:
    """Нормализовать адрес здания для СОПОСТАВЛЕНИЯ (не для отображения).

    Возвращает строку из отсортированных значимых токенов (название улицы,
    номера дома/корпуса/строения), разделённых пробелом — она устойчива к
    перестановке слов и различию в сокращениях между источниками.
    """
    if raw_address is None:
        return ""
    building, _room = split_room(str(raw_address))
    tokens = _content_tokens(building)
    return " ".join(sorted(tokens))


def building_key(raw_address: str) -> str:
    """Ключ группировки объектов торговли в одно письмо — нормализованный
    адрес здания (без "комната ...")."""
    return normalize_address(raw_address)


_DISPLAY_REPLACEMENTS = [
    (re.compile(r"\bулица\b", re.IGNORECASE), "ул."),
    (re.compile(r"\bпроспект\b", re.IGNORECASE), "пр-т"),
    (re.compile(r"\bпереулок\b", re.IGNORECASE), "пер."),
    (re.compile(r"\bшоссе\b", re.IGNORECASE), "ш."),
    (re.compile(r"\bплощадь\b", re.IGNORECASE), "пл."),
    (re.compile(r"\bбульвар\b", re.IGNORECASE), "б-р"),
    (re.compile(r"\bнабережная\b", re.IGNORECASE), "наб."),
    (re.compile(r"\bпроезд\b", re.IGNORECASE), "пр-д"),
]

_DOM_RE = re.compile(r"\bдом\s+", re.IGNORECASE)
_KORP_RE = re.compile(r"\bкорпус\s+", re.IGNORECASE)
_STR_RE = re.compile(r"\bстроение\s+", re.IGNORECASE)
_LEADING_DISTRICT_DISPLAY_RE = re.compile(
    r"^\s*район\s+[^,]+,\s*", re.IGNORECASE
)


def format_address_for_letter(raw_address: str) -> str:
    """Привести адрес здания к виду, принятому в письмах-образцах:
    "ул. Барклая, д.10А", "пр-т Мира, д.211, корп.2" и т.д.

    Это ФОРМАТИРОВАНИЕ ДЛЯ ОТОБРАЖЕНИЯ, а не для сопоставления — исходный
    порядок слов в названии улицы сохраняется как есть (кроме известных
    сокращений вида "улица"->"ул.", "дом"->"д."). Единственное известное
    исключение из образцов — инверсия порядка в адресах с числительным
    в начале названия улицы (например, "Парковая 9-я улица" ->
    "9-я Парковая") — переупорядочивание НЕ выполняется автоматически,
    это можно поправить вручную в интерфейсе перед генерацией.
    """
    building, _room = split_room(raw_address)
    text = building.strip()
    text = _LEADING_DISTRICT_DISPLAY_RE.sub("", text)
    for pattern, canon in _DISPLAY_REPLACEMENTS:
        text = pattern.sub(canon, text)
    text = _DOM_RE.sub("д.", text)
    text = _KORP_RE.sub("корп.", text)
    text = _STR_RE.sub("стр.", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text
