import hashlib
from scystream.sdk.core import entrypoint
from scystream.sdk.file_handling.s3_manager import S3Operations
from scystream.sdk.env.settings import (
    PostgresSettings
)
from affiliations.matcher import AffiliationMatcher
import pandas as pd
import bibtexparser
from sqlalchemy import create_engine
from sqlalchemy.sql import quoted_name

from settings import (
    AffiliationMatchingEntrypoint,
)


def _normalize_table_name(table_name: str) -> str:
    max_length = 63
    if len(table_name) <= max_length:
        return table_name
    digest = hashlib.sha1(table_name.encode("utf-8")).hexdigest()[:10]
    prefix_length = max_length - len(digest) - 1
    return f"{table_name[:prefix_length]}_{digest}"


def _resolve_db_table(settings: PostgresSettings) -> str:
    normalized_name = _normalize_table_name(settings.DB_TABLE)
    settings.DB_TABLE = normalized_name
    return normalized_name


def write_df_to_postgres(df: pd.DataFrame, settings: PostgresSettings):
    resolved_table_name = _resolve_db_table(settings)
    engine = create_engine(
        f"postgresql+psycopg2://{settings.PG_USER}:{settings.PG_PASS}"
        f"@{settings.PG_HOST}:{int(settings.PG_PORT)}/"
    )
    table_name = quoted_name(resolved_table_name, quote=True)
    df.to_sql(table_name, engine, if_exists="replace", index=False)


@entrypoint(AffiliationMatchingEntrypoint)
def affiliation_matching(settings):
    S3Operations.download(settings.bib_input, settings.BIB_DOWNLOAD_PATH)

    # Load bib
    with open(settings.BIB_DOWNLOAD_PATH) as bibtex_file:
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
