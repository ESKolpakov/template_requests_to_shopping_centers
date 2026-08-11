from fixtures import build_synthetic_contacts

from uktc_letters.contacts_source import ContactsIndex, MatchStatus, load_contacts


def test_load_and_match(tmp_path):
    xlsx = tmp_path / "contacts.xlsx"
    build_synthetic_contacts(str(xlsx))

    records = load_contacts(str(xlsx))
    assert len(records) == 3

    index = ContactsIndex(records)

    ok = index.match("ул. Примерная, д.1")
    assert ok.status == MatchStatus.OK
    assert ok.record.management_company == "ТЕСТОВАЯ КОМПАНИЯ"

    not_found = index.match("ул. Несуществующая, д.99")
    assert not_found.status == MatchStatus.NOT_FOUND

    multi_inn = index.match("ул. Спорная, д.9")
    assert multi_inn.status == MatchStatus.MULTIPLE_INN
    assert len(set(multi_inn.records[0].inn_tokens)) == 2


def test_ambiguous_multiple_rows_same_address(tmp_path):
    import openpyxl

    xlsx = tmp_path / "contacts.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Лист 1"
    ws.append(
        [
            "№ п/п", "Адрес/иные ориентиры расположения торгового объекта",
            "Район", "Административный округ г. Москвы", "Наименование ТЦ",
            "Предполагаемое количество торговых объектов",
            "Организационно-правовая форма (код по ОКОПФ)",
            "Управляющая компания", "ИНН управляющей компании",
            "Руководитель управляющей компании", "Телефон управляющей компании",
            "Email управляющей компании",
            "Дополнительная информация (заполняется при необходимости)", "ответ",
        ]
    )
    ws.append(
        [
            1, "ул. Тестовая, д.1", None, None, "ТЦ Вектор", None, "ООО",
            "КОМПАНИЯ РЕНТУС", "7700000001", "Иванов Иван Иванович", None,
            "info@example.test", "", "",
        ]
    )
    ws.append(
        [
            2, "ул. Тестовая, д.1", None, None, "ТЦ Вектор", None, None, None,
            None, None, None, "note@example.test",
            'ООО "Амистад" не является управляющей компанией торгового центра "Вектор"',
            "",
        ]
    )
    wb.save(xlsx)

    records = load_contacts(str(xlsx))
    index = ContactsIndex(records)
    result = index.match("ул. Тестовая, д.1")
    assert result.status == MatchStatus.AMBIGUOUS
    assert len(result.records) == 2
