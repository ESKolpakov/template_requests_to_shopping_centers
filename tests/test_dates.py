import datetime

from uktc_letters.dates import compute_deadline, default_holidays, format_date_ru, parse_date_ru


def test_compute_deadline_business_day_no_shift():
    # 2026-07-01 (среда) + 14 = 2026-07-15 (среда) — рабочий день, без сдвига.
    start = datetime.date(2026, 7, 1)
    result = compute_deadline(start, 14, [])
    assert result == datetime.date(2026, 7, 15)


def test_compute_deadline_shifts_from_saturday():
    # +14 дней от четверга 2026-08-13 = четверг 2026-08-27... подберём дату,
    # которая явно попадает на выходной.
    start = datetime.date(2026, 7, 18)  # суббота
    result = compute_deadline(start, 14, [])
    # 18 июля 2026 + 14 = 1 августа 2026 (суббота) -> сдвиг на понедельник 3 августа.
    assert result.weekday() < 5
    assert result >= datetime.date(2026, 8, 1)


def test_compute_deadline_shifts_over_holiday():
    start = datetime.date(2025, 12, 18)  # +14 = 2026-01-01 (праздник)
    holidays = default_holidays(2026)
    result = compute_deadline(start, 14, holidays)
    assert result not in set(holidays)
    assert result.weekday() < 5
    assert result > datetime.date(2026, 1, 1)


def test_default_holidays_contains_fixed_dates():
    holidays = default_holidays(2027)
    assert datetime.date(2027, 1, 1) in holidays
    assert datetime.date(2027, 5, 9) in holidays
    assert datetime.date(2027, 3, 8) in holidays


def test_format_and_parse_date_ru_roundtrip():
    d = datetime.date(2026, 8, 18)
    assert format_date_ru(d) == "18.08.2026"
    assert parse_date_ru("18.08.2026") == d
    assert parse_date_ru("2026-08-18") == d
