"""Морфология: склонение ФИО в дательный падеж для адресного блока,
определение пола по отчеству, словарь дательных форм типовых должностей
(см. ТЗ, раздел 4.1).

Склонение выполняется через pymorphy3. На редких/иностранных ФИО (пример
из ТЗ — «Гулиев Гулам Билал Оглы») склонение может ошибаться — это
ожидаемо и ТЗ прямо требует показывать результат пользователю на экране
предпросмотра для ручной проверки, а не сохранять втихую (см.
`InflectionResult.low_confidence`).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

__all__ = [
    "Gender",
    "InflectionResult",
    "guess_gender_by_patronymic",
    "inflect_dative",
    "format_dative_initials_surname",
    "format_full_name",
    "position_to_dative",
]

Gender = str  # "male" | "female" | None


@lru_cache(maxsize=1)
def _morph():
    # Импорт и инициализация MorphAnalyzer небыстрые — делаем один раз лениво,
    # чтобы не тормозить запуск приложения, если склонение не понадобится
    # (например, письмо обезличенное).
    import pymorphy3

    return pymorphy3.MorphAnalyzer()


# Типичные окончания женских/мужских отчеств (для случая, когда данные
# пришли из справочника УК/ТЦ без явного поля "Пол" — там оно есть только
# в выписке ЕГРЮЛ).
_FEMALE_PATRONYMIC_ENDINGS = ("вна", "чна", "ична")
_MALE_PATRONYMIC_ENDINGS = ("вич", "ич", "ыч")


def guess_gender_by_patronymic(patronymic: str) -> Gender:
    """Определить пол по окончанию отчества. Возвращает "male"/"female"/None."""
    if not patronymic:
        return None
    p = patronymic.strip().lower()
    if p.endswith(_FEMALE_PATRONYMIC_ENDINGS):
        return "female"
    if p.endswith(_MALE_PATRONYMIC_ENDINGS):
        return "male"
    return None


_GENDER_TO_TAG = {"male": "masc", "female": "femn"}


@dataclass
class InflectionResult:
    original: str
    inflected: str
    low_confidence: bool  # True, если морфология "гадала" (не нашла слово в словаре)


def inflect_dative(word: str, gender: Gender = None) -> InflectionResult:
    """Просклонять одно слово (фамилию/имя/отчество) в дательный падеж.

    Если известен пол — выбирается разбор pymorphy, согласованный с полом
    (иначе, например, фамилия «Лекомцева» по умолчанию разбирается как
    родительный падеж мужской фамилии «Лекомцев» и склоняется неверно).
    """
    word = (word or "").strip()
    if not word:
        return InflectionResult(original=word, inflected=word, low_confidence=True)

    parses = _morph().parse(word)
    if not parses:
        return InflectionResult(original=word, inflected=word, low_confidence=True)

    chosen = None
    if gender in _GENDER_TO_TAG:
        tag = _GENDER_TO_TAG[gender]
        for p in parses:
            if tag in p.tag:
                chosen = p
                break
    if chosen is None:
        chosen = parses[0]

    # low_confidence: pymorphy не опознал слово как имя/фамилию/отчество
    # (тег не содержит Name/Surn/Patr) — типичный случай иностранных ФИО.
    tag_str = str(chosen.tag)
    low_confidence = not any(g in tag_str for g in ("Name", "Surn", "Patr"))

    inflected = chosen.inflect({"datv"})
    result_word = inflected.word if inflected else word

    # Сохраняем регистр первой буквы, как в оригинале (ФИО обычно приходят
    # с заглавной буквы или капсом — приводим результат к варианту
    # "Заглавная+строчные").
    result_word = result_word.capitalize() if result_word else result_word
    return InflectionResult(original=word, inflected=result_word, low_confidence=low_confidence)


def format_dative_initials_surname(
    surname: str, first_name: str, patronymic: str, gender: Gender = None
) -> tuple[str, bool]:
    """Собрать «И.О.Фамилия» в дательном падеже, как в адресном блоке
    образцов ("С.М.Лекомцевой"). Возвращает (строка, low_confidence)."""
    surname_res = inflect_dative(surname, gender)
    first_initial = (first_name or "").strip()[:1].upper()
    patr_initial = (patronymic or "").strip()[:1].upper()
    text = f"{first_initial}.{patr_initial}.{surname_res.inflected}"
    low_confidence = surname_res.low_confidence
    return text, low_confidence


def format_full_name(first_name: str, patronymic: str) -> str:
    """«Имя Отчество» в именительном падеже для приветствия
    ("Уважаемая Светлана Михайловна!")."""

    def cap(word: str) -> str:
        word = (word or "").strip()
        return word.capitalize() if word else word

    return f"{cap(first_name)} {cap(patronymic)}".strip()


# Словарь типовых должностей -> дательный падеж (ТЗ п.4.1). Ключи —
# нормализованные (нижний регистр, без лишних пробелов) варианты написания,
# которые встречаются в выписках ЕГРЮЛ (поле "Должность") и в справочнике.
_POSITION_DATIVE: dict[str, str] = {
    "генеральный директор": "Генеральному директору",
    "директор": "Директору",
    "исполнительный директор": "Исполнительному директору",
    "управляющий": "Управляющему",
    "управляющая": "Управляющей",
    "президент": "Президенту",
    "председатель правления": "Председателю правления",
    "индивидуальный предприниматель": "ИП",
    "ип": "ИП",
}

_FALLBACK_POSITION = "Руководителю"


def position_to_dative(raw_position: str | None) -> str:
    """Привести должность к дательному падежу по словарю типовых
    должностей; для нераспознанных — запасной вариант «Руководителю»
    (см. ТЗ п.4.1)."""
    if not raw_position:
        return _FALLBACK_POSITION
    key = " ".join(raw_position.strip().lower().split())
    return _POSITION_DATIVE.get(key, _FALLBACK_POSITION)
