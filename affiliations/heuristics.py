from settings import INSTITUTION_KEYWORDS


def contains_digits(s: str) -> bool:
    return any(ch.isdigit() for ch in s)


def too_many_non_alpha(s: str, threshold=0.3) -> bool:
    """
    Return True if more than `threshold` fraction of characters
    in the string are non-alphabetic (excluding spaces, hyphens,
                                      and apostrophes).

    High non-alphabetic density suggests the segment is not a person's name
    (e.g., contains punctuation, symbols, codes).
    """
    if not s:
        return True
    bad = sum(not (c.isalpha() or c.isspace() or c in "-'") for c in s)
    return (bad / len(s)) > threshold


def looks_like_institution(segment: str) -> bool:
    """
    Heuristically classify a segment as an institutional affiliation.

    A segment is considered an institution if:
      - The segment is empty
      - The first or second comma-separated token contains digits (e.g.,
                                                                   addresses)
      - The first token contains known institution keywords
      - The first token has unusually many words (unlikely for a person)
      - The first token has a high proportion of non-alphabetic characters
    """
    if not segment:
        return True

    parts = [p.strip() for p in segment.split(",")]
    first = parts[0]
    second = parts[1] if len(parts) > 1 else ""

    if contains_digits(first) or contains_digits(second):
        return True

    if any(kw in first.lower() for kw in INSTITUTION_KEYWORDS):
        return True

    if len(first.split()) > 6:
        return True

    if too_many_non_alpha(first):
        return True

    return False
