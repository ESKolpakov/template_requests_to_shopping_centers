from uktc_letters.addresses import (
    building_key,
    format_address_for_letter,
    normalize_address,
    split_room,
)


def test_split_room_strips_tail():
    building, room = split_room(
        "район Филевский Парк, улица Барклая, дом 10А, комната 20,21,11,10,9,22,23"
    )
    assert building == "район Филевский Парк, улица Барклая, дом 10А"
    assert room.startswith("комната")


def test_split_room_no_room():
    building, room = split_room("Вешняковская улица, 15А")
    assert building == "Вешняковская улица, 15А"
    assert room == ""


def test_normalize_address_matches_across_word_order_and_abbreviations():
    a = normalize_address(
        "район Филевский Парк, улица Барклая, дом 10А, комната 20,21,11,10,9,22,23"
    )
    b = normalize_address("ул. Барклая, д. 10А")
    assert a == b


def test_normalize_address_matches_name_first_vs_type_first():
    a = normalize_address("Вешняковская улица, 15А")
    b = normalize_address("район Вешняки, улица Вешняковская, дом 15А, комната -")
    assert a == b


def test_normalize_address_handles_ordinal_street_name_reorder():
    a = normalize_address(
        "район Северное Измайлово, улица Парковая 9-я, дом 61А, строение 1, комната -"
    )
    b = normalize_address("ул. 9-я Парковая, д.61А, стр.1")
    assert a == b


def test_building_key_is_normalize_address():
    addr = "ул. Минская, д.14-А"
    assert building_key(addr) == normalize_address(addr)


def test_normalize_address_differs_for_different_buildings():
    a = normalize_address("ул. Минская, д.14А")
    b = normalize_address("ул. Минская, д.14Б")
    assert a != b


def test_format_address_for_letter_basic():
    assert (
        format_address_for_letter(
            "район Филевский Парк, улица Барклая, дом 10А, комната 20"
        )
        == "ул. Барклая, д.10А"
    )


def test_format_address_for_letter_prospekt_and_korpus():
    assert (
        format_address_for_letter(
            "район Свиблово, проспект Мира, дом 211, корпус 2, комната -"
        )
        == "пр-т Мира, д.211, корп.2"
    )
