"""Reusable measured charts and report; does not select or tune the policy."""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.ticker import PercentFormatter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from inference.primary_selection import classify_primary
from inference.v3_predictor import load_v3_bundle, predict_v3
from scripts.evaluate_primary_selection import OUT, accept_vectorized, cohorts, dump
from scripts.train_v3_partial_evidence import CLASSES, FEATURES, masks, score, subset

BLUE, TEAL, GRAY = "#315A7D", "#268279", "#697586"
NAMES = {
    "1_positive_0_negative": "1 present\n0 absent",
    "2_positive_0_negative": "2 present\n0 absent",
    "3_positive_0_negative": "3 present\n0 absent",
    "3_positive_3_negative": "3 present\n3 absent",
    "8_positive_0_negative": "≤8 present\n0 absent",
    "8_positive_5_negative": "≤8 present\n5 absent",
}
FOCUS = "3_positive_0_negative"
NOTE = "DDXPlus simulated source · 21 classes · same 53,386 eligible held-out records per scenario · no Kenyan clinical validation"


def save(fig, name):
    fig.savefig(OUT / f"{name}.png", dpi=180, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{name}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def note(fig, text=NOTE):
    # Reserve real layout space for footnotes; text outside the axes otherwise
    # collides with multi-line evidence labels in standalone exports.
    fig.get_layout_engine().set(rect=(0, .11, 1, .89))
    fig.text(.01, .01, text, fontsize=9, color=GRAY)


def comparison_figures(report):
    old, new = report["baseline"]["test"][FOCUS], report["improved_test"][FOCUS]
    labels = ["Underlying\ntop-1 accuracy", "Prediction\ncoverage", "Accuracy among\nshown primaries", "Correct primary /\nall cases"]
    keys = ["underlying_top1_accuracy", "coverage", "selective_accuracy", "correct_primary_per_all_cases"]
    fig, ax = plt.subplots(figsize=(10, 5), layout="constrained")
    x = np.arange(len(keys))
    for shift, data, color, name in ((-.18, old, BLUE, "Original V3"), (.18, new, TEAL, "V3 + selective policy")):
        bars = ax.bar(x+shift, [data[key] for key in keys], width=.35, color=color, label=name)
        ax.bar_label(bars, labels=[f"{100*data[key]:.1f}%" for key in keys], padding=3, fontsize=10)
    ax.set(xticks=x, xticklabels=labels, ylim=(0, 1.12), ylabel="Metric value (denominator labeled below)",
           title="Higher reliability among shown results trades away coverage\n3 present symptoms, all other features unmentioned")
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="upper right", frameon=False)
    ax.grid(axis="y", alpha=.15)
    ax.set_axisbelow(True)
    note(fig)
    save(fig, "01_metrics_comparison")

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for ax, title, prefix in ((axes[0], "Unchanged model on all cases", "underlying_macro_"),
                              (axes[1], "Decision output on the same full cohort\nAbstentions counted as false negatives", "macro_")):
        for shift, data, color, name in ((-.18, old, BLUE, "Original V3"), (.18, new, TEAL, "V3 + selective policy")):
            keys = [prefix+k+("_including_abstention" if prefix == "macro_" else "") for k in ("precision", "recall", "f1")]
            vals = [data[k] for k in keys]
            bars = ax.bar(np.arange(3)+shift, vals, width=.35, color=color, label=name)
            ax.bar_label(bars, labels=[f"{v:.3f}" for v in vals], padding=3, fontsize=9)
        ax.set(xticks=np.arange(3), xticklabels=["Precision", "Recall", "F1"], ylim=(0, 1.05), title=title, ylabel="Macro average across all 21 classes")
        ax.grid(axis="y", alpha=.15)
        ax.set_axisbelow(True)
    axes[0].legend(loc="upper left", frameon=False)
    fig.suptitle("One primary result does not improve the model's learned discrimination", fontsize=14)
    note(fig)
    save(fig, "02_precision_recall_f1")


def confusion_figure():
    fig, axes = plt.subplots(1, 2, figsize=(22, 11), layout="constrained")
    for ax, prefix, title in ((axes[0], "baseline_test", "Original V3 top-1"), (axes[1], "improved_test", "V3 + selective primary / abstain")):
        frame = pd.read_csv(OUT / f"{prefix}_{FOCUS}_confusion.csv", index_col=0)
        values = frame.to_numpy()
        normalized = values/np.maximum(values.sum(axis=1, keepdims=True), 1)
        im = ax.imshow(normalized, vmin=0, vmax=1, cmap="Blues", aspect="auto")
        ax.set(xticks=np.arange(22), xticklabels=CLASSES+["ABSTAIN"], yticks=np.arange(21), yticklabels=CLASSES,
               xlabel="Predicted class / abstention", ylabel="True simulated source class", title=title)
        ax.tick_params(axis="x", labelrotation=90, labelsize=7)
        ax.tick_params(axis="y", labelsize=8)
        ax.axvline(20.5, color="#D38536", linewidth=1)
        for i, j in zip(*np.where(normalized >= .1)):
            ax.text(j, i, f"{normalized[i,j]:.0%}", ha="center", va="center", color="white" if normalized[i,j] > .55 else "#172B4D", fontsize=7)
    fig.colorbar(im, ax=axes, shrink=.7, label="Fraction within true class (each row sums to 100%)")
    fig.suptitle("Matched confusion matrices: 3 present symptoms, 0 explicitly absent", fontsize=17)
    note(fig)
    save(fig, "03_confusion_matrices")


def coverage_calibration_figures(report, data):
    fig, ax = plt.subplots(figsize=(10, 6), layout="constrained")
    bundle = load_v3_bundle()
    curves = {}
    for count, negatives, color in ((1, 0, GRAY), (3, 0, BLUE), (8, 5, TEAL)):
        p, a = masks(data, count, negatives)
        eligible = p.sum(axis=1) > 0
        values = score(bundle, p[eligible], a[eligible], subset(data, eligible))
        confidence, correct = values.max(axis=1), values.argmax(axis=1) == data["y"][eligible]
        # Complete tie groups preserve attainable score thresholds. The curve
        # is descriptive sensitivity analysis on test, never policy selection.
        order = np.argsort(-confidence, kind="stable")
        ordered = confidence[order]
        ends = np.flatnonzero(np.r_[ordered[1:] != ordered[:-1], True])
        counts, cumulative = ends+1, correct[order].cumsum()[ends]
        coverage, accuracy = counts/len(correct), cumulative/counts
        key = f"{count}_positive_{negatives}_negative"
        ax.plot(coverage, accuracy, color=color, linewidth=1.8, label=NAMES[key].replace("\n", "; "))
        deployed = report["improved_test"][key]
        if deployed["coverage"]:
            ax.scatter(deployed["coverage"], deployed["selective_accuracy"], color=color, s=130, marker="*", edgecolors="black", zorder=4)
        curves[key] = [{"score_threshold": float(ordered[end]), "coverage": float(cov), "selective_accuracy": float(acc)}
                       for end, cov, acc in zip(ends, coverage, accuracy)]
    ax.axhline(.9, color="#AD752D", linestyle="--", linewidth=1, label="Declared 90% simulated source target")
    ax.set(xlim=(0, 1.02), ylim=(0, 1.02), xlabel="Prediction coverage", ylabel="Accuracy among selected predictions",
           title="Coverage versus selective accuracy\nLines: descriptive single-score thresholds; stars: frozen policy + scope")
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.yaxis.set_major_formatter(PercentFormatter(1))
    ax.legend(loc="lower left", frameon=False)
    ax.grid(alpha=.15)
    note(fig, NOTE+"\nStars differ from score-only curves: frozen buckets and the fixed respiratory scope filter also control selection.")
    save(fig, "04_coverage_selective_accuracy")
    dump(OUT / "coverage_curves.json", curves)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
    for key, color in (("1_positive_0_negative", GRAY), ("3_positive_0_negative", BLUE), ("8_positive_5_negative", TEAL)):
        row = report["baseline"]["test"][key]
        bins = [b for b in row["reliability_bins"] if b["count"]]
        axes[0].plot([b["mean_score"] for b in bins], [b["accuracy"] for b in bins], marker="o", color=color, label=NAMES[key].replace("\n", "; "))
    axes[0].plot([0, 1], [0, 1], "--", color="#A4ABB4", label="Perfect source-score calibration")
    axes[0].set(xlim=(0, 1), ylim=(0, 1), xlabel="Mean top relative score in bin", ylabel="Observed top-1 correctness", title="Calibration varies with evidence completeness")
    axes[0].legend(loc="upper left", fontsize=8, frameon=False)
    x = np.arange(len(NAMES))
    axes[1].bar(x, [report["baseline"]["test"][key]["underlying_top_label_ece_10_equal_width_bins"] for key in NAMES], color=BLUE)
    axes[1].set(xticks=x, xticklabels=list(NAMES.values()), ylabel="Top-label expected calibration error (10 bins)", title="Underlying ECE is identical before and after")
    axes[1].tick_params(axis="x", labelsize=8)
    axes[1].set_ylim(0, .12)
    note(fig)
    save(fig, "06_source_score_calibration")


def synthetic_suite():
    cases = [
        ("Headache alone", ["E_53", "E_55_@_V_89"], []),
        ("Tiredness alone", ["E_89"], []),
        ("Headache and tiredness", ["E_53", "E_55_@_V_89", "E_89"], []),
        ("Mild fever and headache", ["E_91", "E_53", "E_55_@_V_89"], []),
        ("Cough and sore throat", ["E_201", "E_97"], []),
        ("Fever, cough, sore throat, body aches", ["E_91", "E_201", "E_97", "E_144"], []),
        ("Fever alone", ["E_91"], []),
        ("Cough alone", ["E_201"], []),
        ("Sore throat alone", ["E_97"], []),
        ("Body aches alone", ["E_144"], []),
        ("Itchy nose and itchy eyes", ["E_169", "E_170"], []),
        ("Coughing fits and vomiting after cough", ["E_203", "E_166"], []),
        ("Empty evidence", [], []),
        ("Explicit no fever; no positive symptom", [], ["E_91"]),
        ("Unsupported native feature", ["not_a_model_feature"], []),
        ("Contradictory fever", ["E_91"], ["E_91"]),
        ("Potential emergency: breathlessness and chest pain", ["E_66", "E_53", "E_55_@_V_101"], []),
    ]
    rows = []
    for text, present, absent in cases:
        row = {"input_description": text, "present": present, "absent": absent, "age": 25, "sex": "F",
               "ground_truth": None, "type": "handcrafted native-feature software-behavior probe"}
        for name, function in (("original", predict_v3), ("improved", classify_primary)):
            try:
                row[name] = function(present, absent, 25, "F")
            except ValueError as error:
                row[name] = {"status": "invalid", "error": str(error)}
        rows.append(row)
    result = {"note": "No clinical reference labels or reviewed triage outcomes. Counts describe label emission and abstention, not unsupported-disease errors, diagnostic accuracy, or safety. Explicit feature mapping is specified; this bypasses free-text NLP and API clinical scope/emergency gates. Mild severity is not an input learned by V3. Use separate full-application tests for mappings, urgency, and the primary display.", "cases": rows}
    dump(OUT / "synthetic_native_feature_suite.json", result)
    vague = rows[:10]
    original_count = sum(bool(row["original"].get("predictions")) for row in vague)
    improved_count = sum(row["improved"]["status"] == "eligible" for row in vague)
    fig, ax = plt.subplots(figsize=(8, 4.5), layout="constrained")
    bars = ax.bar(["Original V3", "V3 + selective policy"], [original_count, improved_count], color=[BLUE, TEAL], width=.5)
    ax.bar_label(bars, labels=[f"{original_count} / {len(vague)}", f"{improved_count} / {len(vague)}"], padding=4)
    ax.set(ylim=(0, len(vague)+2), ylabel="Probes emitting a specific condition name",
           title="Native-feature behavior on ten vague-symptom probes\nHandcrafted cases without disease ground truth")
    note(fig, "Software behavior only · fixed age 25, sex F · no accuracy or safety claim · API safety gates tested separately")
    save(fig, "05_vague_symptom_behavior")
    return result


def pct(value):
    return "N/A (no selected cases)" if value is None else f"{100*value:.2f}%"


def write_report(report, suite):
    base, new = report["baseline"]["test"][FOCUS], report["improved_test"][FOCUS]
    enabled = sum(x["enabled"] for x in report["policy"]["buckets"].values())
    lines = ["# Current V3 versus selective primary result: measured evaluation", "",
        "The V3 model is unchanged. The new decision rule shows one possible condition only for selected source-like evidence patterns and otherwise asks for more information. Improved accuracy among selected cases is obtained by abstaining; learned model accuracy, probability calibration and class coverage have not improved. These are simulated DDXPlus results, not validation on Kenyan patients.", "",
        "## Baseline and independent source partitions", "",
        "Original means the currently integrated V3 age-stratified missing-evidence likelihood model, before this request. It uses 34 native features and 21 source classes, age groups with shrinkage 1000 and temperature 0.75 selected previously on tuning NLL. It marginalizes unmentioned features; only explicit no responses become negative evidence. It previously emitted three rankings for any positive feature and marked every result uncertain. The artifact SHA-256 remains `"+report["model_sha256"]+"`.", "",
        "Original source training: 443,075 rows. Original tuning: 26,477 rows; 26,432 unique full-198-feature source profiles select policy thresholds. Previously reporting-only validation is split by full source signature: `%4 == 1` gives 13,507 unique profiles for checking the frozen thresholds; `%4 == 3` gives 12,905 unique profiles for separate reporting validation. One first row per profile is chosen without inspecting its label. Whole original source-validation signatures remain excluded from test. Test retains 53,387 records / 53,273 unique profiles; one record has no supported positive feature. Matched disease-ranking results use the same 53,386 positive-evidence cases as the earlier V3 evaluation; both systems decline a disease for the remaining record.", "",
        "Source duplicates cannot cross training, tuning, independent bound checking, reporting validation or test. Each calibration bucket has exactly one deterministic masked view per unique source profile. The same source may contribute to different buckets; multiple-testing correction does not require independence between buckets. Different sparse scenarios are separate experiments on overlapping test cases and must never be added as independent patients.", "",
        "## Policy and interpretation", "",
        f"A declared engineering target of at most 10% error among selected simulated-source predictions drives threshold selection. This is a research risk budget, not an accepted medical threshold or a patient confidence percentage. For each of 48 exact evidence-count buckets (1–8 positive; 0–5 explicit negative), original tuning selects the score threshold with maximum coverage whose exploratory one-sided 95% exact-binomial bound meets that target. Complete score ties stay together. That chosen threshold is frozen before independently checking it on the separate source-profile cohort. A one-sided Clopper–Pearson error upper bound uses delta=0.05/48. A bucket is enabled only if that bound is ≤0.10; {enabled}/48 passed. Failed buckets are disabled without retuning. The family-wise 95% interpretation requires independent exchangeable source profiles and the same sparse reporting mechanism. It is not a clinical guarantee.", "",
        "The portable function `classify_primary(present, absent, age, sex)` returns eligible / uncertain / no_information, at most one condition, reasons, evidence counts, and internal diagnostics. It removes relative scores from its primary-result object. Unsupported evidence-count combinations abstain. Contradictory native evidence and unsupported features are rejected for correction. A fixed complaint-domain gate also requires a present respiratory anchor: generic fever, pain, muscle aches and fatigue alone cannot identify that the complaint is in the model's respiratory scope. This scope filter was specified from the supported complaint domain, without tuning thresholds on test outcomes. It is not a disease exclusion or triage test. Language confirmation and emergency gates remain separate application requirements.", "",
        "The source-profile bound checks above concern the original pre-scope bucket policy. Filtering that selected cohort by respiratory scope changes the conditional error population, so the original bound is not automatically inherited. Actual scoped-policy metrics are reported below, with the pre-scope results shown separately for transparency. `scoped_calibration_diagnostics` records post-filter source-profile counts and bounds. A separate `v3_primary_scope.json` override disables bucket 1:4 (one positive / four negatives), whose scoped source-validation upper error bound was 0.1042336 and exceeded the declared 0.10 target. Anchors were fixed from the complaint domain before reviewing this scoped calibration result. No score threshold changed; reporting-validation and test labels never choose this override. Additional application language, severity and emergency gates are not measured by these source checks, so no clinical or full-application risk guarantee is claimed.", "",
        "Calibration was evaluated, not assumed. V3 already has a tuning-selected temperature; it was retained. ECE changes with evidence completeness and does not validate a score for an individual patient. No new percentage is exposed to patients. Split conformal was considered, but it would require separate calibration independent of V3 selection and its marginal set coverage would not by itself certify accuracy conditional on singleton selection; direct source-profile selective-risk checks address the stated output decision more directly.", "",
        "## Matched headline comparison", "",
        "Three present symptoms and no explicitly absent features; N=53,386 in both columns. Macro averages include all 21 classes, including classes with no accepted primary. For the full decision-output precision/recall/F1, an abstention is a false negative for the true class. Accepted-only precision/recall/F1 are additional diagnostic fields, not replacements for these full-cohort results.", "",
        "| Metric | Original V3 | V3 + selective policy | Change | Interpretation |",
        "|---|---:|---:|---:|---|",
    ]
    fields = [("Underlying top-1 accuracy", "underlying_top1_accuracy", "Unchanged frozen model"),
              ("Underlying top-3 accuracy", "underlying_top3_accuracy", "Ranking benchmark only; three labels no longer shown"),
              ("Macro precision, full decision output", "macro_precision_including_abstention", "All 21 classes; abstentions are excluded from predicted positives"),
              ("Macro recall, full decision output", "macro_recall_including_abstention", "All cases; abstentions count as missed true classes"),
              ("Macro F1, full decision output", "macro_f1_including_abstention", "All cases, all 21 classes"),
              ("Macro specificity on accepted cases", "macro_specificity_on_accepted", "One-vs-rest diagnostic; changes cohort and is not triage specificity"),
              ("Prediction coverage", "coverage", "Fewer cases receive a disease label"),
              ("Selective accuracy", "selective_accuracy", "Accuracy conditional on a displayed primary"),
              ("Abstention rate", "abstention_rate", "No condition name; uncertainty is not reassurance"),
              ("Correct primary / all cases", "correct_primary_per_all_cases", "Prevents selective accuracy being mistaken for full-population accuracy")]
    for title, key, meaning in fields:
        change = "N/A" if base[key] is None or new[key] is None else f"{100*(new[key]-base[key]):+.2f} pp"
        lines.append(f"| {title} | {pct(base[key])} | {pct(new[key])} | {change} | {meaning} |")
    for title, key in (("Top-label ECE (10 equal-width bins)", "underlying_top_label_ece_10_equal_width_bins"), ("Multiclass Brier score (sum over classes)", "underlying_multiclass_brier"), ("Multiclass log loss", "underlying_log_loss")):
        lines.append(f"| {title} | {base[key]:.4f} | {new[key]:.4f} | {new[key]-base[key]:+.4f} | Same source-relative score distribution; lower is better |")
    lines += ["", "## Trade-off across all matched scenarios", "", "| Reported evidence | Cases | Original top-1 | Original top-3 | New coverage | New selective accuracy | New abstention |", "|---|---:|---:|---:|---:|---:|---:|"]
    for name in NAMES:
        original, improved = report["baseline"]["test"][name], report["improved_test"][name]
        lines.append(f"| {NAMES[name].replace(chr(10), '; ')} | {original['cases']:,} | {pct(original['underlying_top1_accuracy'])} | {pct(original['underlying_top3_accuracy'])} | {pct(improved['coverage'])} | {pct(improved['selective_accuracy'])} | {pct(improved['abstention_rate'])} |")
    lines += ["", "Scoped results above include the actual portable respiratory-domain filter. The same frozen score policy before that filter gives:", "", "| Reported evidence | Pre-scope coverage | Pre-scope selective accuracy | Scoped coverage | Scoped selective accuracy |", "|---|---:|---:|---:|---:|"]
    for name in NAMES:
        model_only, improved = report["model_only_improved_test"][name], report["improved_test"][name]
        lines.append(f"| {NAMES[name].replace(chr(10), '; ')} | {pct(model_only['coverage'])} | {pct(model_only['selective_accuracy'])} | {pct(improved['coverage'])} | {pct(improved['selective_accuracy'])} |")
    lines += ["", "The exact 3-positive / 3-negative bucket failed the independent source-validation bound and remains disabled; its complete abstention is intentional. Some other counts are similarly disabled. Eight-positive scenarios mean up to eight features: source cases with fewer positives use their exact observed-count policy. More symptoms or negative answers need not monotonically enable a primary result; different buckets have different source evidence and independent checks.", "",
        "All full matrices and per-class precision/recall/F1, true support, accepted support, coverage, abstentions and one-vs-rest accepted specificity are exported to CSV. Low class-specific recall and coverage remain visible. High macro specificity in a 21-class task is dominated by many one-vs-rest negatives; it is not evidence of safe exclusion of serious disease.", "",
        "## Class composition and coverage for the headline scenario", "",
        "The same true-class composition is used before and after selection. These are source labels, not Kenyan disease frequencies. Coverage is the fraction of true-class cases allowed a primary; recall counts all cases including abstentions.", "",
        "| Simulated source class | Test cases | Primary coverage | Recall including abstention |",
        "|---|---:|---:|---:|"]
    per_class = pd.read_csv(OUT / f"improved_test_{FOCUS}_per_class.csv", index_col=0)
    per_class.loc[CLASSES].to_csv(OUT / "headline_class_composition_and_coverage.csv")
    for label in CLASSES:
        row = per_class.loc[label]
        lines.append(f"| {label} | {int(row['support']):,} | {pct(row['coverage'])} | {pct(row['recall'])} |")
    lines += ["",
        "## Handcrafted vague-symptom behavior", "",
        "Ten native-feature vague probes produce specific labels in 10/10 original V3 outputs and 0/10 selective outputs. These are behavior counts, not unsupported-disease error rates: no clinical diagnosis or reviewed reference outcome exists for these descriptions. They cannot establish diagnostic accuracy, missed emergencies, appropriate reassurance or unnecessary escalation. The native suite explicitly records inputs and includes the native respiratory-anchor filter; it bypasses NLP, additional API input-context and emergency gates, which require full application tests. The two informative probes still emit one possible source condition when the source policy allows it.", "",
        "| Native probe | Original top-3 ranking | Selective result |",
        "|---|---|---|"]
    for row in suite["cases"]:
        original = "; ".join(p["condition"] for p in row["original"].get("predictions", [])) or row["original"]["status"]
        improved = row["improved"]
        primary = improved.get("primary_prediction")
        display = primary["condition"] if primary else improved["status"]
        lines.append(f"| {row['input_description']} | {original} | {display} |")
    lines += ["", "## Visualizations", "",
        "![Metric comparison](01_metrics_comparison.png)", "",
        "![Macro precision recall F1](02_precision_recall_f1.png)", "",
        "![Matched confusion matrices](03_confusion_matrices.png)", "",
        "![Coverage versus accuracy](04_coverage_selective_accuracy.png)", "",
        "![Vague native probes](05_vague_symptom_behavior.png)", "",
        "![Source score calibration](06_source_score_calibration.png)", "",
        "All figures also have reusable SVG exports. Coverage curves are descriptive test sensitivity analyses; no threshold is chosen from them.", "",
        "## Reproduce", "", "From the ML repository, using its installed virtual environment:", "", "```powershell",
        ".venv/Scripts/python.exe scripts/evaluate_primary_selection.py --baseline",
        ".venv/Scripts/python.exe scripts/evaluate_primary_selection.py",
        ".venv/Scripts/python.exe scripts/render_primary_selection_report.py",
        ".venv/Scripts/python.exe -m pytest tests -q",
        "```", "",
        "For report reproduction without refitting selection, use `evaluate_primary_selection.py --evaluate-only`. The unchanged V3 hash, separate frozen score-policy hash, and scope-override hash are recorded. The first run reads source CSVs and caches compact cohorts in `data/processed/primary_selection_cache`; later runs validate source file size/mtime/schema before reusing that cache. Source CSVs and the ignored local cache are not redistributed. Labels and masks come from authentic simulated source data, never fabricated disease ground truth. Statistical metrics are deterministic; PNG/SVG file metadata can vary between renders. Use the explicit `tests` directory: bare pytest collection currently also discovers a pre-existing non-UTF8 readable data text file as a doctest and fails decoding it.", "",
        "## Remaining limitations and decisions requiring review", "",
        "The source generator's disease frequencies and New York census assumptions do not represent Kenyan prevalence. Many locally important diagnoses, including malaria, are not in these 21 classes; an apparently decisive closed-set score can be wrong outside the vocabulary. Random masking of complete simulated evidence differs from human symptom reporting. Severity and duration are not learned model inputs. There is no Kenyan cohort, clinician-reviewed symptom vignette set, validated emergency reference, prospective safety outcome study or patient comprehension study. The predeclared 90% source target needs clinical governance before any patient use; disabling failed buckets is a software safeguard, not proof of safety. Local prospective data, mapping review, subgroup analysis, triage review and prevalence-shift validation are required before a clinical claim.", "",
        "## Method references", "",
        "- [DDXPlus original dataset paper](https://proceedings.neurips.cc/paper_files/paper/2022/hash/cae73a974390c0edd95ae7aeae09139c-Abstract.html): simulated records and the limits of source-only evidence. [Full paper](https://papers.nips.cc/paper/2022/file/cae73a974390c0edd95ae7aeae09139c-Paper-Datasets_and_Benchmarks.pdf), section 3.2 describes generation and demographic assumptions.",
        "- [NIST exact binomial confidence limits](https://itl.nist.gov/div898/software/dataplot/refman2/auxillar/exacbino.htm): one-sided error-bound method; combined here with separate source-profile checks and Bonferroni correction.",
        "- [Selective Classification for Deep Neural Networks, Geifman and El-Yaniv (2017)](https://proceedings.neurips.cc/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html): selective prediction trades coverage for lower error; this implementation retains the existing likelihood model.",
        "- [Classification with Valid and Adaptive Coverage, Romano et al. (2020)](https://proceedings.neurips.cc/paper_files/paper/2020/hash/244edd7e85dc81602b7615cd705545f5-Abstract.html): alternative set-valued uncertainty method; marginal prediction-set coverage is distinct from selected-only correctness.", ""]
    (OUT / "EVALUATION_REPORT.md").write_text("\n".join(lines), encoding="utf8")


def main():
    plt.rcParams.update({"font.family": "DejaVu Sans", "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "semibold", "font.size": 10})
    report = json.loads((OUT / "evaluation.json").read_text())
    data, _ = cohorts()
    comparison_figures(report)
    confusion_figure()
    coverage_calibration_figures(report, data["test"])
    suite = synthetic_suite()
    write_report(report, suite)
    print("Six measured charts (PNG + SVG), native probe JSON, curves and evaluation report written to", OUT)


if __name__ == "__main__":
    main()
