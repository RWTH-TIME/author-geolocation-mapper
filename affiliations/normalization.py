import unicodedata


def normalize_text(text: str) -> str:
    """Lowercase, strip, remove diacritics."""
    text = unicodedata.normalize("NFD", text.lower().strip())
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def normalize_institution_name(text: str) -> str:
    """Normalize institution strings."""
    text = normalize_text(text)
    for sym in ("\\&", "&"):
        text = text.replace(sym, " and ")
    return " ".join(sorted(text.split()))
