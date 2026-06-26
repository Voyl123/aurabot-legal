"""Tests for weapon parsing and weapon-combo → class title."""

from src.weapons import parse_weapons, class_title


def test_parse_abbreviations_and_separators():
    assert parse_weapons("gs/dagger") == ["Greatsword", "Daggers"]
    assert parse_weapons("GS / Dagger") == ["Greatsword", "Daggers"]
    assert parse_weapons("staff, wand") == ["Staff", "Wand & Tome"]
    assert parse_weapons("xbow+dagger") == ["Crossbows", "Daggers"]


def test_parse_keeps_ampersand_weapon():
    assert parse_weapons("Sword & Shield / Wand") == ["Sword & Shield", "Wand & Tome"]


def test_parse_limits_to_two_and_dedupes():
    assert parse_weapons("gs/gs/dagger/bow") == ["Greatsword", "Daggers"]


def test_parse_empty_and_garbage():
    assert parse_weapons("") == []
    assert parse_weapons(None) == []
    assert parse_weapons("lol/nonsense") == []


def test_class_title_named_combo():
    assert class_title(["Greatsword", "Daggers"]) == "Bladedancer (GS/Dagger)"
    assert class_title(["Staff", "Wand & Tome"]) == "Sage (Staff/Wand)"


def test_class_title_order_independent():
    assert class_title(["Daggers", "Greatsword"]) == "Bladedancer (Dagger/GS)"


def test_class_title_unknown_combo_falls_back_to_abbr():
    # A valid pair with no curated name still gets a clean combo label.
    title = class_title(["Greatsword", "Greatsword"])  # contrived single after dedupe upstream
    assert "GS" in title


def test_class_title_single_and_empty():
    assert class_title(["Longbow"]) == "Bow"
    assert class_title([]) == ""
