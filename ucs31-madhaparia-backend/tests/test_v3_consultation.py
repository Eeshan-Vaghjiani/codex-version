"""Real partial-evidence consultation, with synthetic inputs and no disease labels."""
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

import app.main as main
from app.core.database import SessionLocal, engine
from app.core.errors import ServiceNotReadyError
from app.db.models import ModelVersion, PredictionSession, User
from app.db.register_v3_model_version import register_v3_model_version, activate_v3_model_version
from app.nlp.symptom_mapper import build_confirmation_output
from app.services.consultation import POOL, V3_MODEL_VERSION
from app.services.history import save_prediction_session
from app.services.model_versions import get_active_model_version
from app.services.v3_prediction import get_v3_bundle, predict_partial_evidence
from tests.test_assessment_safety_regressions import SUPPLIED_CASES


@pytest.fixture
def v3_flow(monkeypatch):
    db = SessionLocal()
    saved = []
    original = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.get_db] = lambda: db
    main.app.dependency_overrides[main.get_current_user] = lambda: SimpleNamespace(id=uuid.uuid4(), role="patient")
    version = SimpleNamespace(id=uuid.uuid4(), version=V3_MODEL_VERSION)
    monkeypatch.setattr(main, "get_active_model_version", lambda session: version)
    def save(session, **kwargs):
        saved.append(kwargs)
        return SimpleNamespace(id=uuid.uuid4())
    monkeypatch.setattr(main, "save_prediction_session", save)
    client = TestClient(main.app)
    yield SimpleNamespace(client=client, db=db, saved=saved, version=version)
    client.close()
    db.rollback()
    db.close()
    main.app.dependency_overrides.clear()
    main.app.dependency_overrides.update(original)


def payload(flow, text="I have a cough and fever for two days.", answers=None, **extra):
    mapping = build_confirmation_output(text, flow.db)
    codes = [item["code"] for item in mapping["recognised_symptoms"]
             if item["status"] == "present" and item.get("reported_subject") != "other_person"]
    return {"age": 21, "sex": "M", "text": text, "confirmed_codes": codes,
            "follow_up_answers": answers or [], **extra}


def finish(flow, body, choose=None):
    answers = list(body["follow_up_answers"])
    asked = []
    for _ in range(6):
        response = flow.client.post("/predict", json={**body, "follow_up_answers": answers})
        assert response.status_code == 200, response.text
        data = response.json()
        if data["status"] != "needs_follow_up":
            assert len(answers) <= 5
            return data, answers, asked
        question = data["follow_up_question"]
        qid = question["id"]
        assert qid not in [item["question_id"] for item in answers]
        assert question["rationale"] and question["text"]
        values = {item["value"] for item in question["options"]}
        answer = choose(qid, values) if choose else "no" if qid == "breathing_difficulty" else "unknown"
        assert answer in values
        asked.append(qid)
        answers.append({"question_id": qid, "answer": answer})
    pytest.fail("Consultation did not terminate after five questions")


def assert_selective_result(data):
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


@pytest.mark.parametrize("text,expected", SUPPLIED_CASES, ids=[f"supplied-{i}" for i in range(1, 13)])
def test_supplied_cases_complete_v3_consultation(v3_flow, text, expected):
    data, answers, asked = finish(v3_flow, payload(v3_flow, text))
    if "shortness_of_breath" in expected:
        assert data["status"] == "urgent_review"
        assert not answers and not data["predictions"]
    elif not expected:
        assert data["status"] == "insufficient_evidence"
        assert not answers and not data["predictions"]
    else:
        assert_selective_result(data)
        states = data["assessment_context"]["symptom_states"]
        for code, state in expected.items():
            if code != "weight_loss":  # The source feature requires confirmed involuntary loss.
                assert states[code] == state
        assert len(asked) <= 5
        assert "prediction_id" in data


@pytest.mark.parametrize("english,swahili", [
    ("I have cough", "Nina kikohozi"),
    ("I have fever", "Nina homa"),
    ("I have cough and fever for two days", "Nina kikohozi na homa kwa siku mbili"),
])
def test_equivalent_languages_have_equivalent_model_evidence(v3_flow, english, swahili):
    en, _, _ = finish(v3_flow, payload(v3_flow, english, language="en"))
    sw, _, _ = finish(v3_flow, payload(v3_flow, swahili, language="sw"))
    assert_selective_result(en)
    assert_selective_result(sw)
    assert set(en["model_features"]) == set(sw["model_features"])
    assert set(en["explicitly_absent_features"]) == set(sw["explicitly_absent_features"])
    assert [row["condition"] for row in en["predictions"]] == [row["condition"] for row in sw["predictions"]]
    assert sw["assessment_context"]["language"] == "sw"


def test_explicit_negative_answer_changes_actual_ranked_scores(v3_flow):
    denied, _, _ = finish(v3_flow, payload(v3_flow, "I have cough for two days but no fever"))
    unknown, _, _ = finish(v3_flow, payload(v3_flow, "I have cough for two days but maybe fever"))
    assert_selective_result(denied)
    assert_selective_result(unknown)
    assert "E_91" in denied["explicitly_absent_features"]
    assert "E_91" not in unknown["explicitly_absent_features"]
    assert unknown["assessment_context"]["symptom_states"]["fever"] == "unknown"
    # Scores remain internal; explicit no must still change real model evidence.
    denied_raw = predict_partial_evidence(denied["model_features"], denied["explicitly_absent_features"], denied["age"], denied["sex"])
    unknown_raw = predict_partial_evidence(unknown["model_features"], unknown["explicitly_absent_features"], unknown["age"], unknown["sex"])
    assert denied_raw["predictions"] != unknown_raw["predictions"]


def test_known_duration_skips_repeated_duration_question_and_targets_missing_pool(v3_flow):
    data, _, asked = finish(v3_flow, payload(v3_flow))
    assert "symptom_duration" not in asked
    assert asked[0] == "breathing_difficulty"
    assert all(qid in POOL for qid in asked[1:])
    assert "cough" not in asked and "fever" not in asked
    assert data["assessment_context"]["symptom_durations"]["cough"]["min_days"] == 2
    assert_selective_result(data)


@pytest.mark.parametrize("bad_answers", [
    [{"question_id": "fever", "answer": "yes"}],
    [{"question_id": "breathing_difficulty", "answer": "banana"}],
    [{"question_id": "breathing_difficulty", "answer": "no"}, {"question_id": "breathing_difficulty", "answer": "no"}],
    [{"question_id": "arbitrary_symptom", "answer": "yes"}],
])
def test_invalid_skipped_or_duplicate_answers_rejected(v3_flow, bad_answers):
    response = v3_flow.client.post("/predict", json=payload(v3_flow, answers=bad_answers))
    assert response.status_code in {400, 422}
    assert v3_flow.saved == []


def test_unknown_answers_do_not_become_negative_evidence(v3_flow):
    data, answers, _ = finish(v3_flow, payload(v3_flow))
    for answer in answers:
        if answer["answer"] == "unknown" and answer["question_id"] in POOL:
            assert data["assessment_context"]["symptom_states"][answer["question_id"]] == "unknown"
    assert data["assessment_context"]["questions_asked"] == [row["question_id"] for row in answers]
    stored = v3_flow.saved[-1]["assessment_context"]
    for key in ("symptom_states", "follow_up_answers", "questions_asked", "symptom_durations"):
        assert stored[key] == data["assessment_context"][key]
    assert stored["_primary_audit"]["selection"]["diagnostics"]
    assert "_primary_audit" not in data["assessment_context"]


@pytest.mark.parametrize("text,unexpected", [
    ("I have cough with phlegm", "E_77"),
    ("Ninakohoa makohozi", "E_77"),
    ("I have a tight chest", "E_214"),
    ("Nina kifua kubana", "E_214"),
])
def test_generic_or_distinct_terms_do_not_invent_qualified_features(v3_flow, text, unexpected):
    body = payload(v3_flow, text)
    response = v3_flow.client.post("/predict", json=body)
    assert response.status_code == 200
    data = response.json()
    assert unexpected not in data["model_features"]
    assert unexpected not in data["explicitly_absent_features"]
    if "cough" in body["confirmed_codes"]:
        assert data["assessment_context"]["cough_type"] == "productive"


@pytest.mark.parametrize("intent,expected_feature", [("unintentional", True), ("intentional", False), ("unknown", False)])
def test_weight_loss_intention_controls_native_feature(v3_flow, intent, expected_feature):
    body = payload(v3_flow, "I have cough for two days and have been losing weight")
    first = v3_flow.client.post("/predict", json=body).json()
    assert "E_162" not in first["model_features"]
    answers = [{"question_id": "breathing_difficulty", "answer": "no"}]
    second = v3_flow.client.post("/predict", json={**body, "follow_up_answers": answers}).json()
    assert second["follow_up_question"]["id"] == "weight_loss_intent"
    answers.append({"question_id": "weight_loss_intent", "answer": intent})
    response = v3_flow.client.post("/predict", json={**body, "follow_up_answers": answers})
    assert response.status_code == 200, response.text
    data = response.json()
    assert ("E_162" in data["model_features"]) is expected_feature
    assert data["assessment_context"]["weight_loss_intent"] == intent


def test_emergency_precedes_model_catalogue_and_failed_storage(v3_flow, monkeypatch):
    def routine_failure(*args, **kwargs):
        raise AssertionError("Routine inference must not precede emergency guidance")
    def storage_failure(*args, **kwargs):
        raise RuntimeError("Simulated history outage")
    monkeypatch.setattr(main, "get_active_model_version", routine_failure)
    monkeypatch.setattr(main, "confirm_symptoms", routine_failure)
    monkeypatch.setattr(main, "predict_partial_evidence", routine_failure)
    monkeypatch.setattr(main, "save_prediction_session", storage_failure)
    response = v3_flow.client.post("/predict", json={"age": 21, "sex": "M", "text": "Siwezi kupumua", "confirmed_codes": []})
    assert response.status_code == 200
    assert response.json()["status"] == "urgent_review"
    assert not response.json()["predictions"]


def test_followup_emergency_overrides_stale_trailing_replies(v3_flow):
    response = v3_flow.client.post("/predict", json=payload(v3_flow, answers=[
        {"question_id": "breathing_difficulty", "answer": "yes"},
        {"question_id": "fever", "answer": "no"},
    ]))
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "urgent_review"
    assert data["assessment_context"]["questions_asked"] == ["breathing_difficulty"]
    assert not data["predictions"]


def test_registration_and_activation_are_transactional_and_idempotent(v3_flow):
    before = get_active_model_version(v3_flow.db).id
    first = register_v3_model_version(v3_flow.db)
    second = register_v3_model_version(v3_flow.db)
    assert first.id == second.id
    assert first.class_count == 21 and first.feature_count == 34
    assert get_active_model_version(v3_flow.db).id == before
    active = activate_v3_model_version(v3_flow.db)
    assert get_active_model_version(v3_flow.db).id == active.id
    v3_flow.db.rollback()
    assert get_active_model_version(v3_flow.db).id == before


def test_v3_real_history_persists_evidence_answers_and_model_version(v3_flow, monkeypatch):
    connection = engine.connect()
    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        user = User(email=f"v3-history-{uuid.uuid4().hex}@example.com", password_hash="test-only", role="patient")
        db.add(user)
        db.flush()
        version = register_v3_model_version(db)
        v3_flow.version.id = version.id
        main.app.dependency_overrides[main.get_db] = lambda: db
        main.app.dependency_overrides[main.get_current_user] = lambda: user
        monkeypatch.setattr(main, "save_prediction_session", save_prediction_session)
        data, answers, _ = finish(v3_flow, payload(v3_flow))
        assert_selective_result(data)
        row = db.get(PredictionSession, uuid.UUID(data["prediction_id"]))
        assert row.user_id == user.id and row.model_version_id == version.id
        assert row.assessment_context["follow_up_answers"] == answers
        assert row.assessment_context["model_version"] == V3_MODEL_VERSION
        assert row.predictions == data["predictions"]
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_exact_native_pain_locations_do_not_encode_generic_pain_absent(v3_flow):
    from app.services.symptom_confirmation import confirm_symptoms
    generic = confirm_symptoms("I have headache but no chest pain", ["headache"], v3_flow.db)
    assert generic["model_features"] == ["E_53"]
    assert not generic["explicitly_absent_features"]
    exact = confirm_symptoms("I have forehead pain but no upper chest pain", ["forehead_pain"], v3_flow.db)
    assert set(exact["model_features"]) == {"E_53", "E_55_@_V_89"}
    assert exact["explicitly_absent_features"] == ["E_55_@_V_101"]

@pytest.mark.parametrize('gain,expected_status', [(0.0, 'assessment_uncertain'), (0.019, 'assessment_uncertain'), (0.02, 'needs_follow_up')])
def test_low_benefit_questions_stop_without_blocking_an_assessment(v3_flow, monkeypatch, gain, expected_status):
    import app.services.v3_prediction as service
    monkeypatch.setattr(service, 'rank_follow_up_features', lambda *args, **kwargs: [
        {'feature': 'E_144', 'information_gain': gain},
    ])
    body = payload(v3_flow, 'I have a cough and fever for two days but no difficulty breathing')
    response = v3_flow.client.post('/predict', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data['status'] == expected_status
    if expected_status == 'assessment_uncertain':
        assert_selective_result(data)
        assert data['follow_up_answers'] == []
    else:
        assert data['follow_up_question']['id'] == 'muscle_aches'


def test_unknown_weight_intention_does_not_repeat_the_same_weight_question(v3_flow):
    answers = [{'question_id': 'breathing_difficulty', 'answer': 'no'},
               {'question_id': 'weight_loss_intent', 'answer': 'unknown'}]
    body = payload(v3_flow, 'I have a cough for several weeks and have been losing weight', answers=answers)
    response = v3_flow.client.post('/predict', json=body)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data.get('follow_up_question', {}).get('id') not in {'weight_loss', 'weight_loss_intent'}
    assert 'E_162' not in data['model_features']
    assert data['assessment_context']['symptom_states']['weight_loss'] == 'unknown'


def test_serving_v3_artifact_and_runtime_match_evaluated_model():
    from pathlib import Path
    import ast
    import hashlib
    backend = Path(__file__).resolve().parents[1]
    ml = backend.parent / 'ucs31-madhaparia-ml'
    serving = backend / 'app/ml/artifacts/v3_partial_evidence.json'
    evaluated = ml / 'models/v3_partial_evidence.json'
    assert hashlib.sha256(serving.read_bytes()).digest() == hashlib.sha256(evaluated.read_bytes()).digest()
    def functions(path):
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        return {node.name: ast.dump(node, include_attributes=False) for node in tree.body
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    assert functions(backend / 'app/ml/v3_predictor.py') == functions(ml / 'inference/v3_predictor.py')
