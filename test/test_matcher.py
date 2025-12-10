import pandas as pd
import bibtexparser
import pytest

from affiliations.matcher import AffiliationMatcher
from settings import REFERENCE_COL


@pytest.fixture
def simple_mapping_df():
    # two reference rows, one that will match exactly and another different
    df = pd.DataFrame([
        {REFERENCE_COL: "Test University", "lat": 10.0, "lon": 20.0},
        {REFERENCE_COL: "Other Institute", "lat": 0.0, "lon": 0.0},
    ])
    return df


@pytest.fixture
def simple_bib_db():
    db = bibtexparser.bibdatabase.BibDatabase()
    # one entry with author field and affiliation lines
    db.entries = [
        {
            "ID": "paper1",
            "author": "Smith, John and Doe, Jane",
            "affiliation": "Smith, John; Doe, Jane; Test University,\
                    Department of Stuff, Country"
        },
        {
            "ID": "paper2",
            "author": "Wong, Mei",
            # affiliation that won't match any reference well
            "affiliation": "Wong, Mei; Some Unknown Place, Nowhere"
        },
    ]
    return db


def test_affiliation_matcher_skips_low_similarity(
        simple_mapping_df,
        simple_bib_db
):
    # use a high threshold so that the unknown place is skipped
    matcher = AffiliationMatcher(
        mapping_df=simple_mapping_df,
        match_threshold=90.0,
        assign_all_if_single=True
    )

    df = matcher.match_bib(simple_bib_db)

    # For paper1, we expect two assignments (Smith and Doe) matching
    # Test University
    # For paper2, since similarity to any reference should be low, we
    # expect no rows for it
    assert isinstance(df, pd.DataFrame)
    # there should be exactly 2 rows for paper1
    assert len(df) == 2
    assert set(df['author']) == {"John Smith", "Jane Doe"} or\
        set(df['author']) == {"Smith, John", "Doe, Jane"} or\
        any("John" in a for a in df['author'])
    assert all(df['institution'].notnull())
    # lat/lon should match the Test University row
    assert all(df['lat'] == 10.0)
    assert all(df['lon'] == 20.0)
