"""One-time explicit migration of earlier patient top-three test contracts."""
from pathlib import Path

root = Path(__file__).resolve().parents[2] / 'ucs31-madhaparia-backend'

def edit(name, old, new):
    path = root / 'tests' / name
    text = path.read_text(encoding='utf-8-sig')
    if old not in text:
        raise ValueError(f'Missing exact migration target: {name}: {old[:90]}')
    path.write_text(text.replace(old, new), encoding='utf-8')

name = 'test_v3_consultation.py'
path = root / 'tests' / name
text = path.read_text(encoding='utf-8-sig')
start = text.index('def assert_real_candidates(data):')
end = text.index('\n\n@pytest.mark.parametrize', start)
text = text[:start] + '''def assert_selective_result(data):
    """Selection may abstain; any primary must match actual frozen inference."""
    from tests.test_kenya_patient_experience import assert_single_primary_contract
    assert data["status"] in {"prediction_complete", "assessment_uncertain"}
    assert data["model_version"] == V3_MODEL_VERSION
    assert_single_primary_contract(data)
    assert data["uncertain"] is True
    assert data["next_steps"] and data["assessment_summary"]
    raw = predict_partial_evidence(data["model_features"], data["explicitly_absent_features"], data["age"], data["sex"])
    if data["primary_prediction"]:
        row = data["primary_prediction"]
        assert data["status"] == "prediction_complete"
        assert row["condition"] == raw["predictions"][0]["condition"]
        assert row["display_name"] and row["description"] and row["explanation"]
        assert isinstance(row["supporting_symptoms"], list)
    else:
        assert data["status"] == "assessment_uncertain"
        assert data["decision"]["reasons"]
''' + text[end:]
text = text.replace('assert_real_candidates(', 'assert_selective_result(')
text = text.replace('[(row["condition"], row["model_confidence_percent"]) for row in en["predictions"]] == [(row["condition"], row["model_confidence_percent"]) for row in sw["predictions"]]', '[row["condition"] for row in en["predictions"]] == [row["condition"] for row in sw["predictions"]]')
text = text.replace('assert [(row["condition"], row["model_confidence_percent"]) for row in denied["predictions"]] != [(row["condition"], row["model_confidence_percent"]) for row in unknown["predictions"]]', '''# Scores remain internal; explicit no must still change real model evidence.
    denied_raw = predict_partial_evidence(denied["model_features"], denied["explicitly_absent_features"], denied["age"], denied["sex"])
    unknown_raw = predict_partial_evidence(unknown["model_features"], unknown["explicitly_absent_features"], unknown["age"], unknown["sex"])
    assert denied_raw["predictions"] != unknown_raw["predictions"]''')
text = text.replace('assert v3_flow.saved[-1]["assessment_context"] == data["assessment_context"]', '''stored = v3_flow.saved[-1]["assessment_context"]
    for key in ("symptom_states", "follow_up_answers", "questions_asked", "symptom_durations"):
        assert stored[key] == data["assessment_context"][key]
    assert stored["_primary_audit"]["selection"]["diagnostics"]
    assert "_primary_audit" not in data["assessment_context"]''')
text = text.replace("[(0.0, 'prediction_complete'), (0.019, 'prediction_complete'), (0.02, 'needs_follow_up')]", "[(0.0, 'assessment_uncertain'), (0.019, 'assessment_uncertain'), (0.02, 'needs_follow_up')]")
text = text.replace("if expected_status == 'prediction_complete':", "if expected_status == 'assessment_uncertain':")
path.write_text(text, encoding='utf-8')

# Legacy activated models cannot bypass the new patient selection policy.
name = 'test_assessment_safety_regressions.py'
edit(name, 'assert data["status"] == "insufficient_evidence"', 'assert data["status"] == ("assessment_uncertain" if any(value in {"present", "unknown"} for value in data["assessment_context"]["symptom_states"].values()) else "insufficient_evidence")')
edit(name, 'assert flow.saved[-1]["assessment_context"] == context', 'assert flow.saved[-1]["assessment_context"]["follow_up_answers"] == context["follow_up_answers"]\n    assert flow.saved[-1]["assessment_context"]["patient_decision"] == data["decision"]')
edit(name, '''    assert data["score_note"]
    assert "probability" not in data["score_note"].lower() or "not" in data["score_note"].lower()
    if data["predictions"]:
        assert data["status"] == "prediction_complete"
        for prediction in data["predictions"]:
            assert prediction["condition"]
            assert prediction["display_name"]
            assert prediction["description"]
            assert 0 <= prediction["model_confidence_percent"] <= 100''', '''    assert data["predictions"] == [] and data["primary_prediction"] is None
    assert data["decision"]["reasons"] == ["legacy_model_requires_reassessment"]
    assert "score_note" not in data''')
edit(name, 'def test_v2_three_symptoms_returns_only_uncertain_research_matches(flow):', 'def test_v2_three_symptoms_defer_without_a_current_selection_policy(flow):')
edit(name, '''    assert data["status"] == "prediction_complete"
    assert "E_91" in captured["explicitly_absent_features"]
    assert "E_91" not in captured["symptom_features"]''', '''    assert data["status"] == "assessment_uncertain"
    assert captured == {}  # No patient inference through the older model.
    assert "E_91" in data["explicitly_absent_features"]
    assert "E_91" not in data["model_features"]''')
edit(name, 'def test_explicit_absence_reaches_real_v2_predictor(flow, monkeypatch):', 'def test_legacy_deferral_preserves_explicit_absence_without_running_v2(flow, monkeypatch):')

name = 'test_prediction_validation.py'
edit(name, 'assert data["status"] == "insufficient_evidence"', 'assert data["status"] == "assessment_uncertain"',)
# No selected symptoms is the intentionally different information state.
edit(name, '''    assert data["status"] == "assessment_uncertain"
    assert data["predictions"] == []
    assert "no_supported_present_symptoms" in data["uncertainty_reasons"]''', '''    assert data["status"] == "insufficient_evidence"
    assert data["predictions"] == [] and data["primary_prediction"] is None
    assert data["decision"]["status"] == "insufficient_information"''')
edit(name, 'assert "v1_unknown_absent_mismatch" in data["uncertainty_reasons"]', 'assert data["decision"]["reasons"] == ["legacy_model_requires_reassessment"]')
edit(name, 'assert "confidence_explanation" in data', 'assert "confidence_explanation" not in data')
edit('test_end_to_end.py', 'assert prediction["status"] == "insufficient_evidence"', 'assert prediction["status"] == "assessment_uncertain"\n    assert prediction["decision"]["reasons"] == ["legacy_model_requires_reassessment"]')

name = 'test_v2_prediction_history_integration.py'
edit(name, 'assert result["status"] == "prediction_complete"', 'assert result["status"] == "assessment_uncertain"')
edit(name, 'assert result["feature_count"] == 66\n            assert len(result["predictions"]) == 3', 'assert result["primary_prediction"] is None\n            assert result["predictions"] == []\n            assert result["decision"]["reasons"] == ["legacy_model_requires_reassessment"]')
edit(name, '"prediction_complete"\n                )\n                assert len(saved.predictions) == 3', '"assessment_uncertain"\n                )\n                assert saved.predictions == []')
edit(name, 'assert len(matching[0]["predictions"]) == 3', 'assert matching[0]["predictions"] == []')
edit(name, 'assert matching[0]["score_note"]', 'assert "score_note" not in matching[0]')
edit(name, '"uncertainty_reasons", "model_version"', '"decision", "model_version"')
edit(name, 'assert detail["score_note"]', 'assert "score_note" not in detail')

name = 'test_v2_prediction_api_unit.py'
path = root / 'tests' / name
text = path.read_text(encoding='utf-8-sig')
start = text.index('    def test_v2_returns_research_condition_and_uncertainty(self):')
end = text.index('    def test_red_flag_bypasses_model(self):', start)
text = text[:start] + '''    def assert_legacy_deferral(self, expected_version):
        response = self.request_prediction()
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["model_version"], expected_version)
        self.assertEqual(data["status"], "assessment_uncertain")
        self.assertEqual(data["predictions"], [])
        self.assertIsNone(data["primary_prediction"])
        self.assertEqual(data["decision"]["reasons"], ["legacy_model_requires_reassessment"])
        self.assertTrue(data["uncertain"])
        self.assertFalse(data["clinical_validation"])
        self.assertNotIn("score_note", data)
        self.assertEqual(self.saved["model_version_id"], self.model_version.id)
        self.assertEqual(self.saved["predictions"], [])
        self.mocks[3].assert_not_called()
        self.mocks[4].assert_not_called()

    def test_v2_defers_without_a_current_patient_policy(self):
        self.assert_legacy_deferral("v2_23class_prototype")

    def test_v1_abstains_without_falling_back_to_v2(self):
        self.model_version.version = "1.0"
        self.assert_legacy_deferral("1.0")

    def test_unsupported_only_abstains_without_model_call(self):
        self.confirmation["model_features"] = ["E_55_@_V_101"]
        self.confirmation["confirmed_codes"] = ["cough"]
        self.confirmation["recognised_symptoms"][0]["features"] = ["E_55_@_V_101"]
        self.confirmation["recognised_symptoms"][1]["status"] = "absent"
        self.confirmation["recognised_symptoms"][2]["status"] = "absent"
        self.assert_legacy_deferral("v2_23class_prototype")

''' + text[end:]
start = text.index('    def test_real_v2_model_through_api(self):')
end = text.index('\n\nif __name__', start)
text = text[:start] + '''    def test_real_v2_remains_available_for_internal_comparison(self):
        result = predict_v2_single(
            age=25, sex="M", symptom_features=["E_201", "E_91", "E_181"],
            explicitly_absent_features=["E_66"])
        self.assertEqual(result["model_version"], "v2_23class_prototype")
        self.assertEqual(result["feature_count"], 66)
        self.assertEqual(len(result["predictions"]), 3)
        self.assertEqual(result["predictions"][0]["rank"], 1)
        self.assertIn("score_note", result)
''' + text[end:]
path.write_text(text, encoding='utf-8')
print('Migrated earlier patient ranking contracts; raw model tests and access checks retained.')
