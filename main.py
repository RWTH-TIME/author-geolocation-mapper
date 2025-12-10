from scystream.sdk.core import entrypoint
from scystream.sdk.file_handling.s3_manager import S3Operations
from scystream.sdk.env.settings import (
    PostgresSettings
)
from affiliations.matcher import AffiliationMatcher
import pandas as pd
import bibtexparser
from sqlalchemy import create_engine

from settings import (
    AffiliationMatchingEntrypoint,
)


def write_df_to_postgres(df: pd.DataFrame, settings: PostgresSettings):
    engine = create_engine(
        f"postgresql+psycopg2://{settings.PG_USER}:{settings.PG_PASS}"
        f"@{settings.PG_HOST}:{int(settings.PG_PORT)}/"
    )
    df.to_sql(settings.DB_TABLE, engine, if_exists="replace", index=False)


@entrypoint(AffiliationMatchingEntrypoint)
def affiliation_matching(settings):
    S3Operations.download(settings.bib_input, "input.bib")

    # Load bib
    with open("input.bib") as bibtex_file:
        bib_db = bibtexparser.load(bibtex_file)

    # Load reference csv
    institution_mapping = pd.read_csv("key_geo_gh.csv", sep=";")
    institution_mapping["lat"] = (
        institution_mapping["lat"].astype(str).str.replace(
            ",", ".", regex=False).astype(float)
    )
    institution_mapping["lon"] = (
        institution_mapping["lon"].astype(str).str.replace(
            ",", ".", regex=False).astype(float)
    )

    matcher = AffiliationMatcher(
        mapping_df=institution_mapping,
        match_threshold=settings.MATCH_THRESHOLD,
        assign_all_if_single=settings.ASSIGN_ALL_IF_SINGLE_INSTITUTION,
    )

    results_df = matcher.match_bib(bib_db)

    write_df_to_postgres(results_df, settings.affiliation_output)
