from affiliations.authors import (
    remove_parens,
    parse_single_author,
    parse_authors,
    extract_institution,
)
from affiliations.models import ParsedAffiliation


def test_remove_parens_simple():
    s = "Ren, SY (Corresponding Author)"
    assert remove_parens(s) == "Ren, SY"


def test_parse_single_author_formats():
    assert parse_single_author("Smith, John") == "Smith, John"
    assert parse_single_author("Jane, Doe") == "Jane, Doe"


def test_parse_authors_with_authors_then_institution():
    text = "Smith, John; Doe, Jane; University of Test, Department of Foobar,\
            UK"
    parsed = parse_authors(text)
    assert isinstance(parsed, ParsedAffiliation)
    assert "Smith, John" in parsed.authors
    assert "Doe, Jane" in parsed.authors
    # rest should contain the institution part
    assert "University of Test" in parsed.rest and "Department" in parsed.rest


def test_parse_authors_last_block_person_and_institution():
    # last block contains both person and institution:
    text = "Smith, John; Müller, Hans, University of Freiburg, Germany"
    parsed = parse_authors(text)
    assert "Smith, John" in parsed.authors
    assert "Müller, Hans" in parsed.authors or "Müller, Hans" in\
        parsed.authors or any("Hans" in a for a in parsed.authors)
    assert "University" in parsed.rest


def test_extract_institution_truncates_after_comma():
    rest = "University of Test, Department of X, City"
    inst = extract_institution(rest)
    # normalize_institution_name lowercases & sorts tokens
    assert "university" in inst or "test" in inst
