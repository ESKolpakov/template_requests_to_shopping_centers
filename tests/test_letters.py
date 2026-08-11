import datetime

from fixtures import build_synthetic_contacts, build_synthetic_objects_report

from uktc_letters.config import Settings
from uktc_letters.contacts_source import ContactsIndex, load_contacts
from uktc_letters.letters import LetterStatus, plan_letter
from uktc_letters.objects_source import group_by_building, load_trade_objects


def _setup(tmp_path):
    xlsx = tmp_path / "report.xlsx"
    build_synthetic_objects_report(str(xlsx))
    rows = load_trade_objects(str(xlsx))
    groups = {g.building_address: g for g in group_by_building(rows)}

    contacts_xlsx = tmp_path / "contacts.xlsx"
    build_synthetic_contacts(str(contacts_xlsx))
    contacts = load_contacts(str(contacts_xlsx))
    index = ContactsIndex(contacts)

    settings = Settings(
        executor_name="И.И.Иванов",
        executor_phone="8 (495) 000-00-00",
        signatory_name="Петров П.П.",
    )
    settings.ensure_default_holidays()
    return groups, index, settings


def test_plan_letter_personal_variant(tmp_path):
    groups, index, settings = _setup(tmp_path)
    group = next(g for g in groups.values() if len(g.rows) == 2)

    plan = plan_letter(group, index, settings, datetime.date(2026, 8, 5))

    assert plan.status == LetterStatus.AUTO_PERSONAL
    assert plan.variant == "personal"
    assert "Иванову" in plan.context["RECIPIENT_BLOCK"]
    assert plan.context["GREETING"] == "Уважаемый Иван Иванович!"
    assert plan.context["SUBJECT_WORD_FORM"] == "хозяйствующих субъектах"  # 2 строки -> мн.ч.
    assert plan.context["VERB_OSUSHESTVLYAL"] == "осуществляли"
    assert len(plan.row_specs) == 2
    assert plan.row_specs[0].merge_start is True
    assert plan.row_specs[1].merge_continue is True


def test_plan_letter_impersonal_variant_known_tc(tmp_path):
    groups, index, settings = _setup(tmp_path)
    group = next(g for g in groups.values() if len(g.rows) == 1 and "Дальняя" in g.building_address)

    plan = plan_letter(group, index, settings, datetime.date(2026, 8, 5))

    assert plan.status == LetterStatus.AUTO_IMPERSONAL
    assert plan.variant == "impersonal"
    assert plan.tc_name  # известно из справочника (ИП без ФИО директора)
    assert plan.context["RECIPIENT_BLOCK"].startswith("Администрация торгового центра")
    assert plan.context["GREETING"] == ""
    assert plan.context["SUBJECT_WORD_FORM"] == "хозяйствующем субъекте"  # 1 строка -> ед.ч.


def test_plan_letter_deadline_uses_settings_days_and_holidays(tmp_path):
    groups, index, settings = _setup(tmp_path)
    settings.deadline_days = 5
    settings.holidays = []
    group = next(iter(groups.values()))

    plan = plan_letter(group, index, settings, datetime.date(2026, 7, 1))
    assert plan.context["DEADLINE_DATE"] == "06.07.2026"


def test_plan_letter_flags_low_confidence_declension_for_manual_review(tmp_path):
    # ТЗ п.4.1: на редких/иностранных ФИО склонение может ошибаться —
    # такое письмо не должно тихо сохраняться как "auto_personal", а
    # помечается на подтверждение пользователем (см. пример в ТЗ:
    # "Гулиев Гулам Билал Оглы").
    groups, index, settings = _setup(tmp_path)
    for rec in index._by_address.values():
        for r in rec:
            if r.tc_name == "ТЦ «Пример»":
                r.director_name = "Куулаэ Кызы Айдысмаа"
    group = next(g for g in groups.values() if len(g.rows) == 2)

    plan = plan_letter(group, index, settings, datetime.date(2026, 8, 5))

    assert plan.variant == "personal"
    assert plan.low_confidence_inflection is True
    assert plan.status == LetterStatus.MANUAL_REVIEW


def test_plan_letter_filename_uses_tc_name_when_known(tmp_path):
    groups, index, settings = _setup(tmp_path)
    group = next(g for g in groups.values() if "Дальняя" in g.building_address)
    plan = plan_letter(group, index, settings, datetime.date(2026, 8, 5))
    assert "ТЦ" in plan.filename
    assert plan.filename.endswith("05_08_2026.docx")
