from scystream.sdk.core import entrypoint
from scystream.sdk.file_handling.s3_manager import S3Operations
from scystream.sdk.database_handling.database_manager import (
    PandasDatabaseOperations,
)
from affiliations.matcher import AffiliationMatcher
import pandas as pd
import bibtexparser

from settings import (
    AffiliationMatchingEntrypoint,
)


@entrypoint(AffiliationMatchingEntrypoint)
def affiliation_matching(settings):
    S3Operations.download(settings.bib_input, settings.BIB_DOWNLOAD_PATH)

    # Load bib
    with open(settings.BIB_DOWNLOAD_PATH) as bibtex_file:
        bib_db = bibtexparser.load(bibtex_file)

    # Load reference csv
    institution_mapping = pd.read_csv("key_geo_gh.csv", sep=";")
    institution_mapping["lat"] = (
        institution_mapping["lat"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )
    institution_mapping["lon"] = (
        institution_mapping["lon"]
        .astype(str)
        .str.replace(",", ".", regex=False)
        .astype(float)
    )

    matcher = AffiliationMatcher(
        mapping_df=institution_mapping,
        match_threshold=settings.MATCH_THRESHOLD,
        assign_all_if_single=settings.ASSIGN_ALL_IF_SINGLE_INSTITUTION,
    )

    results_df = matcher.match_bib(bib_db)

    affiliations_db = PandasDatabaseOperations(
        settings.affiliation_output.DB_DSN
    )
    affiliations_db.write(
        table=settings.affiliation_output.DB_TABLE, data=results_df
    )
