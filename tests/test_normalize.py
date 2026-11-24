from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from shadowbank.normalize import (
    building_key,
    categories,
    entity_key,
    fold,
    free_zone_marker,
    is_generic_purpose,
    name_key,
)


def test_fold_strips_accents_and_punctuation() -> None:
    assert fold("Société Générale, S.A.") == "SOCIETE GENERALE S A"
    assert fold("  a--b  ") == "A B"


def test_name_key_removes_trailing_legal_forms_only() -> None:
    assert name_key("Varnel Trading Co., Ltd.") == "VARNEL TRADING"
    assert name_key("Tusket Petroleum DMCC") == "TUSKET PETROLEUM"
    assert name_key("Dorvin Maritime Inc") == "DORVIN MARITIME"
    assert name_key("The Ltd Group Ltd") == "LTD GROUP"
    assert name_key("Mar FZ LLC") == "MAR"


def test_entity_key_includes_country_and_handles_empty() -> None:
    assert entity_key("Varnel Trading Co Ltd", "hk") == "VARNEL TRADING|HK"
    assert entity_key("Varnel Trading Limited", "") == "VARNEL TRADING"
    assert entity_key("Ltd", "HK") == ""


def test_building_key_drops_units_but_keeps_building() -> None:
    a = building_key("Office 1203, Tower 7, Ketvin Lakes Road, Dubai")
    b = building_key("OFFICE #905 - TOWER 7 - KETVIN LAKES RD - DUBAI")
    c = building_key("Office 1203, Tower 8, Ketvin Lakes Road, Dubai")
    assert a == b == "TWR 7 KETVIN LAKES RD DUBAI"
    assert a != c


def test_building_key_floor_suite_and_po_box() -> None:
    assert building_key("Suite 4, Floor 12, 1 Rhoqua Street") == building_key("Floor 3, 1 Rhoqua St")
    assert building_key("Office No. 5, Unit # 7, 2 Rhoqua St") == "2 RHOQUA ST"
    assert building_key("P.O. Box 12, Majuro") == "PO BOX 12 MAJURO"
    assert building_key("") == ""


def test_building_key_keeps_named_unit_words() -> None:
    # A long word after "Unit" is part of the name, not a unit number.
    assert "BUSINESS" in building_key("Unit Business Centre, 4 Talsen Road")


def test_categories_and_generic_purpose() -> None:
    assert categories("Gasoil cargo, freight") == ["shipping", "oil"]
    assert categories("payment") == []
    for p in ["", "payment", "INV 4471", "as per contract", "Payment for goods", "settlement", "TRF REF 99"]:
        assert is_generic_purpose(p), p
    for p in ["crude oil cargo", "freight charter", "server components order"]:
        assert not is_generic_purpose(p), p


def test_free_zone_markers() -> None:
    assert free_zone_marker("Mar Consulting", "", "JAFZA") == "free_zone=JAFZA"
    assert free_zone_marker("Tusket Petroleum DMCC", "", "") == "DMCC in name"
    assert free_zone_marker("Tusket", "Office 2, Free Zone Road", "") == "free zone in address"
    assert free_zone_marker("Lio Metals FZE", "", "") == "FZE suffix"
    assert free_zone_marker("Lio Metals FZ-LLC", "", "") == "FZ-LLC suffix"
    assert free_zone_marker("Lio Metals LLC", "Sheikh Road", "") == ""


@given(st.text(max_size=60))
def test_keys_are_idempotent(s: str) -> None:
    assert fold(fold(s)) == fold(s)
    assert building_key(building_key(s)) == building_key(s)
    assert name_key(name_key(s)) == name_key(s)
