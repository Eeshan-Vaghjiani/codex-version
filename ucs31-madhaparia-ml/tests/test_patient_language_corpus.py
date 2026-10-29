"""Everyday language software contracts; no synthetic disease labels."""
import json
from pathlib import Path

import pytest

from test_autonomous_nlp_regressions import mapper


CORPUS = json.loads((Path(__file__).with_name("fixtures") / "patient_utterances.json").read_text(encoding="utf8"))


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda case: case["id"])
def test_everyday_patient_language_contract(mapper, case):
    result = mapper.build_confirmation_output(case["text"])
    symptoms = {item["code"]: item for item in result["recognised_symptoms"]}
    assert {code: item["status"] for code, item in symptoms.items()} == case["expected_states"], case["purpose"]
    for code, expected in case["expected_attributes"].items():
        for attribute, value in expected.items():
            assert symptoms[code].get(attribute) == value, (code, attribute, case["purpose"])
    for code, features in case["expected_features"].items():
        assert symptoms[code]["features"] == features, case["purpose"]
    assert all("disease" not in item for item in symptoms.values())


def test_corpus_provenance_and_coverage():
    assert "synthetic" in CORPUS["provenance"].lower()
    assert {"en", "sw", "mixed"} <= {case["language"] for case in CORPUS["cases"]}
    assert len({case["id"] for case in CORPUS["cases"]}) == len(CORPUS["cases"])
    assert all(case["purpose"] and case["category"] for case in CORPUS["cases"])
    assert all("expected_disease" not in case for case in CORPUS["cases"])
