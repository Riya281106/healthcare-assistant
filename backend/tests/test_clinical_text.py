from app.utils.clinical_text import normalize, split_clauses


def test_curly_and_straight_apostrophes_normalise_the_same():
    assert normalize("I can\u2019t breathe") == normalize("I can't breathe") == "i cant breathe"


def test_case_and_spacing_are_normalised():
    assert normalize("  CAN'T    BREATHE!! ") == "cant breathe"


def test_devanagari_marks_are_preserved():
    text = "\u0938\u0940\u0928\u0947 \u092e\u0947\u0902 \u0926\u0930\u094d\u0926"
    assert normalize(text) == text


def test_clauses_split_on_but_and_sentences():
    clauses = split_clauses("No fever but chest pain. Also tired")
    assert clauses == ["no fever", "chest pain", "also tired"]


def test_empty_input():
    assert normalize("") == ""
    assert normalize(None) == ""
    assert split_clauses("") == []
