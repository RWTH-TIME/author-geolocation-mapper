import os
import time
import pytest
import boto3
import psycopg2
import pandas as pd
from pathlib import Path
from botocore.exceptions import ClientError

from main import affiliation_matching  # your @entrypoint wrapper


MINIO_USER = "minioadmin"
MINIO_PWD = "minioadmin"
BUCKET_NAME = "test"

POSTGRES_USER = "postgres"
POSTGRES_PWD = "postgres"


def ensure_bucket(s3, bucket):
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        if e.response["Error"]["Code"] in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
        else:
            raise


@pytest.fixture
def s3_minio():
    client = boto3.client(
        "s3",
        endpoint_url="http://localhost:9000",
        aws_access_key_id=MINIO_USER,
        aws_secret_access_key=MINIO_PWD,
    )
    ensure_bucket(client, BUCKET_NAME)
    return client


@pytest.fixture(scope="session")
def postgres_conn():
    """Keep trying until postgres is ready."""
    for _ in range(30):
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                port=5432,
                user=POSTGRES_USER,
                password=POSTGRES_PWD,
                database="postgres",
            )
            conn.autocommit = True
            yield conn
            conn.close()
            return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Postgres did not start")


def test_affiliation_matching_entrypoint(s3_minio, postgres_conn):
    # --------------------------
    # 1. Upload input files
    # --------------------------

    bib_path = Path(__file__).parent / "files" / "savedrecs.bib"

    s3_minio.put_object(
        Bucket=BUCKET_NAME,
        Key="input.bib",
        Body=bib_path.read_bytes(),
    )

    # --------------------------
    # 2. Set environment variables
    # --------------------------

    env = {
        # Input S3
        "bib_file_S3_HOST": "http://127.0.0.1",
        "bib_file_S3_PORT": "9000",
        "bib_file_S3_ACCESS_KEY": MINIO_USER,
        "bib_file_S3_SECRET_KEY": MINIO_PWD,
        "bib_file_BUCKET_NAME": BUCKET_NAME,
        "bib_file_FILE_PATH": "",
        "bib_file_FILE_NAME": "input",
        "bib_file_FILE_EXT": "bib",

        # Output Postgres
        "affiliation_output_PG_HOST": "127.0.0.1",
        "affiliation_output_PG_PORT": "5432",
        "affiliation_output_PG_USER": POSTGRES_USER,
        "affiliation_output_PG_PASS": POSTGRES_PWD,
        "affiliation_output_DB_TABLE": "aff_results",

        # Matcher configuration
        "MATCH_THRESHOLD": "80",
        "ASSIGN_ALL_IF_SINGLE_INSTITUTION": "true",
    }

    for k, v in env.items():
        os.environ[k] = v

    affiliation_matching()

    cur = postgres_conn.cursor()
    cur.execute("SELECT * FROM aff_results ORDER BY 1;")

    df = pd.DataFrame(cur.fetchall(), columns=[
                      col.name for col in cur.description])

    # Basic assertions
    expected_cols = {
        "author", "institution", "similarity", "lat", "lon", "raw_rest"
    }
    assert expected_cols.issubset(df.columns)

    # Check we imported something meaningful
    assert len(df) > 0

    # 1. Test that at least one known author is present
    assert any(df["author"].str.contains("Benyoussef", case=False))

    # 2. Check that matched institution makes sense for a known case
    row = df[df["author"].str.contains("Benyoussef", case=False)].iloc[0]

    assert isinstance(row["institution"], str)
    assert len(row["institution"]) > 3      # non-empty name

    # Similarity is percentage (0–100), not normalized
    assert 0 <= row["similarity"] <= 100

    # 3. Coordinates MUST be present
    assert pd.notna(row["lat"])
    assert pd.notna(row["lon"])
    assert isinstance(row["lat"], float)
    assert isinstance(row["lon"], float)

    # 4. Threshold check
    assert (df["similarity"] >= float(
        os.environ["MATCH_THRESHOLD"])).all()

    # 5. Sanity: we have at least one author
    assert len(df["author"].unique()) >= 1

    # 6. raw_rest contains leftover institution strings
    assert df["raw_rest"].map(lambda x: isinstance(x, str)).all()
