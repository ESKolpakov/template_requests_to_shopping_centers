import datetime

from uktc_letters.letters import LetterPlan, LetterStatus
from uktc_letters.objects_source import BuildingGroup
from uktc_letters.registry import Registry


def _fake_plan(address, status, tc_name=""):
    return LetterPlan(
        building_group=BuildingGroup(key=address, building_address=address, rows=[]),
        status=status,
        status_reason="",
        variant="impersonal",
        tc_name=tc_name,
        address_display=address,
        context={},
        row_specs=[],
        filename=f"{address}.docx",
    )


def test_registry_records_run_and_counts(tmp_path):
    db_path = tmp_path / "registry.sqlite3"
    registry = Registry(db_path)

    plans = [
        _fake_plan("Адрес 1", LetterStatus.AUTO_PERSONAL, "ТЦ 1"),
        _fake_plan("Адрес 2", LetterStatus.AUTO_IMPERSONAL, "ТЦ 2"),
        _fake_plan("Адрес 3", LetterStatus.MANUAL_REVIEW),
    ]
    summary = registry.record_run(
        plans,
        datetime.date(2026, 8, 5),
        objects_source_path="report.xlsx",
        contacts_source_path="contacts.xlsx",
        template_path="template.docx",
    )

    assert summary.total_addresses == 3
    assert summary.auto_personal == 1
    assert summary.auto_impersonal == 1
    assert summary.manual_review == 1

    runs = registry.list_runs()
    assert len(runs) == 1
    assert runs[0].id == summary.id

    letters = registry.list_letters(summary.id)
    assert len(letters) == 3

    manual = registry.list_letters(summary.id, status=LetterStatus.MANUAL_REVIEW.value)
    assert len(manual) == 1
    assert manual[0].address == "Адрес 3"

    registry.close()


def test_registry_persists_between_instances(tmp_path):
    db_path = tmp_path / "registry.sqlite3"
    registry = Registry(db_path)
    registry.record_run([_fake_plan("Адрес 1", LetterStatus.AUTO_PERSONAL)], datetime.date(2026, 8, 5))
    registry.close()

    registry2 = Registry(db_path)
    runs = registry2.list_runs()
    assert len(runs) == 1
    registry2.close()
