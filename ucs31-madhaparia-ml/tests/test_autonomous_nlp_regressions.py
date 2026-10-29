"""Synthetic software regressions; these cases do not establish diagnoses.

Run with RESPIRACARE_TEST_BACKEND_NLP=1 and the backend Python environment
to execute the same contract tests against the production backend mapper.
"""
import ast
import importlib.util
import json
import os
from pathlib import Path
import sys

import pytest

from nlp import symptom_mapper as ml_mapper

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "ucs31-madhaparia-backend"


@pytest.fixture(scope="module")
def mapper():
    if os.environ.get("RESPIRACARE_TEST_BACKEND_NLP") != "1":
        return ml_mapper
    sys.path.insert(0, str(BACKEND))
    os.environ["DATABASE_URL"] = "sqlite://"
    os.environ["JWT_SECRET_KEY"] = "test-only-nlp-contract-key-01234567890123456789"
    spec = importlib.util.spec_from_file_location(
        "backend_nlp_contract", BACKEND / "app/nlp/symptom_mapper.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


CASES = [
    ("I have fever.", {"fever": "present"}),
    ("Runny nose, for a few days with headache and sore throat.",
     {"runny_blocked_nose": "present", "headache": "present", "sore_throat": "present"}),
    ("I have a cough and fever.", {"cough": "present", "fever": "present"}),
    ("I have a cough.", {"cough": "present"}),
    ("I have a runny nose, sneezing and a mild cough.",
     {"runny_blocked_nose": "present", "sneezing": "present", "cough": "present"}),
    ("I have had a cough and fever for two days.", {"cough": "present", "fever": "present"}),
    ("I have had a cough for several weeks and have been losing weight.",
     {"cough": "present", "weight_loss": "present"}),
    ("I have a cough and I am struggling to breathe.",
     {"cough": "present", "shortness_of_breath": "present"}),
    ("I feel unwell.", {}),
    ("I have a cough, but I do not have a fever.", {"cough": "present", "fever": "absent"}),
    ("Nina homa na kikohozi.", {"cough": "present", "fever": "present"}),
    ("Nina kikohozi lakini sina homa.", {"cough": "present", "fever": "absent"}),
]


@pytest.mark.parametrize("text,expected", CASES, ids=[f"supplied-{n}" for n in range(1, 13)])
def test_supplied_extraction_cases(mapper, text, expected):
    result = mapper.build_confirmation_output(text)
    assert {item["code"]: item["status"] for item in result["recognised_symptoms"]} == expected
    if "unwell" not in text:
        assert result["unmatched_wording"] == []
    assert result["has_red_flag"] == ("struggling to breathe" in text)


@pytest.mark.parametrize("text,code,status", [
    ("I may have fever", "fever", "unknown"),
    ("I might have a cough", "cough", "unknown"),
    ("Do I have fever?", "fever", "unknown"),
    ("I don't think I have fever", "fever", "unknown"),
    ("If I have a cough", "cough", "unknown"),
    ("Labda nina homa", "fever", "unknown"),
    ("Sina uhakika kama nina homa", "fever", "unknown"),
    ("Sihisi homa", "fever", "absent"),
    ("I have not only cough but fever", "cough", "present"),
    ("I don’t have fever", "fever", "absent"),
    ("Nina cough lakini sina fever", "fever", "absent"),
    ("Sina homa na nina kikohozi", "cough", "present"),
    ("I have no cough or fever", "fever", "absent"),
    ("I have cough but no fever", "cough", "present"),
    ("My sister has cough but I have fever", "cough", "unknown"),
    ("My sister has cough but I have fever", "fever", "present"),
])
def test_state_and_context(mapper, text, code, status):
    result = mapper.build_confirmation_output(text)
    symptom = next(item for item in result["recognised_symptoms"] if item["code"] == code)
    assert symptom["status"] == status
    if status == "absent":
        assert symptom in result["absent_symptoms"]
    if status == "unknown":
        assert symptom in result["uncertain_symptoms"]


@pytest.mark.parametrize("text,minimum,maximum,duration", [
    ("I have cough for two days", 2, 2, "for two days"),
    ("I have cough and fever for two days", 2, 2, "for two days"),
    ("I have cough for 2 to 5 days", 2, 5, "for 2 to 5 days"),
    ("I have cough for 2-5 days", 2, 5, "for 2-5 days"),
    ("I have cough for three weeks", 21, 21, "for three weeks"),
    ("Nina kikohozi kwa siku mbili", 2, 2, "kwa siku mbili"),
    ("Nina kikohozi wiki tatu", 21, 21, "wiki tatu"),
    ("Nina kikohozi siku mbili hadi tano", 2, 5, "siku mbili hadi tano"),
    ("I have cough since yesterday", 1, 1, "since yesterday"),
    ("Nina kikohozi tangu jana", 1, 1, "tangu jana"),
    ("I have cough for a few days", None, None, "for a few days"),
    ("I have cough for several weeks", None, None, "for several weeks"),
    ("Nina kikohozi kwa wiki kadhaa", None, None, "kwa wiki kadhaa"),
    ("I have cough for two months", None, None, "for two months"),
    ("I have cough for 12 hours", None, None, "for 12 hours"),
    ("I have no cough for two days", None, None, None),
])
def test_duration_without_invented_bounds(mapper, text, minimum, maximum, duration):
    result = mapper.build_confirmation_output(text)
    symptom = next(item for item in result["recognised_symptoms"] if item["code"] == "cough")
    assert (symptom["duration_min_days"], symptom["duration_max_days"], symptom["duration_text"]) == (minimum, maximum, duration)


@pytest.mark.parametrize("text,expected", [
    ("I have a mild cough", "mild"),
    ("I have moderate cough", "moderate"),
    ("I have severe cough", "severe"),
    ("Nina kikohozi kidogo", "mild"),
    ("Nina kikohozi kali", "severe"),
    ("I have cough", None),
    ("I have mild fever and cough", None),
    ("I have no severe cough", None),
])
def test_severity_is_an_attribute(mapper, text, expected):
    result = mapper.build_confirmation_output(text)
    symptom = next(item for item in result["recognised_symptoms"] if item["code"] == "cough")
    assert symptom["severity"] == expected


@pytest.mark.parametrize("text", [
    "I am struggling to breathe", "I can't breathe", "I cannot breathe",
    "I’m gasping for air", "I can't catch my breath", "I cannot catch my breath",
    "I am unable to breathe", "I am not coughing but I am gasping",
    "Ninashindwa kupumua", "Siwezi kupumua", "Ninapumua kwa shida",
    "Napumua kwa shida", "Sina homa lakini siwezi kupumua",
    "I am coughing up blood", "Ninakohoa damu", "Midomo imekuwa bluu",
])
def test_independent_safety_recognition(mapper, text):
    assert mapper.detect_safety_signs(text)


@pytest.mark.parametrize("text", [
    "I am not struggling to breathe", "I have no shortness of breath",
    "Sina shida ya kupumua", "I am not coughing up blood",
    "My sister is gasping", "My brother is coughing up blood",
    "I am sneezing", "Napiga chafya", "I feel unwell", "I went shopping",
])
def test_absence_other_subject_and_vague_text_are_not_emergencies(mapper, text):
    assert mapper.detect_safety_signs(text) == []


def test_backend_and_ml_shared_logic_cannot_silently_drift():
    def definitions(path):
        tree = ast.parse(path.read_text(encoding="utf8"))
        return {node.name: ast.dump(node, include_attributes=False)
                for node in tree.body if isinstance(node, ast.FunctionDef)}
    ml = definitions(ROOT / "ucs31-madhaparia-ml/nlp/symptom_mapper.py")
    backend = definitions(BACKEND / "app/nlp/symptom_mapper.py")
    for name in ["normalize_text", "find_fuzzy_matches", "_find_alias_matches", "find_unmatched_text", "infer_symptom_status",
                 "infer_symptom_subject", "infer_repeated_symptom_context",
                 "parse_duration", "extract_patient_attributes", "detect_safety_signs"]:
        assert ml[name] == backend[name], name
    for filename in ["canonical_symptoms.json", "english_aliases.json", "swahili_aliases.json"]:
        assert json.loads((ROOT / "ucs31-madhaparia-ml/nlp" / filename).read_text(encoding="utf8")) == json.loads((BACKEND / "app/nlp" / filename).read_text(encoding="utf8"))


@pytest.mark.parametrize('text,alias,status', [
    ('I have no sense of smell, fever and cough', 'fever', 'present'),
    ('I have no sense of smell, fever and cough', 'cough', 'present'),
    ('I have no taste, fever and cough', 'cough', 'present'),
    ('I have no energy and headache', 'headache', 'present'),
    ('I have no appetite and cough', 'cough', 'present'),
    ('Sina nguvu na homa', 'homa', 'present'),
    ('I have no fever or cough', 'cough', 'absent'),
    ('Sina homa wala kikohozi', 'kikohozi', 'absent'),
    ('I do not have no sense of smell, fever or cough', 'cough', 'absent'),
    ('I have no sense of smell, but no fever', 'fever', 'absent'),
    ('I am not sure if I have no sense of smell and cough', 'cough', 'unknown'),
])
def test_intrinsic_absence_wording_does_not_negate_other_symptoms(mapper, text, alias, status):
    assert mapper.infer_symptom_status(text, alias) == status
