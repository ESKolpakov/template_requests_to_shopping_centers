"""Расчёт срока предоставления информации (ТЗ, п.4.3).

Срок = дата формирования письма + N календарных дней; если результат
выпадает на субботу/воскресенье или на праздничный/нерабочий день из
редактируемого списка — сдвигается на ближайший следующий рабочий день.
"""

from __future__ import annotations

import datetime

__all__ = [
    "DEFAULT_DEADLINE_DAYS",
    "default_holidays",
    "compute_deadline",
    "format_date_ru",
    "parse_date_ru",
]

DEFAULT_DEADLINE_DAYS = 14


def default_holidays(year: int) -> list[datetime.date]:
    """Базовый набор фиксированных праздников РФ для указанного года
    (см. ТЗ п.4.3). Это значение по умолчанию — фактический список
    праздников/переносов на конкретный год лучше брать из настроек
    приложения (редактируемый список), т.к. он утверждается отдельными
    постановлениями правительства и меняется год от года.
    """
    fixed = [
        (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
        (2, 23),
        (3, 8),
        (5, 1), (5, 9),
        (6, 12),
        (11, 4),
    ]
    return [datetime.date(year, m, d) for m, d in fixed]


def _is_business_day(d: datetime.date, holidays: set[datetime.date]) -> bool:
    return d.weekday() < 5 and d not in holidays  # 5=суббота, 6=воскресенье


def compute_deadline(
    start_date: datetime.date,
    days: int = DEFAULT_DEADLINE_DAYS,
    holidays: list[datetime.date] | None = None,
) -> datetime.date:
    """Дата = start_date + days календарных дней, со сдвигом на ближайший
    следующий рабочий день, если она попадает на выходной/праздник."""
    holidays_set = set(holidays or [])
    deadline = start_date + datetime.timedelta(days=days)
    while not _is_business_day(deadline, holidays_set):
        deadline += datetime.timedelta(days=1)
    return deadline


def format_date_ru(d: datetime.date) -> str:
    """ДД.ММ.ГГГГ — как в письмах-образцах."""
    return d.strftime("%d.%m.%Y")


def parse_date_ru(text: str) -> datetime.date:
    """Разобрать дату из строки в формате ДД.ММ.ГГГГ или ГГГГ-ММ-ДД
    (второй формат — для полей ввода/конфига)."""
    text = (text or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Не удалось разобрать дату: {text!r}")
