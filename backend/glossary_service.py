import re
from sqlalchemy.orm import Session

from glossary_models import GlossaryTerm


GENERIC_CANDIDATE_TERMS = {
    "本",
    "副本",
    "地牢",
    "地下城",
    "下水道",
    "dungeon",
    "dungeons",
    "sewer",
    "sewers",
    "trial",
    "trials",
    "zone",
    "zones",
    "dd",
    "dps",
    "th",
    "tank",
    "healer",
    "heal",
    "lfm",
    "wts",
    "wtb",
    "hm",
    "vet",
    "normal",
    "exp",
    "prog",
    "cp",
}

ROMAN_OR_NUMBER_SUFFIX = re.compile(
    r"[\s\-–—]*(?:I|II|III|IV|V|VI|VII|VIII|IX|X|1|2|3|4|5|6|7|8|9|10)$",
    re.IGNORECASE,
)


def normalize_text(text: str) -> str:
    text = text.lower().strip()

    remove_chars = [
        " ",
        "\t",
        "\n",
        "\r",
        "'",
        "’",
        "`",
        "·",
        ".",
        ",",
        ":",
        ";",
        "-",
        "_",
        "—",
        "–",
        "[",
        "]",
        "(",
        ")",
        "（",
        "）",
    ]

    for ch in remove_chars:
        text = text.replace(ch, "")

    return text


def strip_roman_or_number_suffix(text: str) -> str:
    return ROMAN_OR_NUMBER_SUFFIX.sub("", text).strip()


def build_variants(text: str) -> set[str]:
    variants = set()

    original = text.strip()
    if original:
        variants.add(original)

    without_suffix = strip_roman_or_number_suffix(original)
    if without_suffix:
        variants.add(without_suffix)

    return variants


def lookup_glossary_matches_by_candidates(
    db: Session,
    candidates: list[str],
    limit: int = 20,
) -> list[dict]:
    if not candidates:
        return []

    normalized_candidates = []

    for candidate in candidates:
        for variant in build_variants(candidate):
            candidate_norm = normalize_text(variant)

            if (
                len(candidate_norm) >= 2
                and candidate_norm not in GENERIC_CANDIDATE_TERMS
            ):
                normalized_candidates.append(candidate_norm)

    if not normalized_candidates:
        return []

    terms = db.query(GlossaryTerm).all()

    matches = []
    seen = set()

    for term in terms:
        term_variants = set()
        term_variants.update(build_variants(term.zh))
        term_variants.update(build_variants(term.en))

        for term_variant in term_variants:
            term_norm = normalize_text(term_variant)

            if len(term_norm) < 2:
                continue

            for candidate_norm in normalized_candidates:
                exact_match = candidate_norm == term_norm
                candidate_is_partial = candidate_norm in term_norm
                term_is_partial = term_norm in candidate_norm

                if exact_match or candidate_is_partial or term_is_partial:
                    key = (term.zh, term.en)

                    if key not in seen:
                        matches.append(
                            {
                                "zh": term.zh,
                                "en": term.en,
                            }
                        )
                        seen.add(key)

                    break

            if len(matches) >= limit:
                return matches

    return matches
