"""Real 10,000-case sweep for RespiraCare (Eeshan, 2026-10-29).

NOT a unit-test count claim: this drives the REAL function-level
pipeline for every case -- confirm_symptoms (real NLP mapping, real
negation/subject handling) -> prepare_consultation loop (real
follow-up questions, answered per the case's pattern) ->
build_primary_assessment -- and writes one row per case to CSV, so
the count and every outcome are auditable from the file, not from a
chat message.

Outcome categories (see the summary JSON for definitions):
- red_flag_bypass: a warning sign was found at confirm or during a
  follow-up; the case never reaches a model prediction.
- named_primary: one specific condition, with its rounded match band.
- family_answer: the viral family answer (model family, or context
  family when the user only said "cold"/"flu" -- the latter has no
  model percent by design).
- withheld_with_guidance: no name, but a full withheld screen with
  title/explanation/care steps (never blank).
- blank: no name AND no withheld guidance -- a failure, must be 0.
- sparse_serious_violation: Pulmonary neoplasm named at all, or TB
  named strong, on <=3 present features with no specific supporting
  feature (weight loss, coughing blood, chest pain at rest, breathing
  difficulty, night sweats). Must be 0.
- prompt_first_violation: the initial prompt alone already gave a
  named/family result, yet follow-up questions were still asked.
  Must be 0 (safety questions are the only exception, and the
  initial build is diagnostic: in the real API a question blocks the
  result, so this measures whether a clear prompt was delayed).

Usage: python test_sweep_10000.py <batch> <seed> <out_csv> <out_summary>
  batch: "1" or "2" (batch 2 reuses the batch-1 failure set + new cases
  when reports/test_sweep_10000_1_failures.json exists; otherwise it
  generates a fresh mix). Seed changes the random sampling only.
"""
import csv
import json
import random
import sys
import time
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parents[1] / "ucs31-madhaparia-backend"
sys.path.insert(0, str(BACKEND))

from app.nlp.symptom_mapper import build_confirmation_output  # noqa: E402
from app.services.consultation import prepare_consultation  # noqa: E402
from app.services.primary_assessment import build_primary_assessment  # noqa: E402
from app.services.symptom_confirmation import confirm_symptoms  # noqa: E402

NLP = BACKEND / "app" / "nlp"
CANON = {x["code"]: x for x in json.loads((NLP / "canonical_symptoms.json").read_text())}
EN = json.loads((NLP / "english_aliases.json").read_text())
SW = json.loads((NLP / "swahili_aliases.json").read_text())
RED_FLAG_CODES = [c for c, v in CANON.items() if v.get("is_red_flag")]
ALL_CODES = list(CANON.keys())
SPARSE_SPECIFIC = {"E_162", "E_45", "E_14", "E_66", "E_50"}

ROWS = [SimpleNamespace(code=c, features=v["features"], display_name=v["display_name"])
        for c, v in CANON.items()]


class _Scalars:
    def all(self):
        return ROWS


class FakeDB:
    def scalars(self, *a, **k):
        return _Scalars()


DB = FakeDB()


def phrase(code, lang):
    aliases = (EN if lang == "en" else SW).get(code) or []
    if aliases:
        return aliases[0]
    return CANON[code]["display_name"].lower()


def make_text(codes, lang, duration=None, severity=None):
    if lang == "en":
        parts = [phrase(c, "en") for c in codes]
        text = "I have " + ", ".join(parts[:-1]) + (" and " + parts[-1] if len(parts) > 1 else parts[0] if parts else "")
        if severity:
            text = text.replace("I have ", f"I have {severity} ", 1)
        if duration == "2d":
            text += " for 2 days"
        elif duration == "14d":
            text += " for 3 weeks"
    elif lang == "sw":
        parts = [phrase(c, "sw") for c in codes]
        text = "Nina " + " na ".join(parts)
        if duration == "2d":
            text += " kwa siku 2"
        elif duration == "14d":
            text += " kwa wiki 3"
    else:  # mixed: first in Swahili, rest in English
        parts = [phrase(codes[0], "sw")] + [phrase(c, "en") for c in codes[1:]]
        text = "Nina " + " and ".join(parts)
        if duration == "2d":
            text += " for 2 days"
        elif duration == "14d":
            text += " for 3 weeks"
    return text


def answer_for(question_id, options, pattern, duration):
    values = [o["value"] for o in options]
    if question_id == "symptom_duration" or question_id == "general_duration":
        if pattern == "all-no":
            return "unknown" if "unknown" in values else values[0]
        return {"2d": "under_3_days", "14d": "over_14_days"}.get(duration, "under_3_days") \
            if "under_3_days" in values else values[0]
    if question_id == "symptom_severity":
        return "unknown" if pattern == "all-no" else "mild"
    if question_id == "fatigue_pattern":
        return "unknown" if pattern == "all-no" else "persistent"
    if question_id == "weight_loss_intent":
        return "unknown" if pattern == "all-no" else "unintentional"
    if pattern == "all-yes":
        return "yes"
    if pattern == "all-no":
        return "no"
    if pattern == "2x-unknown":
        return "unknown"
    # mixed: alternate by question order is handled by caller via index
    return "yes"


def classify_result(result):
    primary = result.get("primary_prediction")
    if primary:
        if primary.get("is_family_answer"):
            kind = "context_family" if primary.get("is_context_family_answer") else "model_family"
            return f"family_answer:{kind}", primary.get("condition"), primary.get("match_band") or "", \
                primary.get("match_percent_rounded")
        return "named_primary", primary.get("condition"), primary.get("match_band") or "", \
            primary.get("match_percent_rounded")
    steps = result.get("next_steps") or []
    if result.get("withheld_title") or steps:
        return "withheld_with_guidance", "", "", None
    return "blank", "", "", None


def run_case(case):
    # Batch-2 generator bug, fixed here: regression cases reloaded from
    # a CSV-derived JSON file carried age as a string ("30"), which
    # the V3 age-group lookup rejects as a service error. Coerce here
    # so a data-type bug in the harness can never masquerade as a
    # product failure again.
    text, pattern, age = case["text"], case["pattern"], int(case.get("age", 30))
    lang = case.get("language", "en")
    try:
        mapping = build_confirmation_output(text, None)
        present = [r["code"] for r in mapping["recognised_symptoms"]
                   if r.get("status") == "present" and r.get("reported_subject") != "other_person"]
        conf = confirm_symptoms(text, present, None)
        mapped = ";".join(f"{r['code']}:{r.get('status')}" for r in mapping["recognised_symptoms"])
        if conf["has_red_flag"]:
            return {"mapped_codes": mapped, "initial_outcome": "red_flag_bypass",
                    "initial_primary": "", "initial_band": "", "final_outcome": "red_flag_bypass",
                    "final_primary": "", "final_band": "", "final_match": "",
                    "questions_asked": 0, "question_ids": "", "red_flag_stage": "confirm",
                    "red_flag_codes": ";".join(f["code"] for f in conf["red_flag_symptoms"]),
                    "sparse_serious_violation": 0, "blank": 0, "prompt_first_violation": 0,
                    "outcome_changed": 0, "decision_reasons": "reported_warning_sign",
                    "final_present_count": len(present), "final_absent_count": 0, "error": ""}
        # Diagnostic initial build (what the initial prompt alone gives).
        prof0 = prepare_consultation(conf, [], lang, DB, age, "M")
        init = build_primary_assessment({**prof0, "assessment_context": prof0["assessment_context"]}, age, "M")
        init_outcome, init_primary, init_band, _ = classify_result(init)
        # Real follow-up loop.
        answers, qids, red_stage, red_codes = [], [], "", ""
        prof = prof0
        mixed_index = 0
        for _ in range(20):
            q = prof.get("follow_up_question")
            if not q:
                break
            qid = q["id"]
            qids.append(qid)
            if pattern == "2x-unknown" and len(answers) < 2 \
                    and "unknown" in [o["value"] for o in q["options"]]:
                # First two answers are "not sure" whatever the question
                # type is; the 2x-unknown stop in prepare_consultation
                # then ends the consultation. (Batch 1 bug, fixed here:
                # answer_for() returned informative answers for
                # duration/severity/fatigue/weight-loss questions.)
                val = "unknown"
            elif pattern == "mixed":
                val = "yes" if mixed_index % 2 == 0 else "no"
                if qid in ("symptom_duration", "general_duration", "symptom_severity",
                           "fatigue_pattern", "weight_loss_intent"):
                    val = answer_for(qid, q["options"], "all-yes", case.get("duration"))
                mixed_index += 1
            elif pattern == "2x-unknown" and len(answers) >= 2:
                val = "no" if "no" in [o["value"] for o in q["options"]] else "unknown"
            else:
                val = answer_for(qid, q["options"], pattern, case.get("duration"))
            answers.append({"question_id": qid, "answer": val})
            prof = prepare_consultation(conf, answers, lang, DB, age, "M")
            if prof.get("has_red_flag"):
                red_stage = "follow_up"
                red_codes = ";".join(f.get("code", "") for f in prof.get("red_flag_symptoms", []))
                break
        if red_stage:
            return {"mapped_codes": mapped, "initial_outcome": init_outcome,
                    "initial_primary": init_primary, "initial_band": init_band,
                    "final_outcome": "red_flag_bypass", "final_primary": "", "final_band": "",
                    "final_match": "", "questions_asked": len(qids), "question_ids": ";".join(qids),
                    "red_flag_stage": red_stage, "red_flag_codes": red_codes,
                    "sparse_serious_violation": 0, "blank": 0, "prompt_first_violation": 0,
                    "outcome_changed": 1 if init_outcome != "red_flag_bypass" else 0,
                    "decision_reasons": "reported_warning_sign",
                    "final_present_count": len(prof.get("confirmed_codes", [])),
                    "final_absent_count": len(prof.get("explicitly_absent_features", [])),
                    "error": ""}
        final = build_primary_assessment(prof, age, "M")
        outcome, primary, band, match = classify_result(final)
        present_feats = set(prof.get("model_features", []))
        violation = 0
        if primary == "Pulmonary neoplasm":
            violation = 1
        if primary == "Tuberculosis" and band == "strong" and len(present_feats) <= 3 \
                and not (present_feats & SPARSE_SPECIFIC):
            violation = 1
        # Safety is the only exception: a lone breathing_difficulty
        # question does NOT count as a prompt-first violation.
        _non_safety = [q for q in qids if q != "breathing_difficulty"]
        _init_clear = init_outcome == "named_primary" or init_outcome.startswith("family_answer")
        prompt_violation = 1 if (_init_clear and _non_safety) else 0
        return {"mapped_codes": mapped, "initial_outcome": init_outcome,
                "initial_primary": init_primary, "initial_band": init_band,
                "final_outcome": outcome, "final_primary": primary, "final_band": band,
                "final_match": "" if match is None else match,
                "questions_asked": len(qids), "question_ids": ";".join(qids),
                "red_flag_stage": "", "red_flag_codes": "",
                "sparse_serious_violation": violation, "blank": 1 if outcome == "blank" else 0,
                "prompt_first_violation": prompt_violation,
                "outcome_changed": 1 if outcome != init_outcome or primary != init_primary else 0,
                "decision_reasons": ";".join((final.get("decision") or {}).get("reasons", [])),
                "final_present_count": len(prof.get("model_features", [])),
                "final_absent_count": len(prof.get("explicitly_absent_features", [])),
                "error": ""}
    except Exception as exc:  # record, never silently drop a case
        return {"mapped_codes": "", "initial_outcome": "error", "initial_primary": "",
                "initial_band": "", "final_outcome": "error", "final_primary": "",
                "final_band": "", "final_match": "", "questions_asked": 0, "question_ids": "",
                "red_flag_stage": "", "red_flag_codes": "", "sparse_serious_violation": 0,
                "blank": 0, "prompt_first_violation": 0, "outcome_changed": 0,
                "decision_reasons": "", "final_present_count": 0, "final_absent_count": 0,
                "error": f"{type(exc).__name__}: {exc}"}


PATTERNS = ["all-yes", "all-no", "mixed", "2x-unknown"]
CLUSTERS = [
    ["headache", "sore_throat", "cough", "runny_blocked_nose"],
    ["fever", "cough", "sore_throat", "muscle_aches"],
    ["cough", "fever"],
    ["cough", "weight_loss"],
    ["tiredness", "headache"],
    ["tiredness", "headache", "fever"],
    ["headache", "tiredness", "cough"],
    ["fever", "cough", "tiredness"],
    ["cough", "sore_throat"],
    ["runny_blocked_nose", "sore_throat", "cough"],
    ["fever", "headache", "muscle_aches"],
    ["cough", "wheezing"],
    ["loss_of_smell", "cough", "fever"],
    ["loss_of_smell"],
    ["cough"],
    ["fever"],
]
EXACT = [
    ("Tiredness and headache", "en"), ("i have cold", "en"), ("I have a cold", "en"),
    ("headache, sore throat, cough, running nose", "en"),
    ("headache, tiredness and cough for 2 days", "en"),
    ("I have fever and I feel mild", "en"),
    ("Tiredness and headache and fever", "en"),
    ("Nina homa na kikohozi kwa siku mbili", "sw"),
    ("Siwezi kupumua", "sw"), ("I can't breathe", "en"),
    ("napumua kwa shida", "sw"), ("I can breathe fine and I have a cough", "en"),
    ("I feel cold", "en"), ("I have flu", "en"),
]
POOR = ["I feel bad", "something is wrong", "help me", "I am sick", "not feeling well",
        "my body is not okay", "I don't know what is wrong", "ninaumwa", "sijisikii vizuri",
        "I have pain", "I feel weak", "something", "I am unwell"]
NEGATIONS = [
    "I can breathe fine and I have a cough", "I have a cough but no fever",
    "I have a headache but I can breathe fine", "no difficulty breathing, just a cough",
    "I do not have a fever, only a cough and sore throat",
]


def generate(batch, seed):
    rng = random.Random(seed)
    cases = []

    def add(category, text, lang, pattern, age=30, duration=None):
        cases.append({"category": category, "text": text, "language": lang,
                      "pattern": pattern, "age": age, "duration": duration})

    for i, (text, lang) in enumerate(EXACT):
        for pattern in PATTERNS:
            add("exact_prompts", text, lang, pattern)
    # top up exact to 50 with pattern repeats (already 14*4=56; trim to 50)
    cases = cases[:50]
    # singles
    for i in range(1000):
        code = rng.choice(ALL_CODES)
        lang = rng.choice(["en", "sw", "mixed"])
        dur = rng.choice([None, "2d", "14d"])
        sev = rng.choice([None, "mild", "severe"]) if lang == "en" else None
        add("single", make_text([code], lang, dur, sev), lang, rng.choice(PATTERNS),
            age=rng.choice([30, 30, 30, 0, 70]), duration=dur)
    # pairs / triples / quads
    for category, n, k in (("pair", 2200, 2), ("triple", 2200, 3), ("quad", 1000, 4)):
        for i in range(n):
            codes = rng.sample(ALL_CODES, k)
            lang = rng.choice(["en", "sw", "mixed"])
            dur = rng.choice([None, "2d", "14d"])
            add(category, make_text(codes, lang, dur), lang, rng.choice(PATTERNS), duration=dur)
    # common clusters
    for i in range(1200):
        codes = rng.choice(CLUSTERS)
        lang = rng.choice(["en", "sw", "mixed"])
        dur = rng.choice([None, "2d", "14d"])
        add("common_cluster", make_text(codes, lang, dur), lang, rng.choice(PATTERNS), duration=dur)
    # red flags
    for i in range(700):
        code = rng.choice(RED_FLAG_CODES)
        lang = rng.choice(["en", "sw"])
        extra = rng.choice([[], [rng.choice(ALL_CODES)]])
        add("red_flag", make_text([code] + extra, lang), lang, rng.choice(PATTERNS))
    # negations
    for i in range(500):
        add("negation", rng.choice(NEGATIONS), "en", rng.choice(PATTERNS))
    # duration / severity variants of fixed sets
    fixed = [["cough"], ["cough", "fever"], ["cough", "weight_loss"], ["headache", "tiredness"],
             ["fever", "cough", "sore_throat"]]
    for i in range(600):
        codes = rng.choice(fixed)
        dur = rng.choice(["2d", "14d"])
        sev = rng.choice(["mild", "severe"])
        add("duration_severity", make_text(codes, "en", dur, sev), "en",
            rng.choice(PATTERNS), duration=dur)
    # context words
    for i in range(300):
        code = rng.choice(["common_cold", "flu_like", "dizziness"])
        extra = rng.choice([[], [rng.choice(["cough", "fever", "sore_throat"])]])
        _lang = rng.choice(["en", "sw"])
        add("context", make_text([code] + extra, _lang), _lang, rng.choice(PATTERNS))
    # poor / unusable
    for i in range(250):
        add("poor_unusable", rng.choice(POOR), "en", rng.choice(["all-no", "2x-unknown"]))
    assert len(cases) == 10000, len(cases)
    if batch == "2":
        # Batch 2 mix: batch-1 failures (regressions) + exact prompts +
        # fresh random cases, totalling 10,000. Failure cases are stored
        # by the batch-1 analysis step in *_failures.json.
        fail_path = Path(__file__).resolve().parent / "test_sweep_10000_1_failures.json"
        kept = []
        if fail_path.exists():
            kept = json.loads(fail_path.read_text())
        mix = []
        for item in kept:
            mix.append({"category": "batch1_regression", "text": item["text"],
                        "language": item.get("language", "en"),
                        "pattern": item.get("pattern", "all-no"),
                        "age": item.get("age", 30), "duration": item.get("duration")})
        for item in cases[:50]:  # exact prompts again
            mix.append(item)
        while len(mix) < 10000:
            codes = rng.sample(ALL_CODES, rng.choice([1, 2, 3, 4]))
            lang = rng.choice(["en", "sw", "mixed"])
            dur = rng.choice([None, "2d", "14d"])
            mix.append({"category": "batch2_fresh", "text": make_text(codes, lang, dur),
                        "language": lang, "pattern": rng.choice(PATTERNS), "duration": dur})
        cases = mix[:10000]
    return cases


def main():
    batch, seed, out_csv, out_summary = sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4]
    cases = generate(batch, seed)
    fields = ["case_id", "category", "text", "language", "pattern", "age", "duration",
              "mapped_codes", "initial_outcome", "initial_primary", "initial_band",
              "final_outcome", "final_primary", "final_band", "final_match",
              "questions_asked", "question_ids", "red_flag_stage", "red_flag_codes",
              "sparse_serious_violation", "blank", "prompt_first_violation",
              "outcome_changed", "decision_reasons", "final_present_count",
              "final_absent_count", "error"]
    t0 = time.time()
    with open(out_csv, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for idx, case in enumerate(cases, 1):
            row = run_case(case)
            writer.writerow({"case_id": idx, **{k: case.get(k, "") for k in
                                                 ("category", "text", "language", "pattern", "age", "duration")},
                             **row})
            if idx % 1000 == 0:
                print(f"{idx} cases in {time.time()-t0:.0f}s", flush=True)
    print(f"Done {len(cases)} cases in {time.time()-t0:.0f}s -> {out_csv}", flush=True)


if __name__ == "__main__":
    main()
