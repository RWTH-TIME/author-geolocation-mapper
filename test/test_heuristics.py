from affiliations.heuristics import (
    contains_digits,
    too_many_non_alpha,
    looks_like_institution,
)


def test_contains_digits_true_false():
    assert contains_digits("123 Main St")
    assert contains_digits("Room 42")
    assert not contains_digits("John Smith")


def test_too_many_non_alpha_edge_cases():
    assert too_many_non_alpha("")  # empty -> True by design
    assert too_many_non_alpha("!!!@@@###")  # mostly symbols -> True
    assert not too_many_non_alpha("John Smith")  # normal name -> False
    assert not too_many_non_alpha("Université de Paris")


def test_looks_like_institution_empty_and_digits_and_keywords(monkeypatch):
    # empty -> True
    assert looks_like_institution("")

    # digits in first or second token should return True
    assert looks_like_institution("123 Main St, City")
    assert looks_like_institution("Center for X, 42")

    # keyword matching relies on settings.INSTITUTION_KEYWORDS
    # ensure common keyword triggers classification
    assert looks_like_institution("University of Nowhere")
    assert looks_like_institution("Institute of Testing")


def test_looks_like_institution_long_token_and_symbols():
    long_name = "This is a fake long institution name with many tokens"
    assert looks_like_institution(long_name)

    weird = "Dept @ Lab ###"
    assert looks_like_institution(weird)


def test_person_name_not_institution():
    assert not looks_like_institution("Smith, John")
    assert not looks_like_institution("Maria del Carmen")
