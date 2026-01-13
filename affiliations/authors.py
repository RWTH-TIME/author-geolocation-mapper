from .normalization import normalize_institution_name
from .models import ParsedAffiliation
from .heuristics import looks_like_institution


def remove_parens(s: str) -> str:
    out, depth = [], 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(depth - 1, 0)
        elif depth == 0:
            out.append(ch)
    return "".join(out).strip()


def parse_single_author(segment: str) -> str:
    return segment.strip()


def parse_authors(text: str) -> ParsedAffiliation:
    """Extract authors and the remainder institution block."""
    cleaned = remove_parens(text)
    parts = [p.strip() for p in cleaned.split(";")]

    authors = []

    # Parse everything except last part
    for part in parts[:-1]:
        if part and not looks_like_institution(part):
            authors.append(parse_single_author(part))

    # Last block: may contain author or institution
    last_block = remove_parens(parts[-1])
    pieces = [p.strip() for p in last_block.split(",")]

    # Case: "Lastname, Firstname, Institution…"
    if len(pieces) >= 2:
        maybe_person = f"{pieces[0]}, {pieces[1]}"
        if not looks_like_institution(maybe_person):
            authors.append(parse_single_author(maybe_person))
            rest = ", ".join(pieces[2:])
            return ParsedAffiliation(authors, rest)

    return ParsedAffiliation(authors, last_block)


def extract_institution(rest: str) -> str:
    return normalize_institution_name(rest.split(",", 1)[0].strip())
