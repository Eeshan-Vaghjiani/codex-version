"""
Map English, Swahili and mixed-language symptom text
to canonical respiratory symptom codes.

This module uses the validated English and Swahili aliases
stored in the NLP folder.
"""

import json
import re
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.errors import ServiceNotReadyError
from app.db.models import Symptom, SymptomAlias
from app.nlp.breathing_tier import classify_breathing_tier

from rapidfuzz import fuzz, process
from rapidfuzz.distance import DamerauLevenshtein


PROJECT_ROOT = Path(__file__).resolve().parents[1]

ENGLISH_ALIASES_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "english_aliases.json"
)

SWAHILI_ALIASES_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "swahili_aliases.json"
)

CANONICAL_SYMPTOMS_PATH = (
    PROJECT_ROOT
    / "nlp"
    / "canonical_symptoms.json"
)

# Bundled warning-sign definitions are independent of the editable DB
# catalogue. Cache them at import so routine DB extraction does not read JSON.
_SAFETY_SYMPTOMS = {
    item["code"]: item for item in json.loads(
        CANONICAL_SYMPTOMS_PATH.read_text(encoding="utf-8")
    ) if item["is_red_flag"]
}
_SAFETY_ALIAS_INDEX = tuple(sorted(
    ({"alias": alias.lower(), "code": code, "language": language}
     for code, item in _SAFETY_SYMPTOMS.items()
     for language, aliases in item.get("aliases", {}).items()
     for alias in aliases), key=lambda item: len(item["alias"]), reverse=True,
))

FUZZY_THRESHOLD = 90
SUGGESTION_THRESHOLD = 70

FILLER_WORDS = {
    "i",
    "im",
    "i'm",
    "have",
    "has",
    "having",
    "a",
    "an",
    "the",
    "and",
    "but",
    "or",
    "my",
    "me",
    "am",
    "is",
    "are",
    "feel",
    "feeling",
    "with",
    "also",
    "nina",
    "niko",
    "na",
    "lakini",
    "kuwa",
    "sana", "had", "been", "do", "does", "did", "not", "no", "never",
    "without", "dont", "don't", "doesn't", "didn't", "sina", "hana",
    "hakuna", "sipigi", "wala", "mild", "moderate", "severe", "kidogo",
    "wastani", "kali", "kwa", "siku", "wiki", "since", "still",
    "dry", "wet", "productive", "kikavu", "chenye", "up", "started",
}

def load_json(path):
    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def normalize_text(text):
    """
    Convert text to lowercase and normalize whitespace.
    """

    text = text.lower().strip().replace("’", "'").replace("‘", "'")

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text


def build_alias_index(
    db: Session | None = None,
):
    """
    Build the searchable English and Swahili alias index.

    The API uses the persistent database catalogue.
    JSON files remain available for standalone use.
    """

    alias_index = []

    if db is not None:
        rows = db.execute(
            select(
                SymptomAlias.alias,
                Symptom.code,
                SymptomAlias.language,
            ).join(
                Symptom,
                SymptomAlias.symptom_id
                == Symptom.id,
            )
        ).all()

        for row in rows:
            alias_index.append(
                {
                    "alias": normalize_text(
                        row.alias
                    ),
                    "code": row.code,
                    "language": row.language,
                }
            )

    else:
        english_aliases = load_json(
            ENGLISH_ALIASES_PATH
        )

        swahili_aliases = load_json(
            SWAHILI_ALIASES_PATH
        )

        for code, aliases in (
            english_aliases.items()
        ):
            for alias in aliases:
                alias_index.append(
                    {
                        "alias": normalize_text(
                            alias
                        ),
                        "code": code,
                        "language": "en",
                    }
                )

        for code, aliases in (
            swahili_aliases.items()
        ):
            for alias in aliases:
                alias_index.append(
                    {
                        "alias": normalize_text(
                            alias
                        ),
                        "code": code,
                        "language": "sw",
                    }
                )

    alias_index.sort(
        key=lambda item: len(
            item["alias"]
        ),
        reverse=True,
    )

    return alias_index

def find_fuzzy_matches(
    normalized_text,
    alias_index,
    matched_codes,
    occupied_spans,
):
    """
    Find misspelled or near-matching symptom phrases.

    Fuzzy matching is only used after exact alias matching.
    This reduces the chance of replacing a correct exact match
    with a weaker approximate match.
    """

    fuzzy_matches = []

    words = list(
        re.finditer(
            r"\b[\w']+\b",
            normalized_text,
        )
    )

    for item in alias_index:
        code = item["code"]

        if code == "sputum_reported" and item["alias"] == "mucus":
            continue  # This ambiguous noun requires exact respiratory context.

        if code in matched_codes:
            continue

        alias = item["alias"]

        alias_word_count = len(
            alias.split()
        )

        if alias_word_count == 0:
            continue

        if len(words) < alias_word_count:
            continue

        best_score = 0
        best_candidate = None
        best_span = None

        for start_index in range(
            len(words)
            - alias_word_count
            + 1
        ):
            end_index = (
                start_index
                + alias_word_count
                - 1
            )

            start = words[
                start_index
            ].start()

            end = words[
                end_index
            ].end()

            overlaps = any(
                start < existing_end
                and end > existing_start
                for (
                    existing_start,
                    existing_end,
                )
                in occupied_spans
            )

            if overlaps:
                continue

            candidate = (
                normalized_text[
                    start:end
                ]
            )

            score = fuzz.ratio(
                candidate,
                alias,
            )

            if score > best_score:
                best_score = score
                best_candidate = candidate
                best_span = (
                    start,
                    end,
                )

        # Only a single edit (including an adjacent transposition) in a
        # sufficiently long word is eligible for automatic typo matching.
        # Broad string similarity can silently change one symptom to another.
        is_close_typo = (
            best_candidate is not None
            and len(alias) >= 5
            and len(alias.split()) == 1
            and best_candidate[:1] == alias[:1]
            and DamerauLevenshtein.distance(best_candidate, alias) == 1
        )
        if best_candidate is not None and (
            is_close_typo
            or (len(alias.split()) > 1 and best_score >= 95)
        ):
            fuzzy_matches.append(
                {
                    "code": code,
                    "matched_alias": (
                        best_candidate
                    ),
                    "canonical_alias": alias,
                    "language": item[
                        "language"
                    ],
                    "match_type": "fuzzy",
                    "score": round(
                        best_score,
                        1,
                    ),
                    "_span": best_span,
                }
            )

            matched_codes.add(code)

            occupied_spans.append(
                best_span
            )

    return fuzzy_matches

def find_symptoms(text, db: Session | None = None):
    """Find exact aliases followed by conservative typo matches."""
    return _find_alias_matches(text, build_alias_index(db))


def _find_alias_matches(text, alias_index):
    normalized_text = normalize_text(text)
    matches = []
    matched_codes = set()
    occupied_spans = []

    # -------------------------
    # Exact matching
    # -------------------------

    for item in alias_index:
        alias = item["alias"]

        pattern = (
            r"(?<!\w)"
            + re.escape(alias)
            + r"(?!\w)"
        )

        for match in re.finditer(
            pattern,
            normalized_text,
        ):
            start, end = match.span()
            if item["code"] == "sputum_reported" and alias == "mucus":
                surrounding = normalized_text[max(0, start-40):end+45]
                if not re.search(
                    r"\bcough(?:ing)?\s+(?:up|with)\s+(?:\w+\s+)?mucus\b"
                    r"|\bmucus\s+(?:from\s+(?:my|the)\s+chest|when\s+i\s+cough)\b",
                    surrounding,
                ):
                    continue

            overlaps = any(
                start < existing_end
                and end > existing_start
                for (
                    existing_start,
                    existing_end,
                )
                in occupied_spans
            )

            if overlaps:
                continue

            code = item["code"]

            if code in matched_codes:
                occupied_spans.append((start, end))
                continue

            matches.append(
                {
                    "code": code,
                    "matched_alias": alias,
                    "canonical_alias": alias,
                    "language": item[
                        "language"
                    ],
                    "match_type": "exact",
                    "score": 100.0,
                }
            )

            matched_codes.add(
                code
            )

            occupied_spans.append(
                (
                    start,
                    end,
                )
            )

    # -------------------------
    # Fuzzy matching
    # -------------------------

    fuzzy_matches = (
        find_fuzzy_matches(
            normalized_text,
            alias_index,
            matched_codes,
            occupied_spans,
        )
    )

    for match in fuzzy_matches:
        match.pop(
            "_span",
            None,
        )

    matches.extend(
        fuzzy_matches
    )

    return matches

def find_unmatched_text(
    text,
    matches,
    alias_index=None,
):
    """
    Return meaningful words or phrases that were not
    recognised as supported symptoms.
    """

    remaining_text = normalize_text(
        text
    )

    # Remove all recognised phrases, including alternative
    # aliases that refer to the same canonical symptom.
    matched_codes = {
        match["code"] for match in matches
    }

    aliases_to_remove = {
        normalize_text(match["matched_alias"])
        for match in matches
    }

    if matched_codes:
        aliases_to_remove.update(
            item["alias"]
            for item in (alias_index if alias_index is not None else build_alias_index())
            if item["code"] in matched_codes
        )

    # Remove longer phrases first to avoid partial matches.
    for alias in sorted(
        aliases_to_remove,
        key=len,
        reverse=True
    ):
        pattern = (
            r"(?<!\w)"
            + re.escape(alias)
            + r"(?!\w)"
        )

        remaining_text = re.sub(
            pattern,
            " ",
            remaining_text,
        )

    # Duration and severity are contextual attributes, not unmatched symptoms.
    remaining_text = DURATION_PATTERN.sub(" ", remaining_text)
    # Treat common English/Swahili connectors as separators.
    remaining_text = re.sub(
        r"\b(and|but|or|na|lakini)\b",
        ",",
        remaining_text,
    )

    segments = re.split(
        r"[,;.!?]+",
        remaining_text,
    )

    unmatched = []

    for segment in segments:
        words = re.findall(
            r"\b[\w']+\b",
            segment,
        )

        meaningful_words = [
            word
            for word in words
            if word not in FILLER_WORDS
        ]

        if not meaningful_words:
            continue

        phrase = " ".join(
            meaningful_words
        )

        if phrase not in unmatched:
            unmatched.append(
                phrase
            )

    return unmatched

def suggest_symptoms(
    unmatched_phrases,
    alias_index,
    limit=3,
):
    """
    Suggest supported symptoms for unmatched wording.

    Suggestions are for user review only and are not
    automatically treated as confirmed symptoms.
    """

    suggestions = []

    alias_lookup = {
        item["alias"]: item
        for item in alias_index
    }

    alias_choices = list(
        alias_lookup.keys()
    )

    for phrase in unmatched_phrases:

        # Prevent unsupported symptoms from
        # being incorrectly suggested.
        unsupported_terms = {
            "sneezing",
            "sneeze",
            "sneezes",
        }

        if phrase.strip().lower() in unsupported_terms:
            suggestions.append({
                "unmatched_text": phrase,
                "suggestions": [],
            })
            continue

        results = process.extract(
            phrase,
            alias_choices,
            scorer=fuzz.ratio,
            limit=limit,
        )

        phrase_suggestions = []

        seen_codes = set()

        for (
            alias,
            score,
            _,
        ) in results:

            if score < SUGGESTION_THRESHOLD:
                continue

            item = alias_lookup[
                alias
            ]

            code = item["code"]

            if code in seen_codes:
                continue

            phrase_suggestions.append(
                {
                    "code": code,
                    "suggested_alias": alias,
                    "language": item[
                        "language"
                    ],
                    "score": round(
                        score,
                        1,
                    ),
                }
            )

            seen_codes.add(
                code
            )

        suggestions.append(
            {
                "unmatched_text": phrase,
                "suggestions": (
                    phrase_suggestions
                ),
            }
        )

    return suggestions


OTHER_PERSON_PATTERN = (
    r"\b(?:my\s+(?:sister|brother|mother|father|mom|dad|son|daughter|child|friend|wife|husband)"
    r"|(?:dada|kaka|mama|baba|mtoto|rafiki|mke|mume)\s+(?:yangu|wangu))\b"
)
PATIENT_REFERENCE_PATTERN = (
    r"\b(?:i|me|myself|mimi|nina\w*|nime\w*|nakohoa|siwezi)\b"
    r"|\bmy\s+(?:head|throat|chest|body|nose)\b"
)


def context_prefix(normalized, occurrence):
    boundaries = list(re.finditer(
        r"\b(?:but|lakini|however)\b"
        r"|\b(?:and|na)\s+(?=(?:i\s+)?(?:am|have|feel|can|cannot|can't|was|nina\w*|sina|siwezi|nakohoa|mimi|struggling|gasping|no\s+appetite|not\s+hungry|don'?t\s+feel\s+like\s+eating)\b)"
        r"|[.!?;]", normalized[:occurrence.end()],
    ))
    start = boundaries[-1].end() if boundaries else 0
    return normalized[start:occurrence.start()]


def infer_symptom_status(text, matched_alias):
    """
    Determine whether a recognised symptom is
    present, absent or unknown.
    """
    normalized = normalize_text(text)

    pattern = (
        r"(?<!\w)"
        + re.escape(normalize_text(matched_alias))
        + r"(?!\w)"
    )

    occurrences = list(re.finditer(pattern, normalized))

    if not occurrences:
        return "unknown"

    statuses = []

    for occurrence in occurrences:
        before = normalized[:occurrence.start()]


        after = normalized[occurrence.end():]

        # Check whether a symptom belongs to another person.
        subject_clause = re.split(
            r"\b(?:but|however|lakini)\b|[.!?;]",
            normalized[:occurrence.end()],
        )[-1]

        other_person = re.search(
            OTHER_PERSON_PATTERN,
            subject_clause,
        )

        patient_mentioned = (
            other_person is not None
            and re.search(
                PATIENT_REFERENCE_PATTERN,
                subject_clause[other_person.end():],
            )
        )

        if other_person and not patient_mentioned:
            denied = re.match(
                r"\s*[,;]?\s*(?:but\s+)?not\s+me\b",
                after,
            )

            statuses.append(
                "absent" if denied else "unknown"
            )
            continue

        if normalize_text(matched_alias) in {"sikohoi"}:
            statuses.append("absent")
            continue

        # Check whether a past symptom has resolved.
        if re.search(
            r"\bi\s+had\s+(?:a\s+|an\s+)?$",
            before,
        ):
            if re.search(
                r"\b(?:but\s+not\s+now|not\s+anymore|no\s+longer)\b",
                after,
            ):
                statuses.append("absent")

            elif re.search(
                r"\bstill\s+have\s+it\b",
                after,
            ):
                statuses.append("present")

            else:
                statuses.append("unknown")

            continue


        clause = context_prefix(normalized, occurrence)

        uncertain = re.search(
            r"\b(?:not\s+sure|unsure|don'?t\s+(?:know|think)|sijui|maybe|perhaps|labda|huenda|sina\s+uhakika|may|might|could)\b|\bdo\s+i\s+have\b|\bif\s+(?:i|nina)\b",
            clause
        )

        negations = list(re.finditer(
            r"\b(?:no|not(?!\s+only\b)|never|without|don'?t|doesn'?t|didn'?t|sina|hana|hakuna|sipigi|sihisi|siko)\b",            clause
        ))

        if uncertain:
            statuses.append("unknown")

        elif negations:
            last_negation = negations[-1]
            remainder = clause[last_negation.end():]

            restarted = re.search(
                r"\b(?:i\s+have|i\s+am|nina)\b",
                remainder
            )

            statuses.append(
                "present" if restarted else "absent"
            )

        else:
            statuses.append("present")

    if len(set(statuses)) == 1:
        return statuses[0]

    return "unknown"


def infer_symptom_subject(text, matched_alias):
    """
    Identify clear reports about another person.
    Unclear cases remain eligible for safety review.
    """
    normalized = normalize_text(text)
    alias = normalize_text(matched_alias)

    pattern = (
        r"(?<!\w)"
        + re.escape(alias)
        + r"(?!\w)"
    )

    occurrences = list(re.finditer(pattern, normalized))

    if not occurrences:
        return "unclear"

    subjects = []

    for occurrence in occurrences:
        before = normalized[:occurrence.start()]

        clause = re.split(
            r"[.!?;]|\b(?:but|however|lakini)\b",
            normalized[:occurrence.end()]
        )[-1]

        other_people = list(re.finditer(
            OTHER_PERSON_PATTERN,
            clause
        ))

        patient_references = list(re.finditer(
            PATIENT_REFERENCE_PATTERN,
            clause
        ))

        if (
            other_people
            and (
                not patient_references
                or other_people[-1].start()
                > patient_references[-1].start()
            )
        ):
            subjects.append("other_person")
        else:
            subjects.append("patient_or_unspecified")

    if all(subject == "other_person" for subject in subjects):
        return "other_person"

    return "patient_or_unspecified"



def infer_repeated_symptom_context(
    text, matched_alias, code=None, alias_index=None
):
    """
    Combine different phrases for the same symptom code,
    while keeping patient and other-person reports separate.
    """
    normalized = normalize_text(text)
    aliases = {normalize_text(matched_alias)}

    if code is not None and alias_index is not None:
        aliases.update(
            item["alias"]
            for item in alias_index
            if item["code"] == code
        )

    def matching_aliases(fragment):
        found = []
        occupied = []

        # Longer phrases take priority over overlapping ones.
        for alias in sorted(aliases, key=len, reverse=True):
            pattern = (
                r"(?<!\w)"
                + re.escape(alias)
                + r"(?!\w)"
            )

            for occurrence in re.finditer(pattern, fragment):
                overlaps = any(
                    occurrence.start() < end
                    and occurrence.end() > start
                    for start, end in occupied
                )

                if overlaps:
                    continue

                found.append(alias)
                occupied.append(occurrence.span())

        return found

    # Preserve existing behaviour for one symptom mention.
    if len(matching_aliases(normalized)) < 2:
        return (
            infer_symptom_status(text, matched_alias),
            infer_symptom_subject(text, matched_alias),
        )

    clauses = re.split(
        r"\b(?:but|however|lakini)\b"
        r"|\b(?:and|na)\s+(?=(?:i|my|am|nina|sina)\b)"
        r"|,\s*(?=(?:i|my)\b)"
        r"|[.!?;]",
        normalized,
    )

    mentions = []

    for clause in clauses:
        for alias in matching_aliases(clause):
            mentions.append((
                infer_symptom_status(clause, alias),
                infer_symptom_subject(clause, alias),
            ))

    if not mentions:
        return "unknown", "patient_or_unspecified"

    patient_states = {
        status
        for status, subject in mentions
        if subject != "other_person"
    }

    if not patient_states:
        return "unknown", "other_person"

    if len(patient_states) == 1:
        return patient_states.pop(), "patient_or_unspecified"

    # Conflicting patient reports require confirmation.
    return "unknown", "patient_or_unspecified"


NUMBER_WORDS = {
    "a": 1, "an": 1, "one": 1, "two": 2, "three": 3,
    "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "moja": 1, "mbili": 2, "tatu": 3,
    "nne": 4, "tano": 5, "sita": 6, "saba": 7, "nane": 8,
    "tisa": 9, "kumi": 10,
}
QUANTITY_PATTERN = r"(?:\d+|" + "|".join(NUMBER_WORDS) + r"|a few|few|several|chache|kadhaa)"
DURATION_PATTERN = re.compile(
    r"\b(?:for\s+(?:(?:the\s+)?(?:last|past)\s+)?(?P<en_approx>about\s+)?(?P<en_min>" + QUANTITY_PATTERN + r")"
    r"(?:\s*(?:-|to)\s*(?P<en_max>" + QUANTITY_PATTERN + r"))?"
    r"\s*(?P<en_unit>days?|weeks?|months?|hours?)"
    r"|(?P<ago_min>" + QUANTITY_PATTERN + r")\s+(?P<ago_unit>days?|weeks?|months?|hours?)\s+ago"
    r"|(?:kwa\s+)?(?P<sw_unit>siku|wiki|miezi|saa)\s+"
    r"(?P<sw_min>" + QUANTITY_PATTERN + r")"
    r"(?:\s*(?:-|hadi)\s*(?P<sw_max>" + QUANTITY_PATTERN + r"))?"
    r"|since\s+yesterday|tangu\s+jana|started\s+yesterday"
    r"|since\s+(?:this\s+morning|last\s+night)|started\s+today|tangu\s+asubuhi)\b"
)


def parse_duration(fragment):
    """Preserve vague durations without assigning invented numerical bounds."""
    match = DURATION_PATTERN.search(fragment)
    if match is None:
        return None
    raw = match.group()
    if raw in {"since yesterday", "tangu jana", "started yesterday"}:
        return {"duration_text": raw, "duration_min_days": 1,
                "duration_max_days": 1, "duration_unit": "days"}
    unit = match.group("en_unit") or match.group("sw_unit") or match.group("ago_unit")
    if unit is None:
        return {"duration_text": raw, "duration_min_days": None,
                "duration_max_days": None, "duration_unit": "relative"}
    low = match.group("en_min") or match.group("sw_min") or match.group("ago_min")
    high = match.group("en_max") or match.group("sw_max") or low
    def number(value):
        return int(value) if value.isdigit() else NUMBER_WORDS.get(value)
    minimum, maximum = number(low), number(high)
    if match.group("en_approx"):
        minimum = maximum = None
    multiplier = 7 if unit.startswith("week") or unit == "wiki" else 1
    # Months/hours cannot be exactly represented by integer days.
    if unit.startswith(("month", "hour")) or unit in {"miezi", "saa"}:
        minimum = maximum = None
    if minimum is not None and maximum is not None:
        if minimum < 1 or maximum < minimum:
            return None
        minimum *= multiplier
        maximum *= multiplier
    return {"duration_text": raw, "duration_min_days": minimum,
            "duration_max_days": maximum, "duration_unit": unit}


def extract_patient_attributes(text, matched_alias, code, alias_index):
    """Extract attributes within patient clauses; conflicting reports stay unset."""
    normalized = normalize_text(text)
    aliases = {normalize_text(matched_alias)} | {
        item["alias"] for item in alias_index if item["code"] == code
    }
    clauses = re.split(
        r"\b(?:but|however|lakini)\b"
        r"|\b(?:and|na)\s+(?=(?:i|my|am|nina|sina)\b)"
        r"|,\s*(?=(?:i|my)\b)|[.!?;]", normalized,
    )
    durations, severities = [], set()
    severity_values = {"mild": "mild", "moderate": "moderate", "severe": "severe",
                       "kidogo": "mild", "wastani": "moderate", "kali": "severe"}
    for clause in clauses:
        for alias in sorted(aliases, key=len, reverse=True):
            for occurrence in re.finditer(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", clause):
                if infer_symptom_subject(clause, alias) == "other_person":
                    continue
                if infer_symptom_status(clause, alias) != "present":
                    continue
                # A shared trailing duration applies to a coordinated symptom
                # list, but never cross another subject or an earlier duration.
                following = clause[occurrence.end():]
                duration = parse_duration(following)
                if duration is not None:
                    prefix = following[:following.find(duration["duration_text"])]
                    if not re.search(r"\b(?:with|without)\b", prefix):
                        durations.append(duration)
                local = clause[max(0, occurrence.start()-24):occurrence.end()]
                local = re.split(r",|\b(?:and|na|with)\b", local)[-1]
                values = re.findall(r"\b(?:mild|moderate|severe|kidogo|wastani|kali)\b", local)
                if not values:
                    suffix = re.match(r"\s+(?:(?:is|ni)\s+)?(?:(?:dry|wet|productive|kikavu)\s+)?(mild|moderate|severe|kidogo|wastani|kali)\b", following)
                    values = [suffix.group(1)] if suffix else []
                severities.update(severity_values[value] for value in values)
    distinct = {tuple(sorted(value.items())) for value in durations}
    result = dict(next(iter(distinct))) if len(distinct) == 1 else {
        "duration_text": None, "duration_min_days": None,
        "duration_max_days": None, "duration_unit": None,
    }
    result["severity"] = next(iter(severities)) if len(severities) == 1 else None
    result.update(extract_context_attributes(normalized, aliases, code))
    return result


def extract_context_attributes(normalized, aliases, code):
    contexts = []
    for clause in re.split(r"[.!?;]|\b(?:but|however|lakini)\b", normalized):
        for alias in aliases:
            if not re.search(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", clause):
                continue
            if infer_symptom_subject(clause, alias) == "other_person":
                continue
            if infer_symptom_status(clause, alias) == "present":
                contexts.append(clause)
    result = {}
    context = " ".join(dict.fromkeys(contexts))
    if code == "cough":
        dry = bool(re.search(r"\b(?:dry|kikavu)\b|\b(?:no|without)\s+(?:phlegm|sputum)\b|\bbila\s+makohozi\b", context))
        productive = bool(re.search(r"\b(?:wet|productive)\s+cough\b", context))
        for alias in ("phlegm", "sputum", "makohozi"):
            if re.search(r"\b" + alias + r"\b", context) and infer_symptom_status(context, alias) == "present":
                productive = True
        if re.search(r"\bcough(?:ing)?\s+(?:up|with)\s+(?:\w+\s+)?mucus\b", context):
            productive = True
        result["cough_type"] = "dry" if dry and not productive else "productive" if productive and not dry else None
    if code == "tiredness":
        if re.search(r"\b(?:non[- ]restful|unrefreshing)\s+sleep\b|never\s+feel\s+rested", context):
            result["fatigue_pattern"] = "unrefreshing"
        elif re.search(r"\b(?:constant|constantly|always)\b|all\s+the\s+time|kila\s+wakati", context):
            result["fatigue_pattern"] = "persistent"
        else:
            result["fatigue_pattern"] = "unspecified"
    if code == "weight_loss":
        if re.search(r"without\s+trying|unintentional|unintended|without\s+meaning\s+to|bila\s+(?:kukusudia|sababu)", context):
            result["weight_loss_intent"] = "unintentional"
        elif re.search(r"on\s+purpose|intentionally|dieting|kwa\s+(?:makusudi|kukusudia)", context):
            result["weight_loss_intent"] = "intentional"
        else:
            result["weight_loss_intent"] = "unspecified"
    onset = re.search(r"\b(?:since\s+(?:this\s+morning|last\s+night)|started\s+(?:today|yesterday)|tangu\s+(?:asubuhi|jana\s+usiku))\b", context)
    result["onset_text"] = onset.group() if onset else None
    return result


def extract_symptom_duration_days(text, matched_alias):
    duration = parse_duration(normalize_text(text).split(normalize_text(matched_alias), 1)[-1])
    return duration["duration_min_days"] if duration else None


def extract_patient_duration_days(text, matched_alias, code, alias_index):
    return extract_patient_attributes(text, matched_alias, code, alias_index)["duration_min_days"]


def build_confirmation_output(text, db: Session | None = None):
    """
    Build the structured output that can be sent to the
    frontend for symptom review and confirmation.
    """

    if db is not None and db.scalar(select(SymptomAlias.id).limit(1)) is None:
        raise ServiceNotReadyError(
            "The symptom catalogue has not been loaded into the database. "
            "Run: python -m app.db.seed_symptom_catalog"
        )
    matches = find_symptoms(text, db)

    alias_index = build_alias_index(db)

    unmatched_phrases = (
        find_unmatched_text(
            text,
            matches,
            alias_index,
        )
    )

    suggestions = (
        suggest_symptoms(
            unmatched_phrases,
            alias_index,
        )
    )

    if db is None:
        canonical_index = {item["code"]: item for item in load_json(CANONICAL_SYMPTOMS_PATH)}
    else:
        canonical_index = {
            item.code: {"code": item.code, "display_name": item.display_name,
                        "features": item.features, "kind": item.kind,
                        "is_red_flag": item.is_red_flag}
            for item in db.scalars(select(Symptom)).all()
        }

    recognised_symptoms = []

    for match in matches:
        code = match["code"]

        if code not in canonical_index:
            raise KeyError(
                f"Canonical symptom not found: "
                f"{code}"
            )

        symptom = canonical_index[
            code
        ]

        status, reported_subject = infer_repeated_symptom_context(
            text,
            match["matched_alias"],
            code=code,
            alias_index=alias_index,
        )

        attributes = extract_patient_attributes(
            text, match["matched_alias"], code, alias_index,
        ) if status == "present" else {
            "duration_text": None, "duration_min_days": None,
            "duration_max_days": None, "duration_unit": None, "severity": None,
        }

        recognised_symptoms.append(
            {
                "code": code,
                "display_name": symptom[
                    "display_name"
                ],
                "features": (
                    [] if status == "present" and (
                        (code == "weight_loss" and attributes.get("weight_loss_intent") != "unintentional")
                        or (code == "tiredness" and attributes.get("fatigue_pattern") not in {"persistent", "unrefreshing"})
                    ) else symptom["features"]
                ),
                "kind": symptom[
                    "kind"
                ],
                "is_red_flag": symptom[
                    "is_red_flag"
                ],
                "matched_text": match[
                    "matched_alias"
                ],
                "language": match[
                    "language"
                ],
                "match_type": match[
                    "match_type"
                ],
                "match_score": match[
                    "score"
                ],

                "status": status,
                "reported_subject": reported_subject,
                **attributes,
                "confirmed": False,
            }
        )

    has_red_flag = any(
        symptom["is_red_flag"]
        and symptom["status"] != "absent"
        and symptom["reported_subject"] != "other_person"
        for symptom in recognised_symptoms
    )

    return {
        "input_text": text,
        "recognised_symptoms": (
            recognised_symptoms
        ),
        "unmatched_wording": suggestions,
        "has_red_flag": has_red_flag,
        "absent_symptoms": [item for item in recognised_symptoms if item["status"] == "absent"],
        "uncertain_symptoms": [item for item in recognised_symptoms if item["status"] == "unknown"],
        "requires_confirmation": (
            bool(recognised_symptoms)
            or bool(suggestions)
        ),
    }

def detect_safety_signs(text):
    """Check cached bundled warnings without DB, catalogue loader or ML access."""
    flags = []
    for match in _find_alias_matches(text, _SAFETY_ALIAS_INDEX):
        code = match["code"]
        status, subject = infer_repeated_symptom_context(
            text, match["matched_alias"], code, _SAFETY_ALIAS_INDEX,
        )
        if status == "absent" or subject == "other_person":
            continue
        canonical = _SAFETY_SYMPTOMS[code]
        extra = {}
        if code == "shortness_of_breath":
            tier = classify_breathing_tier(text)
            if tier:
                extra["breathing_tier"] = tier
        flags.append({
            "code": code, "display_name": canonical["display_name"], **extra,
            "features": list(canonical["features"]), "kind": canonical["kind"],
            "is_red_flag": True, "matched_text": match["matched_alias"],
            "language": match["language"], "match_type": match["match_type"],
            "match_score": match["score"], "status": status,
            "reported_subject": subject, "confirmed": False,
            "duration_min_days": None, "duration_max_days": None,
            "duration_text": None, "duration_unit": None, "severity": None,
        })
    return flags


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print(
            'python nlp/symptom_mapper.py '
            '"I have fever and a sore throat"'
        )
        return

    text = " ".join(
        sys.argv[1:]
    )

    matches = find_symptoms(
        text
    )

    alias_index = build_alias_index()

    unmatched_phrases = (
        find_unmatched_text(
            text,
            matches,
        )
    )

    suggestions = (
        suggest_symptoms(
            unmatched_phrases,
            alias_index,
        )
    )

    print()
    print(
        "Input:",
        text,
    )

    print()
    print(
        "Recognised symptoms:"
    )

    if matches:
        for match in matches:
            print(
                "-",
                match["code"],
                "|",
                match["matched_alias"],
                "|",
                match["language"],
                "|",
                match["match_type"],
                "|",
                match["score"],
            )
    else:
        print(
            "No supported symptoms found."
        )

    print()
    print(
        "Unmatched wording:"
    )

    if not suggestions:
        print(
            "None."
        )

    for item in suggestions:
        print(
            "-",
            item["unmatched_text"],
        )

        if not item["suggestions"]:
            print(
                "  No close supported "
                "symptom suggestion."
            )
            continue

        print(
            "  Suggestions:"
        )

        for suggestion in (
            item["suggestions"]
        ):
            print(
                "  -",
                suggestion["code"],
                "|",
                suggestion[
                    "suggested_alias"
                ],
                "|",
                suggestion["language"],
                "|",
                suggestion["score"],
            )


if __name__ == "__main__":
    main()
