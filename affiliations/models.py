from dataclasses import dataclass


@dataclass
class MatchResult:
    best_match: str
    similarity: int
    lat: float
    lon: float


@dataclass
class ParsedAffiliation:
    authors: list[str]
    rest: str


@dataclass
class AffiliationAssignment:
    author: str
    institution: str | None
    similarity: int
    lat: float
    lon: float
    raw_rest: str
