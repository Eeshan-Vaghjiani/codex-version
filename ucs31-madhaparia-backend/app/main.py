from contextlib import asynccontextmanager
from typing import Literal
import uuid
import logging

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.core.auth import (
    get_current_user,
    require_admin,
)
from app.core.config import settings
from app.core.database import check_schema, engine, get_db
from app.core.errors import ServiceNotReadyError
from app.core.security import create_access_token
from app.db.models import User, Symptom
from app.ml.model_loader import (
    model,
    model_features,
    disease_classes,
)
from app.nlp.symptom_mapper import build_confirmation_output
from app.services.assessment_safety import detect_safety_signs
from app.services.auth import (
    authenticate_user,
    create_patient_user,
)
from app.services.health_guidance import (
    enrich_predictions,
    get_prediction_guidance,
    get_urgent_guidance,
    get_insufficient_guidance,
    get_history_guidance,
)
from app.services.history import (
    get_any_prediction_session,
    get_prediction_session,
    list_all_feedback,
    list_all_prediction_sessions,
    list_prediction_sessions,
    save_feedback,
    save_prediction_session,
)
from app.services.prediction import predict_top_conditions

from app.ml.model_loader import V2_MODEL_VERSION
from app.services.v2_prediction import (
    partition_v2_symptom_features,
    predict_v2_single,
    get_v2_bundle,
)

from app.services.symptom_confirmation import confirm_symptoms
from app.services.assessment import (
    prepare_assessment, assessment_language, MIN_RESEARCH_PRESENT_FEATURES,
)

from app.services.consultation import prepare_consultation, V3_MODEL_VERSION
from app.services.v3_prediction import get_v3_bundle, predict_partial_evidence
from app.services.consultation_guidance import consultation_guidance, explain_v3_candidates, LIVE_MODEL_NOTICE

from app.services.primary_assessment import (
    build_primary_assessment, public_assessment_context, history_patient_projection,
    patient_guidance, PATIENT_POLICY_VERSION,
)

from app.services.model_versions import (
    get_active_model_version,
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are created by Alembic. Report readiness separately so
    # a storage outage cannot disable independent emergency guidance.
    try:
        check_schema()
        app.state.database_ready = True
    except (SQLAlchemyError, RuntimeError) as error:
        # Keep the bundled emergency endpoint available during outages.
        app.state.database_ready = False
        logging.getLogger(__name__).warning(
            "Database is not ready (%s); apply migrations or restore connectivity. Emergency mapping remains available.",
            type(error).__name__,
        )
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Backend API for the Respiratory Health Awareness "
        "and Prediction System."
    ),
)

allowed_origins = [
    origin.strip()
    for origin in settings.frontend_origins.split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ServiceNotReadyError)
def service_not_ready_handler(
    request: Request,
    error: ServiceNotReadyError,
):
    return JSONResponse(
        status_code=503,
        content={
            "detail": str(error),
        },
    )


@app.exception_handler(SQLAlchemyError)
def database_unavailable_handler(request: Request, error: SQLAlchemyError):
    return JSONResponse(status_code=503, content={
        "detail": "Database unavailable or schema not ready. Restore connectivity and apply Alembic migrations."
    })


# ---------------------------------------------------------
# Request Models
# ---------------------------------------------------------

MAX_SYMPTOM_TEXT_LENGTH = 2000
MAX_CONFIRMED_CODES = 50


class SymptomTextRequest(BaseModel):
    language: Literal["en", "sw"] | None = None
    breathing_check: Literal['at_rest_or_cannot_speak', 'exertion_full_sentence', 'unknown'] | None = None

    @field_validator("text", check_fields=False)
    @classmethod
    def meaningful_text(cls, value):
        if not value.strip():
            raise ValueError("Please describe your symptoms.")
        return value

    text: str = Field(
        max_length=MAX_SYMPTOM_TEXT_LENGTH,
    )


class SymptomConfirmationRequest(BaseModel):
    text: str = Field(
        max_length=MAX_SYMPTOM_TEXT_LENGTH,
    )
    confirmed_codes: list[str] = Field(
        max_length=MAX_CONFIRMED_CODES,
    )


class FollowUpAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: str = Field(min_length=1, max_length=80)
    answer: str = Field(min_length=1, max_length=80)


class PredictionRequest(SymptomTextRequest):
    model_config = ConfigDict(extra="forbid")
    follow_up_answers: list[FollowUpAnswer] = Field(default_factory=list, max_length=5)
    age: int = Field(ge=0, le=120, strict=True)
    sex: Literal["M", "F"]
    text: str = Field(
        max_length=MAX_SYMPTOM_TEXT_LENGTH,
    )
    confirmed_codes: list[str] = Field(
        max_length=MAX_CONFIRMED_CODES,
    )


class FeedbackRequest(BaseModel):
    prediction_id: uuid.UUID
    was_helpful: bool
    comment: str | None = Field(
        default=None,
        max_length=1000,
    )


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        min_length=8,
        max_length=128,
    )


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(
        max_length=128,
    )


# ---------------------------------------------------------
# General Endpoints
# ---------------------------------------------------------

@app.get("/")
def root():
    return {
        "message": (
            "Respiratory Health Awareness API is running."
        )
    }


@app.get("/health")
def health_check():
    return {
        "status": "degraded" if getattr(app.state, "database_ready", True) is False else "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


@app.get("/database/status")
def database_status():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        return {
            "status": "connected",
            "database": engine.dialect.name,
        }

    except Exception as error:
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable.",
        ) from error


@app.get("/model/status")
def model_status(db: Session = Depends(get_db)):
    active = get_active_model_version(db)
    if active.version == V3_MODEL_VERSION:
        bundle = get_v3_bundle()
        from app.ml.primary_selection import load_gap_policy
        gap_policy = load_gap_policy()
        return {
            "status": "loaded", "model_version": V3_MODEL_VERSION,
            "model_type": bundle["model_type"], "feature_count": len(bundle["features"]),
            "model_feature_count": len(bundle["features"]), "class_count": len(bundle["classes"]),
            "model_class_count": len(bundle["classes"]), "clinical_validation": False,
            "live_model_notice": LIVE_MODEL_NOTICE,
            "training_data": "simulated DDXPlus only", "covid_in_scope": False,
            "gap_validation": "source_validation_checked" if gap_policy else "pending_fresh_fold",
            "patient_naming_enabled": bool(gap_policy and any(item['enabled'] for item in gap_policy['buckets'].values())),
            "gap_source_note": gap_policy.get('source_note') if gap_policy else None,
        }
    if active.version == V2_MODEL_VERSION:
        bundle = get_v2_bundle()
        current_model, features, classes = bundle["model"], bundle["features"], bundle["classes"]
    elif active.version == "1.0":
        if model is None:
            raise ServiceNotReadyError("The V1 model artifacts are unavailable or invalid. Emergency symptom guidance remains available.")
        current_model, features, classes = model, model_features, disease_classes
    else:
        raise ServiceNotReadyError("The active model version is not supported.")
    return {
        "status": "loaded", "model_version": active.version,
        "model_type": type(current_model).__name__,
        "feature_count": len(features), "model_feature_count": int(current_model.n_features_in_),
        "class_count": len(classes), "model_class_count": len(current_model.classes_),
        "clinical_validation": False,
    }



# ---------------------------------------------------------
# Authentication Endpoints
# ---------------------------------------------------------

@app.post(
    "/auth/register",
    status_code=201,
)
def register_patient(
    request: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        user = create_patient_user(
            db,
            email=str(request.email),
            password=request.password,
        )

        return {
            "id": str(user.id),
            "email": user.email,
            "role": user.role,
            "created_at": user.created_at,
        }

    except ValueError as error:
        raise HTTPException(
            status_code=409,
            detail=str(error),
        ) from error


@app.post("/auth/login")
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    user = authenticate_user(
        db,
        email=str(request.email),
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in_minutes": (
            settings.access_token_expire_minutes
        ),
    }


@app.get("/auth/me")
def get_authenticated_user(
    current_user: User = Depends(
        get_current_user
    ),
):
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }


# ---------------------------------------------------------
# NLP Endpoints
# ---------------------------------------------------------

@app.post("/nlp/map")
def map_symptoms(
    request: SymptomTextRequest,
    db: Session = Depends(get_db),
):
    language = assessment_language(request.text, request.language)
    red_flags = detect_safety_signs(request.text)
    if red_flags:
        from app.services.assessment_safety import safety_guidance
        return {
            "input_text": request.text, "recognised_symptoms": red_flags,
            "unmatched_wording": [], "has_red_flag": True,
            "safety_status": "urgent_review", "requires_confirmation": False,
            **safety_guidance(red_flags, language, request.breathing_check),
        }
    from app.services.health_guidance import get_prediction_guidance
    return {**build_confirmation_output(request.text, db),
            'disclaimer': get_prediction_guidance(language)['disclaimer']}



@app.post("/symptoms/confirm")
def confirm_recognised_symptoms(
    request: SymptomConfirmationRequest,
    db: Session = Depends(get_db),
):
    try:
        result = confirm_symptoms(
            text=request.text,
            confirmed_codes=request.confirmed_codes,
            db=db,
        )
        from app.services.health_guidance import get_prediction_guidance
        result['disclaimer'] = get_prediction_guidance(assessment_language(request.text))['disclaimer']
        return result

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error


# ---------------------------------------------------------
# Prediction Endpoint
# ---------------------------------------------------------

@app.post("/predict")
def predict_conditions(
    request: PredictionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    language = assessment_language(request.text, request.language)
    answers = [answer.model_dump() for answer in request.follow_up_answers]
    red_flags = detect_safety_signs(request.text, age=request.age)
    active = None
    try:
        if red_flags:
            confirmation = {
                "confirmed_codes": request.confirmed_codes, "model_features": [],
                "has_red_flag": True, "red_flag_symptoms": red_flags,
                "assessment_context": {"language": language, "follow_up_answers": [],
                    "symptom_states": {flag['code']: flag.get('status', 'present') for flag in red_flags},
                    "severity": {flag['code']: 'severe' for flag in red_flags if flag.get('breathing_tier') == 'emergency'}},
            }
        else:
            confirmation = confirm_symptoms(request.text, request.confirmed_codes, db)
            if confirmation["confirmed_codes"] and not confirmation["has_red_flag"]:
                active = get_active_model_version(db)
            if active is not None and active.version == V3_MODEL_VERSION:
                confirmation = prepare_consultation(confirmation, answers, language, db, request.age, request.sex)
            else:
                confirmation = prepare_assessment(confirmation, answers, language, db, request.age)
        context = confirmation["assessment_context"]
        context["age"] = request.age
        if active is not None:
            context["model_version"] = active.version

        def base():
            return {
                "age": request.age, "sex": request.sex,
                "confirmed_codes": request.confirmed_codes,
                "effective_confirmed_codes": confirmation["confirmed_codes"],
                "model_features": confirmation["model_features"],
                "explicitly_absent_features": confirmation.get("explicitly_absent_features", []),
                "assessment_context": public_assessment_context(context),
                "follow_up_answers": context.get("follow_up_answers", answers),
                "has_red_flag": confirmation["has_red_flag"], "predictions": [], "primary_prediction": None,
                "clinical_validation": False, "uncertain": True,
            }

        def persist(status, predictions, version_id=None):
            saved = save_prediction_session(
                db, user_id=current_user.id, age=request.age, sex=request.sex,
                input_text=request.text, confirmed_codes=confirmation["confirmed_codes"],
                model_features=confirmation["model_features"], status=status,
                has_red_flag=confirmation["has_red_flag"], predictions=predictions,
                model_version_id=version_id, assessment_context=context,
            )
            return str(saved.id)

        if confirmation["has_red_flag"]:
            decision = {"status": "urgent_review", "reasons": ["reported_warning_sign"],
                        "policy_version": PATIENT_POLICY_VERSION}
            context["patient_decision"] = decision
            from app.services.assessment_safety import safety_guidance
            guidance = safety_guidance(confirmation['red_flag_symptoms'], language, request.breathing_check)
            context['urgency'] = guidance['urgency']
            prediction_id = None
            try:
                prediction_id = persist("urgent_review", [])
            except Exception:
                logging.getLogger(__name__).exception("Could not save urgent assessment")
                if hasattr(db, "rollback"):
                    db.rollback()
            if any(flag.get("code") == "infant_fever" for flag in confirmation["red_flag_symptoms"]):
                guidance["health_guidance"] = (
                    "Homa kwa mtoto mchanga inahitaji tathmini ya haraka ya mtaalamu wa afya, hasa chini ya miezi mitatu. Nenda idara ya dharura ya hospitali iliyo karibu sasa. Usisubiri maswali zaidi."
                    if language == "sw" else
                    "Fever in a baby needs prompt medical assessment, especially under three months. Go to the nearest hospital casualty now. Do not wait to complete more questions."
                )
            return {**base(), "prediction_id": prediction_id, "status": "urgent_review", "decision": decision,
                    "red_flag_symptoms": confirmation["red_flag_symptoms"], **guidance}

        question = confirmation.get("follow_up_question")
        if question:
            guidance_context = dict(context, _present_features=confirmation["model_features"])
            return {
                **base(), "status": "needs_follow_up", "follow_up_question": question,
                "decision": {"status": "uncertain", "reasons": ["follow_up_needed"], "policy_version": PATIENT_POLICY_VERSION},
                **patient_guidance(guidance_context, request.age),
            }

        if active is not None and active.version == V3_MODEL_VERSION:
            result = build_primary_assessment(confirmation, request.age, request.sex)
            context["_primary_audit"] = result.pop("_audit")
            context["patient_decision"] = result["decision"]
            context["_patient_primary"] = result["primary_prediction"]
            prediction_id = persist(result["status"], result["predictions"], active.id)
            return {**base(), "prediction_id": prediction_id, "model_version": V3_MODEL_VERSION,
                    "feature_count": len(get_v3_bundle()["features"]), **result}

        # Legacy models have no current validated patient selection policy.
        # They remain available for audit/comparison, never silently replacing V3.
        reported = any(value in {"present", "unknown"} for value in context.get("symptom_states", {}).values())
        status = "assessment_uncertain" if reported else "insufficient_evidence"
        decision = {"status": "uncertain" if reported else "insufficient_information",
                    "reasons": ["legacy_model_requires_reassessment" if active else "insufficient_evidence"],
                    "policy_version": PATIENT_POLICY_VERSION}
        context["patient_decision"] = decision
        context["_patient_primary"] = None
        prediction_id = persist(status, [], active.id) if active else None
        return {**base(), "prediction_id": prediction_id, "status": status, "decision": decision,
                "model_version": active.version if active else None,
                "uncertain": True, "clinical_validation": False,
                **patient_guidance(dict(context, _present_features=confirmation["model_features"]), request.age, decision["status"])}
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


# ---------------------------------------------------------
# Patient History Endpoints
# ---------------------------------------------------------

@app.get("/history")
def get_patient_history(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    sessions = list_prediction_sessions(
        db,
        user_id=current_user.id,
        limit=limit,
    )

    return {"count": len(sessions), "history": [history_patient_projection(session) for session in sessions]}


# ---------------------------------------------------------
# Admin Endpoints
# ---------------------------------------------------------

@app.get("/admin/history")
def get_admin_history(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin
    ),
):
    sessions = list_all_prediction_sessions(
        db,
        limit=limit,
    )

    return {
        "count": len(sessions),
        "history": [
            {
                "prediction_id": str(
                    session.id
                ),
                "user_id": (
                    str(session.user_id)
                    if session.user_id
                    else None
                ),
                "age": session.age,
                "sex": session.sex,
                "input_text": (
                    session.input_text
                ),
                "confirmed_codes": (
                    session.confirmed_codes
                ),
                "status": session.status,
                "has_red_flag": (
                    session.has_red_flag
                ),
                "predictions": (
                    session.predictions
                ),
                "assessment_context": getattr(session, "assessment_context", {}),
                **get_history_guidance(session.status, getattr(session, "assessment_context", {})),
                "created_at": (
                    session.created_at
                ),
            }
            for session in sessions
        ],
    }


@app.get("/admin/history/{prediction_id}")
def get_admin_history_item(
    prediction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin
    ),
):
    session = get_any_prediction_session(
        db,
        prediction_id=prediction_id,
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Prediction session was not found."
            ),
        )

    return {
        "prediction_id": str(session.id),
        "user_id": (
            str(session.user_id)
            if session.user_id
            else None
        ),
        "age": session.age,
        "sex": session.sex,
        "input_text": session.input_text,
        "confirmed_codes": (
            session.confirmed_codes
        ),
        "status": session.status,
        "has_red_flag": (
            session.has_red_flag
        ),
        "predictions": session.predictions,
        "assessment_context": getattr(session, "assessment_context", {}),
        **get_history_guidance(session.status, getattr(session, "assessment_context", {})),
        "created_at": session.created_at,
    }


@app.get("/admin/feedback")
def get_admin_feedback(
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
    ),
    db: Session = Depends(get_db),
    current_admin: User = Depends(
        require_admin
    ),
):
    feedback_items = list_all_feedback(
        db,
        limit=limit,
    )

    return {
        "count": len(feedback_items),
        "feedback": [
            {
                "feedback_id": str(
                    item.id
                ),
                "prediction_id": str(
                    item.prediction_session_id
                ),
                "was_helpful": (
                    item.was_helpful
                ),
                "comment": item.comment,
                "created_at": (
                    item.created_at
                ),
            }
            for item in feedback_items
        ],
    }

@app.get("/history/{prediction_id}")
def get_patient_history_item(
    prediction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    session = get_prediction_session(
        db,
        prediction_id=prediction_id,
        user_id=current_user.id,
    )

    if session is None:
        raise HTTPException(
            status_code=404,
            detail=(
                "Prediction session was not found."
            ),
        )

    return history_patient_projection(session)



# ---------------------------------------------------------
# Feedback Endpoint
# ---------------------------------------------------------

@app.post("/feedback")
def submit_feedback(
    request: FeedbackRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        get_current_user
    ),
):
    try:
        feedback = save_feedback(
            db,
            prediction_session_id=(
                request.prediction_id
            ),
            user_id=current_user.id,
            was_helpful=(
                request.was_helpful
            ),
            comment=request.comment,
        )

        return {
            "status": "feedback_saved",
            "feedback_id": str(
                feedback.id
            ),
            "prediction_id": str(
                feedback.prediction_session_id
            ),
            "was_helpful": (
                feedback.was_helpful
            ),
            "comment": feedback.comment,
            "created_at": (
                feedback.created_at
            ),
        }

    except LookupError as error:
        raise HTTPException(
            status_code=404,
            detail=(
                "Prediction session was not found."
            ),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        ) from error
