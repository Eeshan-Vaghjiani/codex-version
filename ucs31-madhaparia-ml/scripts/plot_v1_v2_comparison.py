
"""Generate V1 vs V2 comparison figures for Issue #29."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]

REPORTS = ROOT / "reports/comparison_v1_v2"
FIGURES = REPORTS / "figures"

FIGURES.mkdir(parents=True, exist_ok=True)


def save_full_input_chart():
    data = pd.read_csv(
        REPORTS / "comparison_metrics.csv"
    )

    metrics = ["accuracy", "macro_f1"]

    labels = ["Accuracy", "Macro F1"]

    v1 = [
        data.loc[data["metric"] == name, "v1"].iloc[0] * 100
        for name in metrics
    ]

    v2 = [
        data.loc[data["metric"] == name, "v2"].iloc[0] * 100
        for name in metrics
    ]

    x = range(len(metrics))
    width = 0.35

    fig, ax = plt.subplots(figsize=(8, 5))

    bars1 = ax.bar(
        [i - width / 2 for i in x],
        v1,
        width,
        label="V1",
    )

    bars2 = ax.bar(
        [i + width / 2 for i in x],
        v2,
        width,
        label="V2",
    )

    ax.set_xticks(list(x), labels)
    ax.set_ylim(0, 110)
    ax.set_ylabel("Score (%)")
    ax.set_title(
        "V1 vs V2: Full-Input Validation Performance"
    )
    ax.legend()
    ax.grid(axis="y", alpha=0.2)

    ax.bar_label(bars1, fmt="%.2f%%", padding=3)
    ax.bar_label(bars2, fmt="%.2f%%", padding=3)

    fig.text(
        0.5,
        0.015,
        "55,808 simulated DDXPlus cases; "
        "different model feature representations",
        ha="center",
        fontsize=9,
    )

    fig.tight_layout(rect=[0, 0.06, 1, 1])

    path = FIGURES / "v1_v2_full_input.png"

    fig.savefig(path, dpi=200)
    plt.close(fig)

    print("Saved:", path)


def save_sparse_charts():
    data = pd.read_csv(
        REPORTS / "sparse_all_conditions_metrics.csv"
    )

    for metric, title, filename in [
        (
            "accuracy",
            "Accuracy",
            "v1_v2_sparse_accuracy.png",
        ),
        (
            "macro_f1",
            "Macro F1-score",
            "v1_v2_sparse_macro_f1.png",
        ),
    ]:
        fig, ax = plt.subplots(figsize=(8, 5))

        for model in ("V1", "V2"):
            subset = data[
                data["model"] == model
            ].sort_values(
                "maximum_reported_symptoms"
            )

            x = subset[
                "maximum_reported_symptoms"
            ].to_numpy()

            y = subset[metric].to_numpy() * 100

            ax.plot(
                x,
                y,
                marker="o",
                linewidth=2,
                label=model,
            )

            for xi, yi in zip(x, y):
                ax.annotate(
                    f"{yi:.2f}%",
                    (xi, yi),
                    xytext=(0, 9),
                    textcoords="offset points",
                    ha="center",
                    fontsize=9,
                )

        ax.set_xticks([1, 2, 3])
        ax.set_xlim(0.8, 3.2)
        ax.set_ylim(0, 100)

        ax.set_xlabel(
            "Maximum number of reported symptoms"
        )

        ax.set_ylabel(f"{title} (%)")

        ax.set_title(
            f"V1 vs V2: Sparse-Input {title}"
        )

        ax.legend()
        ax.grid(alpha=0.2)

        fig.text(
            0.5,
            0.015,
            "55,808 simulated DDXPlus cases; "
            "all 21 original conditions included",
            ha="center",
            fontsize=9,
        )

        fig.tight_layout(rect=[0, 0.06, 1, 1])

        path = FIGURES / filename

        fig.savefig(path, dpi=200)
        plt.close(fig)

        print("Saved:", path)


def main():
    print("ISSUE 29 - COMPARISON FIGURES")
    print("------------------------------------")

    save_full_input_chart()
    save_sparse_charts()

    print("\nStep 27 PASSED!")


if __name__ == "__main__":
    main()
