from uktc_letters.formatting import (
    format_company_name,
    format_legal_address,
    parse_director_field,
    split_fio,
)


def test_split_fio_three_words():
    assert split_fio("Селезнев Сергей Львович") == ("Селезнев", "Сергей", "Львович")


def test_split_fio_rejects_non_three_words():
    assert split_fio("ООО Ромашка") is None
    assert split_fio("") is None
    assert split_fio("Шведов А.Н.") is None


def test_format_company_name_from_full_legal_form():
    assert (
        format_company_name('ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ "АКТИВО-ИНВЕСТ"')
        == "ООО «АКТИВО-ИНВЕСТ»"
    )


def test_format_company_name_from_bare_name_with_opf_hint():
    assert format_company_name("ВИШЕНКА", "ООО") == "ООО «ВИШЕНКА»"


def test_format_company_name_already_short_form():
    assert format_company_name('ООО "ВИШЕНКА"') == "ООО «ВИШЕНКА»"


def test_format_legal_address_title_cases_and_lowercases_abbreviations():
    result = format_legal_address(
        "142701, МОСКОВСКАЯ ОБЛАСТЬ, Г. ВИДНОЕ, УЛ. ОЛЬХОВАЯ, Д. 9"
    )
    assert result == "142701, Московская область, г. Видное, ул. Ольховая, д. 9"


def test_parse_director_field_plain_fio():
    d = parse_director_field("Селезнев Сергей Львович")
    assert d.fio == "Селезнев Сергей Львович"
    assert d.position_raw is None
    assert d.organization_name is None


def test_parse_director_field_with_position_colon():
    d = parse_director_field("ГЕНЕРАЛЬНЫЙ ДИРЕКТОР: Лекомцева Светлана Михайловна")
    assert d.position_raw == "ГЕНЕРАЛЬНЫЙ ДИРЕКТОР"
    assert d.fio == "Лекомцева Светлана Михайловна"


def test_parse_director_field_with_position_newline():
    d = parse_director_field("Генеральный директор\nБаринский Михаил Петрович")
    assert d.position_raw == "Генеральный директор"
    assert d.fio == "Баринский Михаил Петрович"


def test_parse_director_field_position_without_separator():
    d = parse_director_field("Руководитель Авданкин Александр Александрович")
    assert d.position_raw == "Руководитель"
    assert d.fio == "Авданкин Александр Александрович"


def test_parse_director_field_organization_representative():
    d = parse_director_field('Управляющая организация: ООО "ГАРАНТ-ИНВЕСТ"')
    assert d.organization_name == 'ООО "ГАРАНТ-ИНВЕСТ"'
    assert d.fio is None


def test_parse_director_field_unparseable_note():
    d = parse_director_field("по информации префектуры ЮВАО объект закрыт")
    assert d.fio is None
    assert d.organization_name is None


def test_parse_director_field_empty():
    d = parse_director_field("")
    assert d.fio is None
    assert d.position_raw is None
