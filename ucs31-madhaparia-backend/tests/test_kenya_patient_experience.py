"""Kenya patient communication and selection contract regressions.

Inputs are synthetic software scenarios, NOT a clinician-reviewed disease gold
set. Warning-sign expectations are grounded in docs/kenya_research.md; passing
these tests is not evidence of clinical safety, sensitivity or diagnostic accuracy.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy.orm import Session

import app.main as main
from app.core.database import SessionLocal, engine
from app.db.models import PredictionSession, User
from app.nlp.symptom_mapper import build_confirmation_output
from app.services.consultation import V3_MODEL_VERSION


BACKEND = Path(__file__).resolve().parents[1]
TERMINOLOGY = BACKEND / "app/data/patient_terminology.json"
NUMERIC_SCORE_FIELDS = {
    "confidence", "confidence_percent", "model_confidence_percent",
    "probability", "probability_percent", "raw_relative_score",
    "relative_probability", "relative_score", "model_confidence",
    "raw_probability", "raw_score", "score", "log_score",
}


def assert_no_patient_numeric_scores(value):
    """Check nested history/context as well as the primary card payload."""
    if isinstance(value, dict):
        for key, child in value.items():
            if key in NUMERIC_SCORE_FIELDS:
                assert not isinstance(child, (int, float)), (key, child)
            assert_no_patient_numeric_scores(child)
    elif isinstance(value, list):
        for child in value:
            assert_no_patient_numeric_scores(child)


def assert_single_primary_contract(data):
    assert "primary_prediction" in data
    primary = data["primary_prediction"]
    assert data["predictions"] == ([] if primary is None else [primary])
    assert len(data["predictions"]) <= 1
    assert data["clinical_validation"] is False
    assert data["decision"]["status"] in {
        "possible_explanation", "uncertain", "insufficient_information"
    }
    assert isinstance(data["decision"]["reasons"], list)
    assert data["decision"]["policy_version"]
    assert "score_note" not in data
    if primary:
        assert data["decision"]["status"] == "possible_explanation"
        assert primary["medical_name"]
        assert primary["display_name"]
        assert primary["description"]
    assert_no_patient_numeric_scores(data)


@pytest.fixture
def kenya_flow(monkeypatch):
    """Real migrated catalogue/inference, isolated auth and history writes."""
    db = SessionLocal()
    saved = []
    user = SimpleNamespace(id=uuid.uuid4(), role="patient")
    version = SimpleNamespace(id=uuid.uuid4(), version=V3_MODEL_VERSION)
    overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.get_db] = lambda: db
    main.app.dependency_overrides[main.get_current_user] = lambda: user
    monkeypatch.setattr(main, "get_active_model_version", lambda session: version)

    def save(session, **kwargs):
        saved.append(deepcopy(kwargs))
        return SimpleNamespace(id=uuid.uuid4())

    monkeypatch.setattr(main, "save_prediction_session", save)
    client = TestClient(main.app)
    try:
        yield SimpleNamespace(client=client, db=db, saved=saved, user=user)
    finally:
        client.close()
        db.rollback()
        db.close()
        main.app.dependency_overrides.clear()
        main.app.dependency_overrides.update(overrides)


def patient_payload(flow, text, **extra):
    mapped = build_confirmation_output(text, flow.db)
    codes = [row["code"] for row in mapped["recognised_symptoms"]
             if row["status"] == "present" and row.get("reported_subject") != "other_person"]
    return {"age": 24, "sex": "F", "text": text, "confirmed_codes": codes,
            "follow_up_answers": [], **extra}


def finish_assessment(flow, body, *, cough_answer="unknown"):
    answers, asked = list(body.get("follow_up_answers", [])), []
    for _ in range(6):
        response = flow.client.post("/predict", json={**body, "follow_up_answers": answers})
        assert response.status_code == 200, response.text
        data = response.json()
        assert_single_primary_contract(data)
        if data["status"] != "needs_follow_up":
            assert len(answers) <= 5
            return data, answers, asked
        question = data["follow_up_question"]
        qid = question["id"]
        assert qid not in asked
        assert question["text"] and question["rationale"]
        values = {option["value"] for option in question["options"]}
        answer = "no" if qid == "breathing_difficulty" else cough_answer if qid == "cough" else "unknown"
        assert answer in values
        asked.append(qid)
        answers.append({"question_id": qid, "answer": answer})
    pytest.fail("Assessment exceeded five questions")


def test_patient_terminology_exactly_covers_active_source_classes():
    terminology = json.loads(TERMINOLOGY.read_text(encoding="utf-8"))
    bundle = json.loads((BACKEND / "app/ml/artifacts/v3_partial_evidence.json").read_text())
    assert terminology["schema_version"] == 1
    assert set(terminology["conditions"]) == set(bundle["classes"])
    assert len(terminology["conditions"]) == 21
    assert "pending" in terminology["review_status"].lower()
    assert "not clinical validation" in terminology["review_status"].lower()
    for item in terminology["conditions"].values():
        assert item["medical_name"]
        for field in ("display_name", "description"):
            assert set(item[field]) == {"en", "sw"}
            assert all(isinstance(text, str) and text.strip() for text in item[field].values())
        assert item["source_ids"]
        assert set(item["source_ids"]) <= set(terminology["sources"])
    for source in terminology["sources"].values():
        assert source["title"]
        assert urlparse(source["url"]).scheme == "https"
        assert urlparse(source["url"]).netloc


def test_terminology_preserves_diagnostic_distinctions_and_model_keys():
    conditions = json.loads(TERMINOLOGY.read_text(encoding="utf-8"))["conditions"]
    assert conditions["Larygospasm"]["medical_name"] == "Laryngospasm"
    assert "influenza" not in conditions["URTI"]["display_name"]["en"].lower()
    assert "common cold" not in conditions["URTI"]["display_name"]["en"].lower()
    assert "non-cancerous" in conditions["Pulmonary neoplasm"]["description"]["en"]
    assert "cancerous" in conditions["Pulmonary neoplasm"]["description"]["en"]
    assert {"COVID-19", "Malaria", "HIV", "Allergic rhinitis"}.isdisjoint(conditions)


@pytest.mark.parametrize("language", ["en", "sw"])
@pytest.mark.parametrize("condition", ["Influenza", "URTI"])
def test_eligible_selector_maps_one_localized_possibility_without_private_scores(monkeypatch, condition, language):
    """Mock eligibility tests presentation only; it is not a clinical reference."""
    import app.services.primary_assessment as service
    raw = {"condition": condition, "rank": 1, "raw_relative_score": 0.92}
    chosen = {"status": "eligible", "primary_prediction": raw,
              "reasons": [], "policy_version": "test-selector-only",
              "clinical_validation": False,
              "diagnostics": {"score": 0.92, "confidence": 0.92}}
    monkeypatch.setattr(service, "select_primary_evidence", lambda *args, **kwargs: deepcopy(chosen))
    confirmation = {
        "model_features": ["E_201", "E_91", "E_144"], "explicitly_absent_features": [],
        "assessment_context": {"language": language, "symptom_states": {
            "cough": "present", "fever": "present", "muscle_aches": "present"}},
    }
    result = service.build_primary_assessment(confirmation, 24, "F")
    audit = result.pop("_audit")
    assert audit["selection"]["primary_prediction"] == raw
    assert_single_primary_contract(result)
    assert result["status"] == "prediction_complete"
    primary = result["primary_prediction"]
    terms = json.loads(TERMINOLOGY.read_text(encoding="utf-8"))["conditions"][condition]
    assert primary["condition"] == condition
    assert primary["medical_name"] == terms["medical_name"]
    assert primary["display_name"] == terms["display_name"][language]
    assert primary["description"] == terms["description"][language]
    assert primary["evidence_note"] and result["assessment_summary"]


@pytest.mark.parametrize("guard", ["unsupported_wording", "reported_severity"])
def test_input_guards_do_not_turn_eligible_pattern_into_reassurance(monkeypatch, guard):
    import app.services.primary_assessment as service
    monkeypatch.setattr(service, "select_primary_evidence", lambda *args, **kwargs: {
        "status": "eligible", "primary_prediction": {"condition": "Influenza"},
        "reasons": [], "policy_version": "test-selector-only", "diagnostics": {},
    })
    confirmation = {"model_features": ["E_201", "E_91"],
        "assessment_context": {"language": "en", "symptom_states": {"cough": "present"}}}
    if guard == "unsupported_wording":
        confirmation["unmatched_wording"] = ["unexplained new symptom"]
    else:
        confirmation["assessment_context"]["severity"] = {"cough": "severe"}
    result = service.build_primary_assessment(confirmation, 24, "F")
    result.pop("_audit")
    assert_single_primary_contract(result)
    assert result["status"] == "assessment_uncertain"
    assert result["primary_prediction"] is None
    assert result["decision"]["reasons"]


@pytest.mark.parametrize("text", [
    "I have a headache", "I feel tired", "I have headache and tiredness",
    "I have mild fever and headache", "I have body aches and tiredness",
    "Nina maumivu ya kichwa na uchovu",
    "My head hurts and I feel tired", "I have hedache and tiredness",
])
def test_nonspecific_nonrespiratory_symptoms_do_not_force_disease(kenya_flow, text):
    data, _, asked = finish_assessment(
        kenya_flow, patient_payload(kenya_flow, text), cough_answer="no")
    assert data["status"] in {"assessment_uncertain", "insufficient_evidence"}
    assert data["primary_prediction"] is None
    assert data["uncertain"] is True
    assert data["decision"]["status"] != "possible_explanation"
    assert set(asked) <= {"breathing_difficulty", "general_duration", "symptom_severity", "cough", "fever"}
    assert data["assessment_summary"] and data["next_steps"]
    visible = " ".join(str(data.get(key, "")) for key in ("assessment_summary", "next_steps", "health_guidance"))
    assert "ruled out" not in visible.lower()
    assert "you are low risk" not in visible.lower()
    assert "this is low risk" not in visible.lower()


def test_headache_and_tiredness_get_relevant_duration_question(kenya_flow):
    data, _, asked = finish_assessment(kenya_flow,
        patient_payload(kenya_flow, "I have headache and tiredness"), cough_answer="no")
    assert "general_duration" in asked
    assert data["primary_prediction"] is None
    assert "symptom_duration" not in asked  # No invented cough duration.


@pytest.mark.parametrize("text", [
    "I have cough and sore throat",
    "I have fever, cough, sore throat and body aches for two days",
    "I have a runny nose, sneezing, a cough and sore throat for two days",
    "Nina homa na kikohozi kwa siku mbili",
])
def test_respiratory_patterns_return_at_most_one_qualified_possibility(kenya_flow, text):
    data, _, _ = finish_assessment(kenya_flow, patient_payload(kenya_flow, text))
    assert_single_primary_contract(data)
    assert data["uncertain"] is True
    if data["primary_prediction"]:
        condition = data["primary_prediction"]["condition"]
        terminology = json.loads(TERMINOLOGY.read_text(encoding="utf-8"))["conditions"][condition]
        assert data["primary_prediction"]["medical_name"] == terminology["medical_name"]
        assert data["primary_prediction"]["display_name"] == terminology["display_name"]["en" if not text.startswith("Nina") else "sw"]


@pytest.mark.parametrize("text", [
    "I have a severe sudden headache",
    "I have a headache, fever and a stiff neck",
    "I have severe crushing chest pressure",
    "I am gasping for air",
    "Siwezi kupumua",
])
def test_reported_danger_signs_precede_model_and_followup(kenya_flow, monkeypatch, text):
    def unavailable(*args, **kwargs):
        raise AssertionError("Warning guidance must precede routine inference")
    monkeypatch.setattr(main, "get_active_model_version", unavailable)
    monkeypatch.setattr(main, "predict_partial_evidence", unavailable)
    response = kenya_flow.client.post("/predict", json={
        "age": 24, "sex": "F", "text": text, "confirmed_codes": []})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "urgent_review"
    assert data["predictions"] == [] and data["primary_prediction"] is None
    assert data.get("follow_up_question") is None
    assert data["health_guidance"]
    assert_no_patient_numeric_scores(data)


def test_infant_fever_receives_care_advice_without_guessing_months(kenya_flow):
    response = kenya_flow.client.post("/predict", json=patient_payload(
        kenya_flow, "I have a fever", age=0))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["primary_prediction"] is None
    assert data["status"] in {"urgent_review", "professional_review"}
    assert data["health_guidance"]
    assert data.get("follow_up_question") is None


@pytest.mark.parametrize("text", [
    "I have a cough but no difficulty breathing",
    "I have a cough but no stiff neck or severe sudden headache",
    "Nina kikohozi lakini sina shida ya kupumua",
])
def test_denied_danger_signs_are_not_positive_emergencies(kenya_flow, text):
    response = kenya_flow.client.post("/predict", json=patient_payload(kenya_flow, text))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] != "urgent_review"
    assert_single_primary_contract(data)


def test_exactly_fourteen_day_cough_prompts_professional_assessment_advice(kenya_flow):
    response = kenya_flow.client.post("/predict", json=patient_payload(
        kenya_flow, "I have had a cough for 14 days"))
    assert response.status_code == 200, response.text
    data = response.json()
    guidance = data["health_guidance"].lower()
    assert any(word in guidance for word in ("arrange", "assessment", "healthcare professional", "health facility"))
    assert data["care_level"] == "professional_review"
    assert "self-care only" not in guidance
    assert data["assessment_context"]["symptom_durations"]["cough"]["min_days"] == 14


def test_three_to_fourteen_day_answer_does_not_invent_fourteen_day_lower_bound(kenya_flow):
    body = patient_payload(kenya_flow, "I have a cough but no difficulty breathing")
    response = kenya_flow.client.post("/predict", json=body)
    assert response.status_code == 200, response.text
    first = response.json()
    assert first["follow_up_question"]["id"] == "symptom_duration"
    response = kenya_flow.client.post("/predict", json={**body, "follow_up_answers": [
        {"question_id": "symptom_duration", "answer": "3_to_14_days"}]})
    assert response.status_code == 200, response.text
    data = response.json()
    duration = data["assessment_context"]["symptom_durations"]["cough"]
    assert duration["min_days"] == 3 and duration["max_days"] == 14
    assert data["care_level"] != "professional_review"


@pytest.mark.parametrize("body", [
    {"age": 24, "sex": "F", "text": "", "confirmed_codes": []},
    {"age": 24, "sex": "F", "text": "   ", "confirmed_codes": []},
    {"age": True, "sex": "F", "text": "cough", "confirmed_codes": ["cough"]},
    {"age": 24, "sex": "F", "text": "cough", "confirmed_codes": "cough"},
    {"age": 24, "sex": "F", "text": "cough", "confirmed_codes": [True]},
    {"age": 24, "sex": "F", "text": "cough", "confirmed_codes": ["cough"], "primary_prediction": {"condition": "Influenza"}},
])
def test_invalid_requests_never_save_or_generate_predictions(kenya_flow, body):
    response = kenya_flow.client.post("/predict", json=body)
    assert response.status_code == 422, response.text
    assert kenya_flow.saved == []


@pytest.mark.parametrize("text", ["My ankle is itchy and my fingernail is cracked", "I feel unwell"])
def test_unsupported_text_does_not_fabricate_a_supported_disease(kenya_flow, text):
    data, _, _ = finish_assessment(kenya_flow,
        patient_payload(kenya_flow, text))
    assert data["primary_prediction"] is None
    assert data["predictions"] == []
    assert data["decision"]["status"] == "insufficient_information"


def test_conflicting_fever_reports_stay_unknown_and_do_not_invent_both_states(kenya_flow):
    body = patient_payload(kenya_flow, "I have a cough and fever, but I have no fever")
    assert "fever" not in body["confirmed_codes"]
    response = kenya_flow.client.post("/predict", json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["assessment_context"]["symptom_states"]["fever"] == "unknown"
    assert "E_91" not in data["model_features"]
    assert "E_91" not in data["explicitly_absent_features"]
    assert_single_primary_contract(data)


def test_confirming_an_unsupported_code_is_rejected(kenya_flow):
    response = kenya_flow.client.post("/predict", json={
        "age": 24, "sex": "F", "text": "I have cough", "confirmed_codes": ["invented_symptom"]})
    assert response.status_code in {400, 422}
    assert kenya_flow.saved == []


def test_legacy_patient_history_is_reassessment_required_without_db_mutation(kenya_flow):
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        user = User(email=f"kenya-history-{uuid.uuid4().hex}@example.com", password_hash="test-only", role="patient")
        db.add(user)
        db.flush()
        old_predictions = [
            {"condition": "Influenza", "rank": 1, "model_confidence_percent": 98.2},
            {"condition": "URTI", "rank": 2, "raw_relative_score": 0.01},
            {"condition": "Pneumonia", "rank": 3, "probability": 0.008},
        ]
        row = PredictionSession(user_id=user.id, age=24, sex="F", input_text="Cough and fever",
            confirmed_codes=["cough", "fever"], model_features=["E_201", "E_91"],
            status="prediction_complete", has_red_flag=False, predictions=deepcopy(old_predictions), assessment_context={})
        db.add(row)
        db.flush()
        row_id = row.id
        main.app.dependency_overrides[main.get_db] = lambda: db
        main.app.dependency_overrides[main.get_current_user] = lambda: user
        main.app.dependency_overrides[main.require_admin] = lambda: SimpleNamespace(id=user.id, role="admin")
        for path in ("/history", f"/history/{row_id}"):
            response = kenya_flow.client.get(path)
            assert response.status_code == 200, response.text
            body = response.json()
            item = body["history"][0] if "history" in body else body
            assert item["status"] == "reassessment_required"
            assert item["primary_prediction"] is None
            assert item["predictions"] == []
            assert_no_patient_numeric_scores(body)
        for path in ("/admin/history", f"/admin/history/{row_id}"):
            response = kenya_flow.client.get(path)
            assert response.status_code == 200, response.text
            body = response.json()
            item = body["history"][0] if "history" in body else body
            assert item["predictions"] == old_predictions
            assert item["status"] == "prediction_complete"
        db.expire_all()
        preserved = db.get(PredictionSession, row_id)
        assert preserved.predictions == old_predictions
        assert preserved.status == "prediction_complete"
        assert preserved.assessment_context == {}
    finally:
        db.close()
        transaction.rollback()
        connection.close()


@pytest.mark.parametrize("path", ["/admin/history", f"/admin/history/{uuid.uuid4()}"])
def test_patient_identity_cannot_access_raw_admin_audit_history(kenya_flow, path):
    response = kenya_flow.client.get(path)
    assert response.status_code == 403, response.text
