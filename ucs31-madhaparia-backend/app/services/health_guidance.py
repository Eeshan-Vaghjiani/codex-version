import json
from pathlib import Path


CONDITION_INFO_PATH = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "condition_information.json"
)


with CONDITION_INFO_PATH.open(
    "r",
    encoding="utf-8",
) as file:
    CONDITION_INFORMATION = json.load(file)


CONFIDENCE_EXPLANATION = (
    "The model confidence shows how strongly the submitted "
    "symptom pattern matched each condition in the trained model. "
    "It is not the probability that you have that condition and "
    "it is not a medical diagnosis."
)


GENERAL_GUIDANCE = (
    "Use these results as general health-awareness information. "
    "If symptoms persist, worsen, become severe, or concern you, "
    "consider seeking assessment from a healthcare professional."
)


URGENT_GUIDANCE = (
    "A confirmed red-flag symptom was detected. "
    "Seek urgent medical assessment. If symptoms are severe "
    "or rapidly worsening, contact local emergency services."
)


DISCLAIMER = (
    "This system provides health-awareness information only. "
    "It does not provide a medical diagnosis and should not "
    "replace assessment by a qualified healthcare professional. "
    "It has not been clinically validated for patients in Kenya and considers only a limited set of respiratory conditions."
)


def enrich_predictions(
    predictions: list[dict],
) -> list[dict]:
    enriched_predictions = []

    for prediction in predictions:
        condition = prediction["condition"]

        if condition not in CONDITION_INFORMATION:
            raise ValueError(
                f"No condition information found for: {condition}"
            )

        condition_info = CONDITION_INFORMATION[condition]

        enriched_predictions.append(
            {
                "rank": prediction["rank"],
                "condition": condition,
                "display_name": condition_info["display_name"],
                "model_confidence_percent": (
                    prediction["confidence_percent"]
                ),
                "description": (
                    condition_info["short_description"]
                ),
            }
        )

    return enriched_predictions


def get_prediction_guidance(language="en", context=None) -> dict:
    context = context or {}
    states = context.get("symptom_states", {})
    duration = context.get("duration") or {}
    prolonged = (duration.get("min_days") >= 14 if duration.get("min_days") is not None else any(
        word in str(duration.get("text", "")).lower() for word in ("weeks", "months", "wiki", "miezi")))
    assessment_advice = (
        ("Tafuta tathmini ya mtaalamu wa afya mapema kwa kikohozi cha muda mrefu au kupungua uzito bila kukusudia. "
         if language == "sw" else
         "Arrange professional medical assessment promptly for prolonged cough or unexplained weight loss. ")
        if states.get("weight_loss") == "present" or (states.get("cough") == "present" and prolonged)
        else ""
    )
    if language == "sw":
        return {
            "confidence_explanation": "Alama ya modeli haijarekebishwa kuwa uwezekano wa kitabibu. Si uwezekano kwamba una ugonjwa huu.",
            "health_guidance": assessment_advice + "Dalili zikiendelea, zikizidi au zikikutia wasiwasi, tafuta tathmini ya mtaalamu wa afya. Alama ndogo haimaanishi hatari ndogo.",
            "disclaimer": "Mfumo huu hutoa mwongozo tu, si utambuzi wa ugonjwa wala mbadala wa mtaalamu wa afya aliyehitimu. Haujathibitishwa kitabibu kwa wagonjwa nchini Kenya na hutathmini baadhi tu ya magonjwa ya mfumo wa upumuaji.",
        }
    return {
        "confidence_explanation": CONFIDENCE_EXPLANATION,
        "health_guidance": assessment_advice + GENERAL_GUIDANCE + " A low model score does not mean low medical risk.",
        "disclaimer": DISCLAIMER,
    }


def get_urgent_guidance(language="en") -> dict:
    if language == "sw":
        return {
            "health_guidance": "Dalili ya hatari imetambuliwa. Tafuta huduma ya matibabu ya haraka. Ikiwa unapumua kwa shida sana, unashindwa kuzungumza, au hali inazidi haraka, tafuta huduma ya dharura sasa. Usisubiri kukamilisha maswali haya.",
            "disclaimer": get_prediction_guidance(language)["disclaimer"],
        }
    return {
        "health_guidance": "A warning sign was detected. Seek urgent medical assessment. If breathing difficulty is severe, you cannot speak normally, or symptoms are rapidly worsening, seek emergency care now. Do not wait to complete this questionnaire.",
        "disclaimer": DISCLAIMER,
    }


def get_insufficient_guidance(language="en", context=None) -> dict:
    return {
        **get_prediction_guidance(language, context),
        "uncertainty_message": (
            "Taarifa hizi hazitoshi kutambua ugonjwa kwa uhakika. Modeli hii ni ya utafiti na haijathibitishwa kitabibu. Tafuta tathmini ya mtaalamu wa afya kulingana na dalili zako."
            if language == "sw" else
            "This information cannot reliably distinguish a condition. The model is experimental and has not been clinically validated. Seek professional assessment based on your symptoms."
        ),
        "score_note": (
            "Alama za modeli si uwezekano wa kitabibu uliothibitishwa."
            if language == "sw" else
            "Model scores are uncalibrated and are not validated clinical probabilities."
        ),
    }


def get_history_guidance(status, context=None):
    """Keep safety/uncertainty visible when revisiting current or legacy records."""
    context = context or {}
    language = context.get("language", "en")
    if status == "urgent_review":
        return get_urgent_guidance(language)
    if context.get("model_version") == "v3_partial_evidence":
        from app.services.consultation_guidance import consultation_guidance
        return {
            **consultation_guidance(context, context.get("age", 21)),
            "uncertain": True,
            "uncertainty_reasons": context.get("uncertainty_reasons", ["simulated_source_not_clinically_validated"]),
            "model_version": "v3_partial_evidence", "clinical_validation": False,
            "model_status": "research_partial_evidence",
        }
    return {
        **get_insufficient_guidance(language, context),
        "uncertain": True,
        "uncertainty_reasons": context.get("uncertainty_reasons", ["not_clinically_validated"]),
        "model_version": context.get("model_version", "legacy_unknown"),
        "clinical_validation": False,
        "model_status": "research_prototype" if context.get("model_version") == "v2_23class_prototype" else "legacy_unvalidated",
    }
