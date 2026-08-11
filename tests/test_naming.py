import datetime

from uktc_letters.naming import build_letter_filename, sanitize_filename_part


def test_sanitize_filename_part_replaces_spaces_and_commas():
    assert sanitize_filename_part("ул. Барклая, д.10А") == "ул._Барклая_д.10А"


def test_sanitize_filename_part_strips_invalid_chars():
    assert sanitize_filename_part('ТЦ "Вектор"') == "ТЦ_Вектор"


def test_build_letter_filename_with_tc_name():
    name = build_letter_filename("ул. Барклая, д.10А", "Фили", datetime.date(2026, 8, 5))
    assert name == "ул._Барклая_д.10А_ТЦ_Фили_05_08_2026.docx"


def test_build_letter_filename_without_tc_name():
    name = build_letter_filename("ул. Сормовская, д.6", "", datetime.date(2026, 8, 5))
    assert name == "ул._Сормовская_д.6_05_08_2026.docx"
