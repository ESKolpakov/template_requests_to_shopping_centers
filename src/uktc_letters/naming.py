"""Формирование имени файла итогового письма (ТЗ, п.8):
"адрес + (опционально) «ТЦ» + название + дата формирования", например
`улица_Барклая_дом_10А_ТЦ_Фили_05_08_2026.docx`.
"""

from __future__ import annotations

import datetime
import re

__all__ = ["sanitize_filename_part", "build_letter_filename"]

_INVALID_WIN_CHARS_RE = re.compile(r'[\\/:*?"<>|]')


def sanitize_filename_part(text: str) -> str:
    """Заменить пробелы/запятые на "_" и убрать символы, недопустимые в
    именах файлов Windows."""
    text = (text or "").strip()
    text = _INVALID_WIN_CHARS_RE.sub("", text)
    text = re.sub(r"[,\s]+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text.strip("_")


def build_letter_filename(
    address_display: str, tc_name: str, formation_date: datetime.date
) -> str:
    date_part = formation_date.strftime("%d_%m_%Y")
    address_part = sanitize_filename_part(address_display)
    parts = [address_part]
    if tc_name and tc_name.strip():
        parts.append("ТЦ")
        parts.append(sanitize_filename_part(tc_name))
    parts.append(date_part)
    return "_".join(p for p in parts if p) + ".docx"
