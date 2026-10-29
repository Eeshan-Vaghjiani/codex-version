from fastapi.testclient import TestClient

from app.main import app
from app.nlp import symptom_mapper


client = TestClient(app)


def test_nlp_mixed_english_swahili():
    response = client.post(
        "/nlp/map",
        json={
            "text": "I have fever na kikohozi"
        },
    )

    assert response.status_code == 200

    data = response.json()

    codes = {
        symptom["code"]
        for symptom in data["recognised_symptoms"]
    }

    assert "fever" in codes
    assert "cough" in codes
    assert data["requires_confirmation"] is True


def test_nlp_fuzzy_spelling():
    response = client.post(
        "/nlp/map",
        json={
            "text": "I have a couhg and feaver"
        },
    )

    assert response.status_code == 200

    data = response.json()

    codes = {
        symptom["code"]
        for symptom in data["recognised_symptoms"]
    }

    assert "cough" in codes
    assert "fever" in codes


def test_nlp_unmatched_wording():
    response = client.post(
        "/nlp/map",
        json={
            "text": "I have fever and a skin rash"
        },
    )

    assert response.status_code == 200

    data = response.json()

    codes = {
        symptom["code"]
        for symptom in data["recognised_symptoms"]
    }

    assert "fever" in codes

    unmatched = [
        item["unmatched_text"]
        for item in data["unmatched_wording"]
    ]

    assert "skin rash" in unmatched


def test_symptom_confirmation():
    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "I have fever na kikohozi",
            "confirmed_codes": [
                "fever",
                "cough",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert set(data["confirmed_codes"]) == {
        "fever",
        "cough",
    }

    assert set(data["model_features"]) == {
        "E_91",
        "E_201",
    }

    assert data["has_red_flag"] is False
    assert data["safety_status"] == "continue"
    assert data["requires_confirmation"] is False


def test_partial_confirmation():
    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "I have fever and cough",
            "confirmed_codes": [
                "fever",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["confirmed_codes"] == [
        "fever",
    ]

    assert data["model_features"] == [
        "E_91",
    ]

    rejected_codes = {
        symptom["code"]
        for symptom in data["rejected_symptoms"]
    }

    assert "cough" in rejected_codes


def test_red_flag_confirmation():
    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "I am coughing up blood",
            "confirmed_codes": [
                "coughing_blood",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["has_red_flag"] is True
    assert data["safety_status"] == "urgent_review"

    red_flag_codes = {
        symptom["code"]
        for symptom in data["red_flag_symptoms"]
    }

    assert "coughing_blood" in red_flag_codes
    assert "E_45" in data["model_features"]


def test_safety_only_red_flag():
    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "My lips are turning blue",
            "confirmed_codes": [
                "blue_lips",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["has_red_flag"] is True
    assert data["safety_status"] == "urgent_review"
    assert data["model_features"] == []


def test_invalid_confirmation():
    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "I have fever",
            "confirmed_codes": [
                "skin_rash",
            ],
        },
    )

    assert response.status_code == 400

    data = response.json()

    assert "skin_rash" in data["detail"]

def test_nlp_endpoint_uses_database_catalog(
    monkeypatch,
):
    def fail_json_load(*args, **kwargs):
        raise AssertionError(
            "JSON catalogue should not be used "
            "by the API."
        )

    monkeypatch.setattr(
        symptom_mapper,
        "load_json",
        fail_json_load,
    )

    response = client.post(
        "/nlp/map",
        json={
            "text": "I have fever na kikohozi"
        },
    )

    assert response.status_code == 200

    data = response.json()

    codes = {
        symptom["code"]
        for symptom
        in data["recognised_symptoms"]
    }

    assert "fever" in codes
    assert "cough" in codes


def test_confirmation_endpoint_uses_database_catalog(
    monkeypatch,
):
    def fail_json_load(*args, **kwargs):
        raise AssertionError(
            "JSON catalogue should not be used "
            "by the API."
        )

    monkeypatch.setattr(
        symptom_mapper,
        "load_json",
        fail_json_load,
    )

    response = client.post(
        "/symptoms/confirm",
        json={
            "text": "I have fever and cough",
            "confirmed_codes": [
                "fever",
                "cough",
            ],
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert set(
        data["confirmed_codes"]
    ) == {
        "fever",
        "cough",
    }

    assert set(
        data["model_features"]
    ) == {
        "E_91",
        "E_201",
    }