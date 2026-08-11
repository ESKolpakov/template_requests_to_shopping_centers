"""Оркестрация формирования одного письма по зданию: определение адресата
(персональный/обезличенный вариант, ТЗ п.4.1), расчёт словоформ по числу
хозяйствующих субъектов (п.4.2), расчёт срока (п.4.3), сборка плейсхолдеров
и строк таблицы-приложения, имя файла.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum

from .addresses import format_address_for_letter
from .config import Settings
from .contacts_source import ContactRecord, ContactsIndex, MatchResult, MatchStatus
from .dates import compute_deadline, format_date_ru
from .docx_template import RowSpec, build_row_specs
from .egrul_parser import EgrulData
from .formatting import (
    clean_tc_name,
    format_company_name,
    format_legal_address,
    parse_director_field,
)
from .morphology import (
    format_dative_initials_surname,
    format_full_name,
    guess_gender_by_patronymic,
    position_to_dative,
)
from .naming import build_letter_filename
from .objects_source import BuildingGroup

__all__ = [
    "LetterStatus",
    "LetterPlan",
    "plan_letter",
]


class LetterStatus(str, Enum):
    AUTO_PERSONAL = "auto_personal"      # ТЗ п.8: "сформировано автоматически"
    AUTO_IMPERSONAL = "auto_impersonal"  # ТЗ п.8: "сформировано в обезличенном виде"
    MANUAL_REVIEW = "manual_review"      # ТЗ п.8: "не удалось определить УК"


def _number_forms(is_plural: bool) -> dict[str, str]:
    """Словоформы по числу хозяйствующих субъектов (ТЗ п.4.2). Помимо
    буквального плейсхолдера {{SUBJECT_WORD_FORM}} из ТЗ (сопоставлен с
    формой "хозяйствующем субъекте"/"хозяйствующих субъектах" — именно
    этот пример приведён в самом ТЗ), для остальных переменных мест по
    тексту письма, обнаруженных при построчном сравнении образцов
    (ул.Барклая — ед.ч., ул.Матвеевская,д.2 — мн.ч.), выведен отдельный
    набор токенов, которые можно расставить по тексту шаблона."""
    if not is_plural:
        return {
            "SUBJECT_WORD_FORM": "хозяйствующем субъекте",
            "VERB_OSUSHESTVLYAL": "осуществлял",
            "OBJECT_WORD": "объекта",
            "TRADE_OBJECT_PHRASE": "торгового объекта",
            "SUBJECT_NOM": "хозяйствующий субъект",
            "SUBJECT_PREP": "хозяйствующем субъекте",
            "UKAZANNYY": "указанный",
            "OSUSHESTVLYAVSHIY": "осуществлявшем",
            "SUBJECT_CLAUSE": "осуществлял хозяйствующий субъект, указанный",
            "SUBJECT_PREP_CLAUSE": "хозяйствующем субъекте, осуществлявшем",
        }
    return {
        "SUBJECT_WORD_FORM": "хозяйствующих субъектах",
        "VERB_OSUSHESTVLYAL": "осуществляли",
        "OBJECT_WORD": "объектов",
        "TRADE_OBJECT_PHRASE": "торговых объектов",
        "SUBJECT_NOM": "хозяйствующие субъекты",
        "SUBJECT_PREP": "хозяйствующих субъектах",
        "UKAZANNYY": "указанные",
        "OSUSHESTVLYAVSHIY": "осуществлявших",
        "SUBJECT_CLAUSE": "осуществляли хозяйствующие субъекты, указанные",
        "SUBJECT_PREP_CLAUSE": "хозяйствующих субъектах, осуществлявших",
    }


@dataclass
class LetterPlan:
    building_group: BuildingGroup
    status: LetterStatus
    status_reason: str
    variant: str  # "personal" | "impersonal"
    tc_name: str
    address_display: str
    context: dict[str, str]
    row_specs: list[RowSpec]
    filename: str
    low_confidence_inflection: bool = False
    contact_match: MatchResult | None = None


def _build_personal_block(
    surname: str,
    first_name: str,
    patronymic: str,
    gender: str | None,
    position_raw: str | None,
    company_display: str,
    address_display: str,
) -> tuple[list[str], list[str], str, bool]:
    """Вернуть (строки должность/УК/ФИО, строки адреса, приветствие,
    low_confidence).

    Раздельно на две группы строк — а не одним списком — потому что в
    образцах писем эти две части адресного блока набраны с РАЗНЫМ отступом
    (должность/УК/ФИО — одним уровнем, юридический адрес — увеличенным,
    "лесенкой") — см. `docx_template`/шаблон, где это два разных абзаца
    с разными `{{RECIPIENT_BLOCK_MAIN}}`/`{{RECIPIENT_BLOCK_ADDRESS}}`.
    """
    if gender is None:
        gender = guess_gender_by_patronymic(patronymic)

    fio_dative, low_conf = format_dative_initials_surname(surname, first_name, patronymic, gender)
    greeting_name = format_full_name(first_name, patronymic)
    greeting_word = "Уважаемая" if gender == "female" else "Уважаемый"
    greeting = f"{greeting_word} {greeting_name}!" if greeting_name.strip() else ""

    main_lines = [position_to_dative(position_raw), company_display, fio_dative]
    address_lines = [address_display] if address_display else []
    return main_lines, address_lines, greeting, low_conf


def _resolve_personal_variant(
    record: ContactRecord, egrul: EgrulData | None
) -> tuple[list[str], list[str], str, bool] | None:
    """Попытаться собрать персональный адресный блок из данных ЕГРЮЛ
    (приоритетно, т.к. они точнее и содержат пол/должность) либо из
    справочника УК/ТЦ. Возвращает None, если данных недостаточно —
    письмо в этом случае формируется в обезличенном виде."""
    if egrul is not None:
        if egrul.representative_is_organization:
            # ТЗ п.6: лицо, имеющее право действовать без доверенности, —
            # другая организация, а не физлицо. Подставляем как есть, без
            # попытки определить "Уважаемый/Уважаемая".
            company_display = format_company_name(egrul.short_name or egrul.full_name or "")
            main_lines = [
                position_to_dative(egrul.representative_position),
                company_display,
                egrul.representative_org_name or "",
            ]
            legal_address = format_legal_address(egrul.legal_address or "")
            address_lines = [legal_address] if legal_address else []
            return main_lines, address_lines, "", False
        if egrul.representative_surname:
            company_display = format_company_name(egrul.short_name or egrul.full_name or "")
            return _build_personal_block(
                egrul.representative_surname,
                egrul.representative_first_name or "",
                egrul.representative_patronymic or "",
                egrul.representative_gender,
                egrul.representative_position,
                company_display,
                format_legal_address(egrul.legal_address or ""),
            )

    director = parse_director_field(record.director_name)
    company_display = format_company_name(record.management_company, record.opf)

    if director.organization_name:
        # Лицо, действующее от имени УК без доверенности, — тоже
        # организация (например, "Управляющая организация: ООО «Х»"), а не
        # физлицо — без попытки определить "Уважаемый/Уважаемая" (по
        # аналогии с тем же случаем в выписке ЕГРЮЛ, ТЗ п.6).
        main_lines = [
            position_to_dative(director.position_raw),
            company_display,
            director.organization_name,
        ]
        return main_lines, [], "", False

    if director.fio is None:
        return None

    surname, first_name, patronymic = director.fio.split()
    position_raw = director.position_raw
    if position_raw is None and (record.opf or "").strip().upper() == "ИП":
        position_raw = "ИП"
    return _build_personal_block(
        surname, first_name, patronymic, None, position_raw, company_display, ""
    )


def plan_letter(
    building_group: BuildingGroup,
    contacts_index: ContactsIndex,
    settings: Settings,
    formation_date: datetime.date,
    egrul_overrides: dict[str, EgrulData] | None = None,
) -> LetterPlan:
    """Построить план письма для одного здания (группы строк выгрузки).

    `egrul_overrides` — необязательный словарь {нормализованный_адрес:
    EgrulData} с результатами уже пройденной проверки по ЕГРЮЛ для этого
    запуска генерации (см. модуль ЕГРЮЛ, раздел 6 ТЗ) — используется,
    если данных справочника недостаточно для персонального варианта.
    """
    address_display = format_address_for_letter(building_group.building_address)
    match = contacts_index.match(building_group.building_address)

    egrul_overrides = egrul_overrides or {}
    egrul = egrul_overrides.get(building_group.key)

    tc_name = ""
    variant = "impersonal"
    status = LetterStatus.AUTO_IMPERSONAL
    reason = ""
    recipient_main_lines: list[str] = ["Администрация торгового центра"]
    recipient_address_lines: list[str] = [address_display] if address_display else []
    greeting = ""
    low_confidence = False

    if match.status == MatchStatus.AMBIGUOUS:
        status = LetterStatus.MANUAL_REVIEW
        reason = match.reason
        tc_name = clean_tc_name(match.records[0].tc_name) if match.records else ""
    elif match.status == MatchStatus.MULTIPLE_INN:
        status = LetterStatus.MANUAL_REVIEW
        reason = match.reason
        tc_name = clean_tc_name(match.records[0].tc_name)
    elif match.status == MatchStatus.NOT_FOUND and egrul is None:
        status = LetterStatus.MANUAL_REVIEW
        reason = (
            "Адрес не найден в справочнике УК/ТЦ — неизвестно название "
            "торгового центра. Письмо сформировано черновиком в "
            "обезличенном виде, требуется ручная проверка."
        )
    else:
        record = match.record
        if record is not None:
            tc_name = clean_tc_name(record.tc_name)

        personal = _resolve_personal_variant(record, egrul) if (record is not None or egrul) else None
        if personal is not None:
            recipient_main_lines, recipient_address_lines, greeting, low_confidence = personal
            variant = "personal"
            status = LetterStatus.MANUAL_REVIEW if low_confidence else LetterStatus.AUTO_PERSONAL
            if low_confidence:
                reason = (
                    "Автоматическое склонение ФИО в адресном блоке может "
                    "быть неточным (редкое/иностранное имя) — проверьте "
                    "и подтвердите перед сохранением."
                )
            if egrul and not tc_name:
                tc_name = clean_tc_name(egrul.short_name or egrul.full_name or "") or tc_name
        else:
            status = LetterStatus.AUTO_IMPERSONAL

    row_specs = build_row_specs(building_group.rows)
    is_plural = len(row_specs) > 1
    forms = _number_forms(is_plural)

    deadline = compute_deadline(formation_date, settings.deadline_days, settings.holiday_dates())

    recipient_main_lines = [line for line in recipient_main_lines if line is not None]
    recipient_address_lines = [line for line in recipient_address_lines if line is not None]
    context: dict[str, str] = {
        # {{RECIPIENT_BLOCK}} — весь адресный блок одним куском (для
        # шаблонов с одним плейсхолдером на один абзац, см. TEMPLATE_GUIDE).
        "RECIPIENT_BLOCK": "\n".join(recipient_main_lines + recipient_address_lines),
        # {{RECIPIENT_BLOCK_MAIN}}/{{RECIPIENT_BLOCK_ADDRESS}} — то же самое,
        # но раздельно: в образцах писем должность/УК/ФИО и юридический
        # адрес набраны с разным отступом ("лесенкой"), поэтому их удобнее
        # класть в два разных абзаца с разным форматированием.
        "RECIPIENT_BLOCK_MAIN": "\n".join(recipient_main_lines),
        "RECIPIENT_BLOCK_ADDRESS": "\n".join(recipient_address_lines),
        "GREETING": greeting,
        "TC_NAME": tc_name,
        "TC_ADDRESS": address_display,
        "DEADLINE_DATE": format_date_ru(deadline),
        "EXECUTOR_NAME": settings.executor_name,
        "EXECUTOR_PHONE": settings.executor_phone,
        "SIGNATORY_NAME": settings.signatory_name,
    }
    context.update(forms)

    filename = build_letter_filename(address_display, tc_name, formation_date)

    return LetterPlan(
        building_group=building_group,
        status=status,
        status_reason=reason,
        variant=variant,
        tc_name=tc_name,
        address_display=address_display,
        context=context,
        row_specs=row_specs,
        filename=filename,
        low_confidence_inflection=low_confidence,
        contact_match=match,
    )
