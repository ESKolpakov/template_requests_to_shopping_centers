from fixtures import build_synthetic_objects_report

from uktc_letters.objects_source import (
    clean_object_name,
    group_by_building,
    load_trade_objects,
)


def test_clean_object_name_strips_parenthesized_suffix():
    assert clean_object_name("Мастер ПОЛО (ТЦ до 14.08.2026)") == "Мастер ПОЛО"
    assert (
        clean_object_name("Двери Регионов (доп запрос на нов УК ТЦ до 14.08.2026)")
        == "Двери Регионов"
    )


def test_clean_object_name_no_parens():
    assert clean_object_name("Смешные цены") == "Смешные цены"


def test_load_and_group(tmp_path):
    xlsx = tmp_path / "report.xlsx"
    build_synthetic_objects_report(str(xlsx))

    rows = load_trade_objects(str(xlsx))
    assert len(rows) == 3

    groups = group_by_building(rows)
    # Первые две строки — один адрес (Примерная, 1) -> одна группа из 2 строк.
    by_key = {g.key: g for g in groups}
    assert len(groups) == 2
    grouped = [g for g in groups if len(g.rows) == 2][0]
    assert grouped.rows[0].object_name == "Тестовый магазин"
    assert grouped.rows[1].subject == "Иванов Иван Иванович"

    single = [g for g in groups if len(g.rows) == 1][0]
    assert single.rows[0].object_name == "Одиночный объект"
    assert single.rows[0].floor == "2"
    assert single.rows[0].room_number == "12"
