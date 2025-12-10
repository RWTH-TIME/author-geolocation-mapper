from scystream.sdk.core import entrypoint
from scystream.sdk.file_handling.s3_manager import S3Operations
from scystream.sdk.env.settings import (
    PostgresSettings
)
from affiliations.matcher import AffiliationMatcher
from affiliations.normalization import normalize_institution_name
import pandas as pd
import bibtexparser
from sqlalchemy import create_engine

from settings import (
    AffiliationMatchingEntrypoint,
    REFERENCE_COL,
    BIBInput,
    AffiliationOutput
)


def write_df_to_postgres(df: pd.DataFrame, settings: PostgresSettings):
    engine = create_engine(
        f"postgresql+psycopg2://{settings.PG_USER}:{settings.PG_PASS}"
        f"@{settings.PG_HOST}:{int(settings.PG_PORT)}/{settings.PG_DB}"
    )
    df.to_sql(settings.DB_TABLE, engine, if_exists="replace", index=False)


# @entrypoint(AffiliationMatchingEntrypoint)
def affiliation_matching(settings):
    # S3Operations.download(settings.bib_input, "input.bib")

    # Load bib
    with open("test/files/savedrecs.bib") as bibtex_file:
        bib_db = bibtexparser.load(bibtex_file)

    # Load reference csv
    institution_mapping = pd.read_csv("key_geo_gh.csv", sep=";")
    institution_mapping["normalized"] = \
        institution_mapping[REFERENCE_COL].apply(normalize_institution_name)
    reference_names = institution_mapping["normalized"].tolist()

    matcher = AffiliationMatcher(
        mapping_df=institution_mapping,
        normalized_ref_names=reference_names,
        match_threshold=settings.MATCH_THRESHOLD,
        assign_all_if_single=settings.ASSIGN_ALL_IF_SINGLE_INSTITUTION,
    )

    results_df = matcher.match_bib(bib_db)

    print(results_df)
    return results_df


if __name__ == "__main__":
    settings = AffiliationMatchingEntrypoint(
        ASSIGN_ALL_IF_SINGLE_INSTITUTION=False,
        MATCH_THRESHOLD=75.0,
        bib_input=BIBInput(
            BUCKET_NAME="bucket",
            FILE_EXT="bib",
            FILE_NAME="name",
            FILE_PATH="",
            S3_ACCESS_KEY="access",
            S3_HOST="host",
            S3_PORT="1234",
            S3_SECRET_KEY="secret"
        ),
        affiliation_output=AffiliationOutput(
            DB_TABLE="postgres",
            PG_HOST="localhost",
            PG_PASS="postgres",
            PG_PORT="postgres",
            PG_USER="postgres",
        )
    )

    affiliation_matching(settings)
