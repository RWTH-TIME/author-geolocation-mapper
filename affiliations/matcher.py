import pandas as pd
from rapidfuzz import process, fuzz
import bibtexparser

from settings import REFERENCE_COL
from .models import MatchResult
from .authors import parse_authors, extract_institution


class AffiliationMatcher:
    """
    High-level orchestrator: takes BibTeX entries, extracts authors,
    matches institutions using fuzzy matching, returns structured results.
    """

    def __init__(
        self,
        mapping_df: pd.DataFrame,
        normalized_ref_names: list[str],
        match_threshold: float = 70.0,
        assign_all_if_single=True,
    ):
        self.mapping_df = mapping_df
        self.ref_names = normalized_ref_names
        self.threshold = match_threshold
        self.assign_all_if_single = assign_all_if_single

    def best_match(self, query: str) -> MatchResult:
        match, score, idx = process.extractOne(
            query,
            self.ref_names,
            scorer=fuzz.token_sort_ratio,
        )
        row = self.mapping_df.loc[idx]
        return MatchResult(
            best_match=row[REFERENCE_COL],
            similarity=score,
            lat=row["lat"],
            lon=row["lon"],
        )

    def match_bib(
        self,
        bib_db: bibtexparser.bibdatabase.BibDatabase
    ) -> pd.DataFrame:
        results = []

        for entry in bib_db.entries:
            paper_authors = self._parse_paper_authors(entry)
            affiliations = self._parse_affiliations(entry)

            single_aff = len(affiliations) == 1

            for aff in affiliations:
                parsed = parse_authors(aff)
                inst = extract_institution(parsed.rest)
                match = self.best_match(inst)

                targets = (
                    parsed.authors
                    if parsed.authors
                    else (
                        paper_authors if single_aff and
                        self.assign_all_if_single else [])
                )

                for author in targets:
                    results.append(self._make_assignment(
                        author, parsed.rest, match))

        return pd.DataFrame(results)

    # --------------------------
    # Helpers
    # --------------------------
    @staticmethod
    def _parse_paper_authors(entry: dict) -> list[str]:
        raw = entry.get("author", "")
        raw = " ".join(raw.replace("\n", " ").split())
        return [a.strip() for a in raw.split(" and ")]

    @staticmethod
    def _parse_affiliations(entry: dict) -> list[str]:
        raw_aff = entry.get("affiliation", "")
        return [a.strip() for a in raw_aff.split("\n") if a.strip()]

    def _make_assignment(
        self,
        author: str,
        rest: str,
        match: MatchResult
    ) -> dict:
        institution = match.best_match if \
            match.similarity > self.threshold else None

        return {
            "author": author,
            "institution": institution,
            "similarity": match.similarity,
            "lat": match.lat,
            "lon": match.lon,
            "raw_rest": rest,
        }
