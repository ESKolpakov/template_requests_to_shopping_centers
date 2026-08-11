from uktc_letters.morphology import (
    format_dative_initials_surname,
    format_full_name,
    guess_gender_by_patronymic,
    position_to_dative,
)


def test_dative_female_surname():
    text, low_conf = format_dative_initials_surname(
        "Лекомцева", "Светлана", "Михайловна", "female"
    )
    assert text == "С.М.Лекомцевой"
    assert low_conf is False


def test_dative_male_surname():
    text, low_conf = format_dative_initials_surname(
        "Жданов", "Дмитрий", "Анатольевич", "male"
    )
    assert text == "Д.А.Жданову"
    assert low_conf is False


def test_format_full_name_nominative():
    assert format_full_name("Светлана", "Михайловна") == "Светлана Михайловна"
    assert format_full_name("дмитрий", "анатольевич") == "Дмитрий Анатольевич"


def test_guess_gender_by_patronymic():
    assert guess_gender_by_patronymic("Михайловна") == "female"
    assert guess_gender_by_patronymic("Анатольевич") == "male"
    assert guess_gender_by_patronymic("") is None


def test_position_to_dative_known_and_fallback():
    assert position_to_dative("ГЕНЕРАЛЬНЫЙ ДИРЕКТОР") == "Генеральному директору"
    assert position_to_dative("Директор") == "Директору"
    assert position_to_dative("ип") == "ИП"
    assert position_to_dative(None) == "Руководителю"
    assert position_to_dative("Коммерческий директор") == "Руководителю"
