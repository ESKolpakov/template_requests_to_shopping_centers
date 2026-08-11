"""Парсер PDF-выписок из ЕГРЮЛ (см. ТЗ, раздел 6).

Важно: этот модуль НЕ обращается к egrul.nalog.ru и не проходит капчу —
он только разбирает уже скачанный пользователем PDF-файл (текстовый слой,
не OCR). Автоматизация ограничивается подстановкой ИНН в форму поиска
(см. `egrul_search_url`) и разбором готового файла.

Формат выписки стабилен в начале документа (структура полей идентична у
разных организаций), а дальше идёт история записей ЕГРЮЛ переменной
длины — поэтому весь нужный блок ищется по тексту меток (заголовков
полей), а не по фиксированному номеру страницы/пункта.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

__all__ = [
    "EgrulData",
    "egrul_search_url",
    "parse_egrul_pdf",
    "find_latest_egrul_pdf",
]


def egrul_search_url(inn: str) -> str:
    """URL страницы поиска ЕГРЮЛ с ИНН, который можно подставить в поле
    поиска (открывается в браузере пользователя — см. ТЗ п.6.1)."""
    return f"https://egrul.nalog.ru/index.html?query={inn}"


@dataclass
class EgrulData:
    inn: str | None = None
    full_name: str | None = None
    short_name: str | None = None
    legal_address: str | None = None

    # Лицо, имеющее право без доверенности действовать от имени юр. лица:
    representative_surname: str | None = None
    representative_first_name: str | None = None
    representative_patronymic: str | None = None
    representative_position: str | None = None
    representative_gender: str | None = None  # "male" / "female" / None
    # Если лицо, имеющее право действовать без доверенности, — не физлицо,
    # а другая организация (см. ТЗ п.6, отдельный кейс):
    representative_org_name: str | None = None

    @property
    def representative_is_organization(self) -> bool:
        return bool(self.representative_org_name) and not self.representative_surname


def _clean(text: str | None) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    # Артефакт переноса строки в заголовке "... на русском\nязыке" —
    # хвостовое слово "языке" иногда попадает в конец значения при
    # построчном извлечении текста.
    text = re.sub(r"\s*языке\s*$", "", text, flags=re.IGNORECASE)
    return text


def _value_after(text: str, label: str, stop_labels: tuple[str, ...] = ()) -> str | None:
    """Извлечь значение поля, следующее в тексте после метки `label`, до
    первой из `stop_labels` либо до начала следующего пронумерованного
    пункта выписки (строка вида "12 Заголовок...")."""
    idx = text.find(label)
    if idx == -1:
        return None
    start = idx + len(label)
    end = len(text)
    for stop in stop_labels:
        j = text.find(stop, start)
        if j != -1 and j < end:
            end = j
    m = re.search(r"\n\s*\d{1,3}\s+[А-ЯЁ]", text[start : end + 120])
    if m:
        candidate_end = start + m.start()
        if candidate_end < end:
            end = candidate_end
    return _clean(text[start:end])


def _section(text: str, start_markers: tuple[str, ...], end_markers: tuple[str, ...]) -> str | None:
    for marker in start_markers:
        idx = text.find(marker)
        if idx != -1:
            start = idx + len(marker)
            end = len(text)
            for em in end_markers:
                j = text.find(em, start)
                if j != -1 and j < end:
                    end = j
            return text[start:end]
    return None


_REP_SECTION_MARKERS = (
    "Сведения о лице, имеющем право без доверенности действовать от имени "
    "юридического\nлица",
    "Сведения о лице, имеющем право без доверенности действовать от имени "
    "юридического лица",
)
_REP_SECTION_END_MARKERS = (
    "Сведения об уставном капитале",
    "Сведения об участниках",
    "Сведения о видах",
)

_GENDER_MAP = {"женский": "female", "мужской": "male"}


def parse_egrul_text(text: str) -> EgrulData:
    """Разобрать уже извлечённый текстовый слой выписки (используется и в
    парсере PDF, и в тестах — на синтетическом тексте той же структуры)."""
    data = EgrulData()

    data.full_name = _value_after(text, "Полное наименование на русском языке")
    data.short_name = _value_after(text, "Сокращенное наименование на русском")
    data.legal_address = _value_after(
        text, "Адрес юридического лица", ("Сведения о регистрации",)
    )
    data.inn = _value_after(text, "ИНН юридического лица", ("КПП",))

    rep_section = _section(text, _REP_SECTION_MARKERS, _REP_SECTION_END_MARKERS)
    if rep_section:
        surname = _value_after(rep_section, "Фамилия", ("Имя",))
        first_name = _value_after(rep_section, "Имя", ("Отчество",))
        patronymic = _value_after(rep_section, "Отчество")
        position = _value_after(rep_section, "Должность")
        gender_raw = _value_after(rep_section, "Пол")

        if surname:
            data.representative_surname = surname
            data.representative_first_name = first_name
            data.representative_patronymic = patronymic
            data.representative_position = position
            data.representative_gender = _GENDER_MAP.get((gender_raw or "").lower())
        else:
            # Лицо, имеющее право действовать без доверенности, — другая
            # организация (управляющая компания), а не физлицо: ФИО в
            # блоке нет, вместо него — наименование юрлица.
            org_name = _value_after(
                rep_section, "Наименование", ("ГРН",)
            ) or _value_after(rep_section, "Полное наименование", ("ГРН",))
            data.representative_org_name = org_name
            data.representative_position = position

    return data


def parse_egrul_pdf(path: str, max_pages: int = 6) -> EgrulData:
    """Разобрать PDF-файл выписки из ЕГРЮЛ.

    `max_pages` ограничивает количество читаемых страниц: нужный блок
    полей всегда находится в начале выписки (первые 2-3 страницы), а
    дальше идёт история записей переменной длины (у разных организаций —
    разное число страниц, см. ТЗ п.6) — читать её незачем и медленно.
    """
    import pdfplumber

    with pdfplumber.open(path) as pdf:
        n = min(max_pages, len(pdf.pages))
        texts = [pdf.pages[i].extract_text() or "" for i in range(n)]
    text = "\n".join(texts)
    return parse_egrul_text(text)


_FILENAME_INN_HINT_RE = re.compile(r"(\d{10,15})")


def find_latest_egrul_pdf(directory: str, inn: str | None = None) -> str | None:
    """Найти самый свежий PDF в папке загрузок браузера, по возможности
    сверяясь по ИНН (внутри самого файла, а не только по имени — см. ТЗ
    п.6.3, имя файла ЕГРЮЛ содержит ОГРН и таймстамп, не ИНН напрямую).

    Возвращает путь к файлу или None, если подходящих файлов не найдено.
    Отсортированные по mtime кандидаты проверяются по содержимому: если
    `inn` указан, возвращается первый файл, у которого ИНН внутри PDF
    совпадает; иначе — просто самый свежий PDF в папке.
    """
    import os

    if not os.path.isdir(directory):
        return None

    candidates = [
        os.path.join(directory, name)
        for name in os.listdir(directory)
        if name.lower().endswith(".pdf")
    ]
    candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)

    if not inn:
        return candidates[0] if candidates else None

    for path in candidates:
        try:
            data = parse_egrul_pdf(path, max_pages=2)
        except Exception:
            continue
        if data.inn and data.inn.strip() == inn.strip():
            return path
    return None
