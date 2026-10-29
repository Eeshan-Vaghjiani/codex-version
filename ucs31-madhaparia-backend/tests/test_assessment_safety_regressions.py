"""Integrated software behavior tests; synthetic inputs have no disease ground truth."""
from types import SimpleNamespace
import uuid

from fastapi.testclient import TestClient
import pytest

import app.main as main
from app.core.database import SessionLocal
from app.core.errors import ServiceNotReadyError
from app.nlp.symptom_mapper import build_confirmation_output
from app.services.assessment import prepare_assessment
from app.services.symptom_confirmation import confirm_symptoms


SUPPLIED_CASES = [
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


@pytest.fixture
def flow(monkeypatch):
    """Use the migrated test catalogue; isolate auth/model choice/history writes."""
    db = SessionLocal()
    saved = []
    version = SimpleNamespace(id=uuid.uuid4(), version="1.0")
    original_overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.get_db] = lambda: db
    main.app.dependency_overrides[main.get_current_user] = lambda: SimpleNamespace(
        id=uuid.uuid4(), role="patient", email="audit-flow@example.com"
    )
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
    main.app.dependency_overrides.update(original_overrides)


def request(text="I have a cough.", codes=None, answers=None, **extra):
    return {"age": 21, "sex": "M", "text": text,
            "confirmed_codes": ["cough"] if codes is None else codes,
            "follow_up_answers": [] if answers is None else answers, **extra}


def finish_questions(client, payload):
    answers, asked = list(payload["follow_up_answers"]), []
    for _ in range(4):
        response = client.post("/predict", json={**payload, "follow_up_answers": answers})
        assert response.status_code == 200, response.text
        data = response.json()
        if data["status"] != "needs_follow_up":
            assert len(asked) <= 3
            return data
        question = data["follow_up_question"]
        assert question["id"] not in asked
        assert question["text"]
        assert question["rationale"]
        assert question["options"]
        assert all(option["label"].startswith(f"{index}. ")
                   for index, option in enumerate(question["options"], 1))
        asked.append(question["id"])
        values = {option["value"] for option in question["options"]}
        answer = "no" if "no" in values else "unknown"
        answers.append({"question_id": question["id"], "answer": answer})
    pytest.fail("Follow-up loop did not terminate within the configured limit")


@pytest.mark.parametrize("text,expected", SUPPLIED_CASES, ids=[f"supplied-{n}" for n in range(1, 13)])
def test_all_supplied_cases_through_api(flow, text, expected):
    mapped_response = flow.client.post("/nlp/map", json={"text": text})
    assert mapped_response.status_code == 200
    mapped = mapped_response.json()
    if "shortness_of_breath" in expected:
        # The safety route intentionally returns warning signs immediately.
        assert mapped["has_red_flag"] is True
        assert any(item["code"] == "shortness_of_breath" for item in mapped["recognised_symptoms"])
    else:
        assert {item["code"]: item["status"] for item in mapped["recognised_symptoms"]} == expected
    codes = [code for code, state in expected.items() if state == "present"]
    confirmation_response = flow.client.post("/symptoms/confirm", json={"text": text, "confirmed_codes": codes})
    assert confirmation_response.status_code == 200, confirmation_response.text
    confirmation = confirmation_response.json()
    assert set(confirmation["confirmed_codes"]) == set(codes)
    for item in confirmation["absent_symptoms"]:
        assert item["status"] == "absent"
        assert item["code"] not in confirmation["confirmed_codes"]
    data = finish_questions(flow.client, request(text, codes))
    if "shortness_of_breath" in codes:
        assert data["status"] == "urgent_review"
        assert data["has_red_flag"] is True
    else:
        assert data["status"] == ("assessment_uncertain" if any(value in {"present", "unknown"} for value in data["assessment_context"]["symptom_states"].values()) else "insufficient_evidence")
        assert data["uncertain"] is True
    assert data["predictions"] == []


@pytest.mark.parametrize("text", [
    "I have cough but I do not have fever",
    "Nina kikohozi lakini sina homa",
    "I have cough na sina homa",
])
def test_absence_survives_confirmation_and_assessment(flow, text):
    result = confirm_symptoms(text, ["cough"], flow.db)
    assert result["model_features"] == ["E_201"]
    assert result["explicitly_absent_features"] == ["E_91"]
    assessment = prepare_assessment(result, [], "en", flow.db)
    assert assessment["assessment_context"]["symptom_states"]["fever"] == "absent"
    assert assessment["explicitly_absent_features"] == ["E_91"]
    assert "E_91" not in assessment["model_features"]


def test_uncertain_and_unmentioned_are_distinct(flow):
    result = confirm_symptoms("I have cough but maybe fever", ["cough"], flow.db)
    assessment = prepare_assessment(result, [], "en", flow.db)
    states = assessment["assessment_context"]["symptom_states"]
    assert states["cough"] == "present"
    assert states["fever"] == "unknown"
    assert "headache" not in states
    assert "E_91" not in assessment["model_features"]
    assert "E_91" not in assessment["explicitly_absent_features"]


@pytest.mark.parametrize("text,code", [
    ("I have no fever", "fever"), ("Maybe I have fever", "fever"),
    ("My sister has cough", "cough"),
])
def test_absent_uncertain_other_subject_cannot_be_confirmed_positive(flow, text, code):
    response = flow.client.post("/symptoms/confirm", json={"text": text, "confirmed_codes": [code]})
    assert response.status_code == 400


@pytest.mark.parametrize("text", [
    "I am struggling to breathe", "Ninashindwa kupumua", "Siwezi kupumua",
    "I have no fever and am struggling to breathe", "I am gasping for air",
])
def test_emergency_cannot_be_rejected_or_blocked_by_catalogue_failure(flow, monkeypatch, text):
    def fail(*args, **kwargs):
        raise AssertionError("Emergency route attempted routine catalogue/model processing")
    monkeypatch.setattr(main, "confirm_symptoms", fail)
    monkeypatch.setattr(main, "get_active_model_version", fail)
    monkeypatch.setattr(main, "predict_top_conditions", fail)
    monkeypatch.setattr(main, "predict_v2_single", fail)
    response = flow.client.post("/predict", json=request(text, []))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "urgent_review"
    assert data["predictions"] == []
    assert data.get("follow_up_question") is None
    assert data["health_guidance"]


def test_emergency_map_does_not_require_live_database(flow, monkeypatch):
    def fail(*args, **kwargs):
        raise ServiceNotReadyError("Simulated unavailable symptom catalogue")
    monkeypatch.setattr(main, "build_confirmation_output", fail)
    response = flow.client.post("/nlp/map", json={"text": "Siwezi kupumua"})
    assert response.status_code == 200, response.text
    assert response.json()["has_red_flag"] is True
    assert response.json()["health_guidance"]


def test_emergency_guidance_survives_history_storage_failure(flow, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("Simulated unavailable history storage")
    monkeypatch.setattr(main, "save_prediction_session", fail)
    response = flow.client.post("/predict", json=request("I cannot breathe", []))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "urgent_review"


def test_followup_yes_immediately_triggers_emergency(flow):
    first = flow.client.post("/predict", json=request()).json()
    assert first["follow_up_question"]["id"] == "breathing_difficulty"
    response = flow.client.post("/predict", json=request(answers=[{"question_id": "breathing_difficulty", "answer": "yes"}]))
    assert response.status_code == 200
    assert response.json()["status"] == "urgent_review"
    assert response.json()["predictions"] == []


def test_followup_emergency_cannot_be_hidden_by_stale_trailing_answers(flow):
    answers = [{"question_id": "breathing_difficulty", "answer": "yes"},
               {"question_id": "symptom_duration", "answer": "under_3_days"},
               {"question_id": "fever", "answer": "no"}]
    response = flow.client.post("/predict", json=request(answers=answers))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "urgent_review"
    assert data["predictions"] == []
    assert data["assessment_context"]["questions_asked"] == ["breathing_difficulty"]
    assert data["assessment_context"]["follow_up_answers"] == answers[:1]


def test_followup_answers_change_the_recorded_profile(flow):
    answers = [{"question_id": "breathing_difficulty", "answer": "no"},
               {"question_id": "symptom_duration", "answer": "3_to_14_days"},
               {"question_id": "fever", "answer": "yes"}]
    response = flow.client.post("/predict", json=request(answers=answers))
    assert response.status_code == 200, response.text
    data = response.json()
    context = data["assessment_context"]
    assert context["symptom_states"]["shortness_of_breath"] == "absent"
    assert context["symptom_states"]["fever"] == "present"
    assert context["duration"]["min_days"] == 3
    assert context["duration"]["max_days"] == 14
    assert "E_91" in data["model_features"]
    assert context["questions_asked"] == [answer["question_id"] for answer in answers]
    assert data["status"] == ("assessment_uncertain" if any(value in {"present", "unknown"} for value in data["assessment_context"]["symptom_states"].values()) else "insufficient_evidence")
    assert flow.saved[-1]["assessment_context"]["follow_up_answers"] == context["follow_up_answers"]
    assert flow.saved[-1]["assessment_context"]["patient_decision"] == data["decision"]


@pytest.mark.parametrize("answers", [
    [{"question_id": "fever", "answer": "yes"}],
    [{"question_id": "breathing_difficulty", "answer": "banana"}],
    [{"question_id": "breathing_difficulty", "answer": "no"}, {"question_id": "breathing_difficulty", "answer": "no"}],
    [{"question_id": "symptom_duration", "answer": "2"}],
])
def test_out_of_order_invalid_or_duplicate_followups_rejected(flow, answers):
    response = flow.client.post("/predict", json=request(answers=answers))
    assert response.status_code in {400, 422}


def test_over_limit_followups_rejected(flow):
    # Uncapped gathering (authorised 2026-10-29): the hard ceiling is 20, so a
    # 21-answer payload is rejected, but 6 (over the old cap of 5) is accepted.
    from app.services.consultation import MAX_CONSULTATION_QUESTIONS
    assert MAX_CONSULTATION_QUESTIONS == 20
    response = flow.client.post("/predict", json=request(answers=[{"question_id": "breathing_difficulty", "answer": "no"}] * (MAX_CONSULTATION_QUESTIONS + 1)))
    assert response.status_code == 422


def test_replay_is_deterministic(flow):
    payload = request(answers=[{"question_id": "breathing_difficulty", "answer": "no"}])
    first = flow.client.post("/predict", json=payload).json()
    second = flow.client.post("/predict", json=payload).json()
    for field in ("status", "follow_up_question", "assessment_context", "model_features"):
        assert first[field] == second[field]


def test_existing_duration_and_severity_reach_assessment(flow):
    result = confirm_symptoms("I have a mild cough for two days", ["cough"], flow.db)
    assessment = prepare_assessment(result, [{"question_id": "breathing_difficulty", "answer": "no"}], "en", flow.db)
    context = assessment["assessment_context"]
    assert context["duration"]["min_days"] == 2
    assert context["severity"] == {"cough": "mild"}
    assert assessment["follow_up_question"]["id"] == "fever"


def test_swahili_question_meaning_and_language(flow):
    response = flow.client.post("/predict", json=request("Nina kikohozi", ["cough"], language="sw"))
    assert response.status_code == 200
    data = response.json()
    assert data["assessment_context"]["language"] == "sw"
    assert data["follow_up_question"]["id"] == "breathing_difficulty"
    labels = [item["label"] for item in data["follow_up_question"]["options"]]
    assert labels == ["1. Ndiyo", "2. Hapana", "3. Sina uhakika"]


@pytest.mark.parametrize("age,sex", [(0, "F"), (21, "M"), (21, "F"), (80, "M"), (120, "F")])
def test_sparse_input_policy_consistent_across_demographics(flow, age, sex):
    data = finish_questions(flow.client, request(age=age, sex=sex))
    assert data["status"] == ("assessment_uncertain" if any(value in {"present", "unknown"} for value in data["assessment_context"]["symptom_states"].values()) else "insufficient_evidence")
    assert data["predictions"] == []


def test_empty_text_is_rejected_without_predictions(flow):
    response = flow.client.post("/predict", json=request("", []))
    assert response.status_code == 422
    assert flow.saved == []


def test_v2_three_symptoms_defer_without_a_current_selection_policy(flow):
    flow.version.version = main.V2_MODEL_VERSION
    text = "I have a runny nose, headache and sore throat for two days"
    codes = ["runny_blocked_nose", "headache", "sore_throat"]
    data = finish_questions(flow.client, request(text, codes))
    assert data["uncertain"] is True
    assert data["predictions"] == [] and data["primary_prediction"] is None
    assert data["decision"]["reasons"] == ["legacy_model_requires_reassessment"]
    assert "score_note" not in data


def test_headache_present_and_chest_pain_absent_do_not_conflict(flow):
    result = confirm_symptoms("I have headache but no chest pain", ["headache"], flow.db)
    assert "E_53" in result["model_features"]
    assert "E_55_@_V_89" not in result["model_features"]
    assert "E_53" not in result["explicitly_absent_features"]
    assert "E_55_@_V_101" not in result["explicitly_absent_features"]
    assessment = prepare_assessment(result, [], "en", flow.db)
    assert not set(assessment["model_features"]) & set(assessment["explicitly_absent_features"])


def test_denied_headache_does_not_deny_all_pain(flow):
    result = confirm_symptoms("I have cough but no headache", ["cough"], flow.db)
    assert "E_53" not in result["explicitly_absent_features"]
    assert "E_55_@_V_89" not in result["explicitly_absent_features"]
    assessment = prepare_assessment(result, [], "en", flow.db)
    assert "E_53" not in assessment["explicitly_absent_features"]


@pytest.mark.parametrize("payload", [
    request(age=True), request(age=False), request(age=21.5), request(age="21"),
    request(age=-1), request(age=121), request(sex="male"),
    request(language="fr"), request(text=None), request(text="   "),
    request(confirmed_codes=[True]), request(confirmed_codes="cough"),
    request(unknown_client_field=True), request(assessment_context={"symptom_states": {"fever": "present"}}),
    request(answers=[{"question_id": "breathing_difficulty", "answer": "no", "extra": True}]),
])
def test_malformed_prediction_payloads_rejected_without_saving(flow, payload):
    response = flow.client.post("/predict", json=payload)
    assert response.status_code == 422, response.text
    assert flow.saved == []


@pytest.mark.parametrize("text,codes", [
    ("I have cough", ["cough"]),
    ("I have cough and fever", ["cough", "fever"]),
    ("Nina homa na kikohozi", ["cough", "fever"]),
])
def test_v2_sparse_inputs_do_not_force_a_disease(flow, text, codes):
    flow.version.version = main.V2_MODEL_VERSION
    data = finish_questions(flow.client, request(text, codes))
    assert data["status"] == ("assessment_uncertain" if any(value in {"present", "unknown"} for value in data["assessment_context"]["symptom_states"].values()) else "insufficient_evidence")
    assert data["uncertain"] is True
    assert data["predictions"] == []


def test_legacy_deferral_preserves_explicit_absence_without_running_v2(flow, monkeypatch):
    flow.version.version = main.V2_MODEL_VERSION
    captured = {}
    predictor = main.predict_v2_single

    def record(**kwargs):
        captured.update(kwargs)
        return predictor(**kwargs)

    monkeypatch.setattr(main, "predict_v2_single", record)
    text = "I have a runny nose, headache and sore throat for two days, but no fever"
    data = finish_questions(flow.client, request(text, ["runny_blocked_nose", "headache", "sore_throat"]))
    assert data["status"] == "assessment_uncertain"
    assert captured == {}  # No patient inference through the older model.
    assert "E_91" in data["explicitly_absent_features"]
    assert "E_91" not in data["model_features"]
    assert data["assessment_context"]["symptom_states"]["fever"] == "absent"


def test_fever_duration_does_not_supply_unreported_cough_duration(flow):
    text = "I have a cough. I have fever for two days."
    response = flow.client.post("/predict", json=request(
        text, ["cough", "fever"],
        answers=[{"question_id": "breathing_difficulty", "answer": "no"}],
    ))
    assert response.status_code == 200, response.text
    data = response.json()
    context = data["assessment_context"]
    assert context["duration"] is None
    assert context["symptom_durations"]["fever"]["min_days"] == 2
    assert "cough" not in context["symptom_durations"]
    assert data["follow_up_question"]["id"] == "symptom_duration"


def test_prolonged_cough_duration_is_preserved_separately_from_fever(flow):
    text = "I have had a cough for several weeks. I have fever for two days."
    response = flow.client.post("/predict", json=request(
        text, ["cough", "fever"],
        answers=[{"question_id": "breathing_difficulty", "answer": "no"}],
    ))
    assert response.status_code == 200, response.text
    data = response.json()
    context = data["assessment_context"]
    assert context["duration"]["symptom_code"] == "cough"
    assert context["duration"]["text"] == "for several weeks"
    assert context["symptom_durations"]["cough"]["text"] == "for several weeks"
    assert context["symptom_durations"]["fever"]["min_days"] == 2
    assert data["follow_up_question"]["id"] == "unexplained_weight_loss"


@pytest.mark.parametrize("text,language,advice", [
    ("I have had a cough for several weeks and have been losing weight.", "en", "arrange"),
    ("Nina kikohozi kwa wiki kadhaa na ninapungua uzito.", "sw", "tathmini"),
])
def test_prolonged_cough_weight_loss_gets_professional_advice_before_questions_finish(flow, text, language, advice):
    response = flow.client.post("/predict", json=request(text, ["cough", "weight_loss"], language=language))
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "needs_follow_up"
    assert data["follow_up_question"]["id"] == "breathing_difficulty"
    assert advice in data["health_guidance"].lower()
    assert data["predictions"] == []
    assert "tuberculosis" not in data["health_guidance"].lower()
