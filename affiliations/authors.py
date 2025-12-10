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
    if "," in segment:
        last, first = (x.strip() for x in segment.split(",", 1))
        return f"{first} {last}"
    return segment.strip()


def parse_authors(text: str) -> ParsedAffiliation:
    """Extract authors and institution rest block."""
    cleaned = remove_parens(text)
    parts = [p.strip() for p in cleaned.split(";")]

    authors = []

    # Parse authors, except last part (which might be author + institution)
    for part in parts[:-1]:
        if part and not looks_like_institution(part):
            authors.append(parse_single_author(part))

    last_block = remove_parens(parts[-1])
    pieces = [p.strip() for p in last_block.split(",")]

    # Now look at special last part, check wether author can be found
    if len(pieces) >= 2:
        maybe_person = f"{pieces[0]} {pieces[1]}"
        if not looks_like_institution(maybe_person):
            authors.append(f"{pieces[1]} {pieces[0]}")
            rest = ", ".join(pieces[2:])
            return ParsedAffiliation(authors, rest)

    return ParsedAffiliation(authors, last_block)


def extract_institution(rest: str) -> str:
    return normalize_institution_name(rest.split(",", 1)[0].strip())
