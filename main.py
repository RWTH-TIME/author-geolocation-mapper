import bibtexparser
import pprint
import unicodedata
import pandas as pd
from rapidfuzz import fuzz, process

with open("savedrecs.bib") as bibtex_file:
    bib_db = bibtexparser.load(bibtex_file)


"""
Matching of Institutions
"""


def normalize_inst_names(text: str):
    text = text.lower()

    text = ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    )

    # replace latex escaped & and normal &
    text = text.replace("\\&", " and ")
    text = text.replace("&", " and ")

    tokens = text.split()
    tokens = sorted(tokens)
    return " ".join(tokens)


def extract_inst_name_from_rest(rest: str):
    return normalize_inst_names(rest.split(",")[0])


key_df = pd.read_csv("key_geo_gh.csv", sep=";")
print(key_df)

# Assume the CSV has a column named "name" or similar
# Adjust the column name here:
REFERENCE_COL = "name"    # <-- change this if needed

# Create a normalized column in your reference list
key_df["norm"] = key_df[REFERENCE_COL].apply(normalize_inst_names)

# Build a list of searchable normalized names
reference_names = key_df["norm"].tolist()


def best_match(raw_insti):
    norm_query = normalize_inst_names(raw_insti)

    match, score, idx = process.extractOne(
        norm_query,
        reference_names,
        scorer=fuzz.token_sort_ratio
    )

    return {
        "raw": raw_insti,
        "best_match": key_df.loc[idx, REFERENCE_COL],
        "similarity": score,
        "country": key_df.loc[idx, "country"] if "country" in key_df.columns else None,
        "city": key_df.loc[idx, "city"] if "city" in key_df.columns else None
    }


"""
Extracting of Authors from Affiliations
"""


def remove_parens(s):
    out = ""
    skip = 0
    for ch in s:
        if ch == "(":
            skip += 1
        elif ch == ")":
            if skip > 0:
                skip -= 1
        elif skip == 0:
            out += ch
    return out.strip()


def normalize_simple(s: str) -> str:
    s = s.lower()
    out = []
    for ch in s:
        if ch in ".,;:()[]{}-":
            out.append(" ")
        else:
            out.append(ch)
    s = "".join(out)
    return " ".join(s.split())  # collapse whitespace


INSTITUTION_KEYWORDS = {
    "univ", "university", "dept", "department", "inst", "institute",
    "lab", "laboratory", "college", "school", "hosp", "hospital",
    "ctr", "center", "centre", "faculty", "fac", "academy", "dept.", "inst.",
    "management"
}
ASSIGN_ALL_IF_SINGLE_INSTITUTION = False


def looks_like_institution_segment(segment: str) -> bool:
    """
    Heuristic tests that a comma-separated segment is probably an institution line,
    not a person name.
    """
    if not segment:
        return True

    pieces = [p.strip() for p in segment.split(",")]
    # If any of the first two pieces contains digits -> address/institution
    for p in pieces[:2]:
        if any(ch.isdigit() for ch in p):
            return True

    # If any of the first two pieces contains an institution keyword -> institution
    for p in pieces[:2]:
        lower = p.lower().replace(".", "")
        for kw in INSTITUTION_KEYWORDS:
            if kw in lower:
                return True

    # If the first piece is long (more than 4 tokens) it's unlikely to be a personal first name
    if len(pieces[0].split()) > 4:
        return True

    # If the first piece contains many non-alpha chars (commas already split), it's likely not a name
    non_alpha = sum(1 for ch in pieces[0] if not (
        ch.isalpha() or ch.isspace() or ch in "-'"))
    if non_alpha / max(1, len(pieces[0])) > 0.3:
        return True

    # Otherwise assume it's not an institution (i.e., likely a person)
    return False

# ------------------------------------------------------------
# Parse an affiliation line into (authors_in_line, rest_of_affiliation)
# If no authors are found, authors_in_line = []
# ------------------------------------------------------------


def parse_authors(text: str):
    """
    Revised parse_authors that skips institutional segments in parts[:-1].
    Returns (authors_list, rest_string).
    """
    # remove parentheses content early
    text = remove_parens(text)

    parts = [p.strip() for p in text.split(";")]

    authors = []

    # Iterate definite-author segments (all except the last) but skip institution-like ones
    for part in parts[:-1]:
        seg = remove_parens(part).strip()
        if not seg:
            continue

        # If this segment looks like an institution, skip it entirely
        if looks_like_institution_segment(seg):
            # skip adding bogus author
            continue

        # otherwise parse author: split on first comma
        if "," in seg:
            first, last = [x.strip() for x in seg.split(",", 1)]
            authors.append(f"{first} {last}")
        else:
            # fallback
            authors.append(seg)

    # handle final block (may contain last author + rest or just rest)
    last_block = remove_parens(parts[-1]).strip()
    pieces = [p.strip() for p in last_block.split(",")]

    if len(pieces) < 2:
        # last block doesn't contain an author (only rest)
        return authors, last_block

    # If the first two items in the last block look like institution → no author here
    first_two_joined = pieces[0] + " " + (pieces[1] if len(pieces) > 1 else "")
    if looks_like_institution_segment(first_two_joined):
        return authors, last_block

    # otherwise the first two pieces form the final author
    first = pieces[0]
    last = pieces[1]
    authors.append(f"{first} {last}")
    rest = ", ".join(pieces[2:]).strip()
    return authors, rest


"""
MAIN
"""
for entry in bib_db.entries:
    entry_id = entry.get("ID")

    raw_authors = entry.get("author", "")
    cleaned_authors = " ".join(raw_authors.replace("\n", " ").split())
    paper_authors = [a.strip() for a in cleaned_authors.split(" and ")]

    raw_affiliations = entry.get("affiliation", "")
    affiliations = [aff.strip()
                    for aff in raw_affiliations.split("\n") if aff.strip()]

    mapping = {}

    for affi in affiliations:
        aff_authors, rest = parse_authors(affi)
        match = best_match(extract_inst_name_from_rest(rest))

        # If authors detected → assign normally
        if aff_authors:
            # Extract institution-like chunk
            for a in aff_authors:
                mapping[a] = {
                    "institution": match["best_match"] if match["similarity"] > 75 else None,
                    "lat": 0,
                    "lon": 0,
                    "similarity": match["similarity"],
                    "raw": match["raw"],
                    "rest": extract_inst_name_from_rest(rest)
                }

    # Handle: "assign all authors if only one institution"
    if ASSIGN_ALL_IF_SINGLE_INSTITUTION:
        if len(mapping) == 0 and len(affiliations) == 1:
            _, rest = parse_authors(affiliations[0])
            match = best_match(extract_inst_name_from_rest(rest))

            if rest:
                for a in paper_authors:
                    mapping[a] = {
                        "institution": match["best_match"] if match["similarity"] > 75 else None,
                        "lat": 0,
                        "lon": 0,
                        "similarity": match["similarity"],
                        "raw": match["raw"],
                        "rest": rest
                    }

    print(f"\n=== {entry_id} ===")
    pprint.pprint(mapping, sort_dicts=True)
