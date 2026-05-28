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


def ranges_overlap(first: tuple[int, int], second: tuple[int, int]) -> bool:
    return first[0] < second[1] and second[0] < first[1]


def choose_maximal_matches(matches: list[dict], limit: int) -> list[dict]:
    ordered_matches = sorted(
        matches,
        key=lambda match: (
            -(match["end"] - match["start"]),
            -match["score"],
            match["start"],
        ),
    )

    accepted = []
    occupied_ranges: list[tuple[int, int]] = []
    seen_terms = set()

    for match in ordered_matches:
        match_range = (match["start"], match["end"])
        term_key = (match["zh"], match["en"])

        if term_key in seen_terms:
            continue

        if any(ranges_overlap(match_range, occupied) for occupied in occupied_ranges):
            continue

        accepted.append(match)
        occupied_ranges.append(match_range)
        seen_terms.add(term_key)

        if len(accepted) >= limit:
            break

    accepted.sort(key=lambda match: (match["candidate_index"], match["start"]))

    return [
        {
            "zh": match["zh"],
            "en": match["en"],
        }
        for match in accepted
    ]


def lookup_glossary_matches_by_candidates(
    db: Session,
    candidates: list[str],
    limit: int = 20,
) -> list[dict]:
    if not candidates:
        return []

    normalized_candidates = []

    for candidate_index, candidate in enumerate(candidates):
        for variant in build_variants(candidate):
            candidate_norm = normalize_text(variant)

            if (
                len(candidate_norm) >= 2
                and candidate_norm not in GENERIC_CANDIDATE_TERMS
            ):
                normalized_candidates.append(
                    {
                        "index": candidate_index,
                        "norm": candidate_norm,
                    }
                )

    if not normalized_candidates:
        return []

    terms = db.query(GlossaryTerm).all()

    possible_matches = []
    seen_possible = set()

    for term in terms:
        term_variants = set()
        term_variants.update(build_variants(term.zh))
        term_variants.update(build_variants(term.en))

        for term_variant in term_variants:
            term_norm = normalize_text(term_variant)

            if len(term_norm) < 2:
                continue

            for candidate in normalized_candidates:
                candidate_norm = candidate["norm"]
                match_start = candidate_norm.find(term_norm)
                exact_match = candidate_norm == term_norm
                term_is_partial = match_start != -1

                if exact_match or term_is_partial:
                    key = (
                        candidate["index"],
                        match_start,
                        match_start + len(term_norm),
                        term.zh,
                        term.en,
                    )

                    if key not in seen_possible:
                        possible_matches.append(
                            {
                                "candidate_index": candidate["index"],
                                "start": match_start,
                                "end": match_start + len(term_norm),
                                "score": 2 if exact_match else 1,
                                "zh": term.zh,
                                "en": term.en,
                            }
                        )
                        seen_possible.add(key)

                    break

    return choose_maximal_matches(possible_matches, limit)
