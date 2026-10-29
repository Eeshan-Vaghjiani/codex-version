from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)


def test_root():
    response = client.get("/")

    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "Respiratory Health Awareness API is running."
    )


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "ok"
    assert "service" in data
    assert "environment" in data


def test_model_status():
    response = client.get("/model/status")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "loaded"
    assert data["model_type"] == "RandomForestClassifier"
    assert data["feature_count"] == 198
    assert data["model_feature_count"] == 198
    assert data["class_count"] == 21
    assert data["model_class_count"] == 21


def test_database_status_connected(monkeypatch):
    class FakeConnection:
        def __enter__(self):
            return self

        def __exit__(
            self,
            exc_type,
            exc_value,
            traceback,
        ):
            return False

        def execute(self, statement):
            return None

    class FakeDialect:
        name = "postgresql"

    class FakeEngine:
        dialect = FakeDialect()

        def connect(self):
            return FakeConnection()

    monkeypatch.setattr(
        main_module,
        "engine",
        FakeEngine(),
    )

    response = client.get("/database/status")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "connected"
    assert data["database"] == "postgresql"


def test_database_status_unavailable(monkeypatch):
    class FakeEngine:
        def connect(self):
            raise RuntimeError(
                "Database unavailable"
            )

    monkeypatch.setattr(
        main_module,
        "engine",
        FakeEngine(),
    )

    response = client.get("/database/status")

    assert response.status_code == 503
    assert (
        response.json()["detail"]
        == "Database connection unavailable."
    )

def test_cors_allows_frontend_origin():
    response = client.options(
        "/auth/register",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "content-type"
            ),
        },
    )

    assert response.status_code == 200

    assert (
        response.headers[
            "access-control-allow-origin"
        ]
        == "http://localhost:5173"
    )

def test_cors_does_not_allow_unknown_origin():
    response = client.options(
        "/auth/register",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert (
        "access-control-allow-origin"
        not in response.headers
    )

def test_model_status_reflects_active_v2(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(main_module, "get_active_model_version",
                        lambda db: SimpleNamespace(version=main_module.V2_MODEL_VERSION))
    response = client.get("/model/status")
    assert response.status_code == 200
    data = response.json()
    assert data["model_version"] == main_module.V2_MODEL_VERSION
    assert data["feature_count"] == data["model_feature_count"] == 66
    assert data["class_count"] == data["model_class_count"] == 23
    assert data["clinical_validation"] is False


def test_invalid_active_artifact_returns_503_without_fallback(monkeypatch):
    from types import SimpleNamespace
    from app.services import v2_prediction
    monkeypatch.setattr(main_module, "get_active_model_version",
                        lambda db: SimpleNamespace(version=main_module.V2_MODEL_VERSION))
    v2_prediction.get_v2_bundle.cache_clear()
    def corrupt():
        raise KeyError("Malformed artifact")
    monkeypatch.setattr(v2_prediction, "load_v2_model_bundle", corrupt)
    try:
        response = client.get("/model/status")
        assert response.status_code == 503
        assert "no fallback" in response.json()["detail"]
    finally:
        v2_prediction.get_v2_bundle.cache_clear()
