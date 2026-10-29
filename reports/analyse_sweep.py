"""Analyse a sweep CSV into a summary + failure list.

Derived flags are recomputed here from the raw columns (question_ids,
initial_outcome, final_outcome, final_primary, final_band,
final_present_count), not trusted from the runner's derived columns,
so a runner definition bug cannot hide a failure cluster.

Usage: python analyse_sweep.py <csv> <summary_json> <failures_json>
"""
import collections
import csv
import json
import sys


def main():
    csv_path, summary_path, failures_path = sys.argv[1:4]
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
    n = len(rows)

    def is_clear(outcome):
        return outcome == "named_primary" or outcome.startswith("family_answer")

    for r in rows:
        qids = [q for q in r["question_ids"].split(";") if q]
        r["_qids"] = qids
        r["_prompt_violation"] = 1 if (is_clear(r["initial_outcome"])
                                        and any(q != "breathing_difficulty" for q in qids)) else 0
        r["_blank"] = 1 if r["final_outcome"] == "blank" else 0
        try:
            pc = int(r["final_present_count"] or 0)
        except ValueError:
            pc = 0
        # Sparse-serious guard, as settled: neoplasm is a violation
        # only on <=3 features with NO specific supporting feature.
        # Specific codes in the mapped text, or a weight-loss-intent
        # follow-up that activates the weight-loss feature, count as
        # specific support (the CSV does not carry the final feature
        # list, so this adjudication is conservative: it only flags a
        # case where neither is present).
        _specific_codes = {"weight_loss", "coughing_blood", "chest_pain", "shortness_of_breath",
                           "heavy_sweating"}
        _mapped = {part.split(":")[0] for part in r["mapped_codes"].split(";") if part}
        _specific = bool(_mapped & _specific_codes) or "weight_loss_intent" in r["question_ids"]
        r["_sparse_neoplasm"] = 1 if (r["final_primary"] == "Pulmonary neoplasm"
                                      and pc <= 3 and not _specific) else 0
        r["_any_neoplasm"] = 1 if r["final_primary"] == "Pulmonary neoplasm" else 0
        r["_sparse_tb_strong"] = 1 if (r["final_primary"] == "Tuberculosis"
                                       and r["final_band"] == "strong" and pc <= 3
                                       and not _specific) else 0
        r["_strong_sparse"] = 1 if (r["final_outcome"] == "named_primary"
                                    and r["final_band"] == "strong" and pc <= 2) else 0
        r["_unmapped"] = 1 if not r["mapped_codes"] else 0
        r["_advice_only_question"] = 1 if any(q in ("general_duration", "symptom_severity") for q in qids) else 0

    by_outcome = collections.Counter(r["final_outcome"] for r in rows)
    by_category = {}
    for cat in sorted({r["category"] for r in rows}):
        sub = [r for r in rows if r["category"] == cat]
        by_category[cat] = {"n": len(sub), **dict(collections.Counter(r["final_outcome"] for r in sub))}
    by_pattern = {}
    for pat in sorted({r["pattern"] for r in rows}):
        sub = [r for r in rows if r["pattern"] == pat]
        by_pattern[pat] = {"n": len(sub), **dict(collections.Counter(r["final_outcome"] for r in sub))}
    by_initial = collections.Counter(r["initial_outcome"] for r in rows)
    questions = [int(r["questions_asked"] or 0) for r in rows]
    summary = {
        "n": n,
        "by_final_outcome": dict(by_outcome),
        "by_initial_outcome": dict(by_initial),
        "by_category": by_category,
        "by_pattern": by_pattern,
        "blank_count": sum(r["_blank"] for r in rows),
        "error_count": sum(1 for r in rows if r["final_outcome"] == "error"),
        "errors": [r for r in rows if r["final_outcome"] == "error"][:20],
        "prompt_first_violations_recomputed": sum(r["_prompt_violation"] for r in rows),
        "sparse_neoplasm_count": sum(r["_sparse_neoplasm"] for r in rows),
        "any_neoplasm_count": sum(r["_any_neoplasm"] for r in rows),
        "sparse_tb_strong_count": sum(r["_sparse_tb_strong"] for r in rows),
        "strong_on_sparse_count": sum(r["_strong_sparse"] for r in rows),
        "unmapped_count": sum(r["_unmapped"] for r in rows),
        "advice_only_question_cases": sum(r["_advice_only_question"] for r in rows),
        "questions_asked_total": sum(questions),
        "questions_asked_mean": round(sum(questions) / n, 2) if n else 0,
        "questions_asked_zero": sum(1 for q in questions if q == 0),
        "outcome_changed_count": sum(1 for r in rows if r["outcome_changed"] == "1"),
        "red_flag_confirm": sum(1 for r in rows if r["red_flag_stage"] == "confirm"),
        "red_flag_followup": sum(1 for r in rows if r["red_flag_stage"] == "follow_up"),
        "negation_red_flag": [r for r in rows if r["category"] == "negation"
                              and r["final_outcome"] == "red_flag_bypass"][:20],
        "exact_prompts": {},
    }
    for text in sorted({r["text"] for r in rows if r["category"] == "exact_prompts"}):
        sub = [r for r in rows if r["text"] == text]
        summary["exact_prompts"][text] = {
            pat: {"final_outcome": s["final_outcome"], "final_primary": s["final_primary"],
                  "final_band": s["final_band"], "questions_asked": s["questions_asked"],
                  "question_ids": s["question_ids"]}
            for pat, s in ((r["pattern"], r) for r in sub)}
    # Failure clusters: anything that must be 0, plus strong-on-sparse
    # observations and unmapped cases, for the fix pass.
    failures = []
    for r in rows:
        reasons = []
        if r["_blank"]:
            reasons.append("blank")
        if r["final_outcome"] == "error":
            reasons.append("error:" + r["error"])
        if r["_prompt_violation"]:
            reasons.append("prompt_first_violation")
        if r["_sparse_neoplasm"]:
            reasons.append("sparse_neoplasm")
        if r["_sparse_tb_strong"]:
            reasons.append("sparse_tb_strong")
        if r["_advice_only_question"]:
            reasons.append("advice_only_question_asked")
        if reasons:
            failures.append({"case_id": r["case_id"], "category": r["category"], "text": r["text"],
                             "language": r["language"], "pattern": r["pattern"], "age": r["age"],
                             "duration": r["duration"], "reasons": reasons,
                             "initial_outcome": r["initial_outcome"], "initial_primary": r["initial_primary"],
                             "final_outcome": r["final_outcome"], "final_primary": r["final_primary"],
                             "questions_asked": r["questions_asked"], "question_ids": r["question_ids"],
                             "mapped_codes": r["mapped_codes"]})
    summary["failure_cluster_counts"] = dict(collections.Counter(
        reason for f in failures for reason in f["reasons"]))
    summary["failure_cases_total"] = len(failures)
    summary["strong_on_sparse_examples"] = [
        {"text": r["text"], "final_primary": r["final_primary"], "final_band": r["final_band"],
         "final_present_count": r["final_present_count"], "mapped_codes": r["mapped_codes"]}
        for r in rows if r["_strong_sparse"]][:20]
    summary["unmapped_examples"] = [
        {"text": r["text"], "category": r["category"], "final_outcome": r["final_outcome"]}
        for r in rows if r["_unmapped"]][:20]
    json.dump(summary, open(summary_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(failures, open(failures_path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(json.dumps({k: summary[k] for k in
                      ("n", "by_final_outcome", "blank_count", "error_count",
                       "prompt_first_violations_recomputed", "sparse_neoplasm_count",
                       "any_neoplasm_count", "sparse_tb_strong_count", "strong_on_sparse_count",
                       "unmapped_count", "advice_only_question_cases", "questions_asked_mean",
                       "questions_asked_zero", "outcome_changed_count", "red_flag_confirm",
                       "red_flag_followup", "failure_cases_total", "failure_cluster_counts")},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
