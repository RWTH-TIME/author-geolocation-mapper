from scystream.sdk.env.settings import (
    EnvSettings,
    InputSettings,
    OutputSettings,
    FileSettings,
    PostgresSettings
)

REFERENCE_COL = "name"
INSTITUTION_KEYWORDS = {
    "univ", "university", "dept", "department", "inst", "institute",
    "lab", "laboratory", "college", "school", "hosp", "hospital",
    "ctr", "center", "centre", "faculty", "fac", "academy", "dept.", "inst.",
    "management"
}


class BIBInput(FileSettings, InputSettings):
    __identifier__ = "bib_file"
    FILE_EXT: str = "bib"


class AffiliationOutput(PostgresSettings, OutputSettings):
    __identifier__ = "affiliation_output"


class AffiliationMatchingEntrypoint(EnvSettings):
    ASSIGN_ALL_IF_SINGLE_INSTITUTION: bool = True
    MATCH_THRESHOLD: float = 75.0

    bib_input: BIBInput
    affiliation_output: AffiliationOutput
