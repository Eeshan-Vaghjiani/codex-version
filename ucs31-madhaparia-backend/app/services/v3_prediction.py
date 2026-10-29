"""Backend adapter for the partial-evidence research model."""
from functools import lru_cache
from app.core.errors import ServiceNotReadyError


@lru_cache(maxsize=1)
def get_v3_bundle():
    from app.ml.v3_predictor import load_v3_bundle
    try:
        return load_v3_bundle()
    except Exception as error:
        raise ServiceNotReadyError('The partial-evidence model is unavailable or invalid; no alternative model was silently activated.') from error


def _partition(present, absent):
    supported = set(get_v3_bundle()['features'])
    return ([f for f in dict.fromkeys(present) if f in supported],
            [f for f in dict.fromkeys(absent) if f in supported],
            sorted((set(present) | set(absent)) - supported))


def rank_follow_up_features(present, absent, age, sex, candidates):
    from app.ml.v3_predictor import question_information_gain
    get_v3_bundle()
    positives, negatives, _ = _partition(present, absent)
    candidates = [feature for feature in candidates if feature in get_v3_bundle()['features']]
    return question_information_gain(positives, negatives, age, sex, candidates)


def predict_partial_evidence(present, absent, age, sex):
    from app.ml.v3_predictor import predict_v3
    get_v3_bundle()
    positives, negatives, unsupported = _partition(present, absent)
    result = predict_v3(positives, negatives, age, sex)
    result['unsupported_model_features'] = unsupported
    result['feature_count'] = len(get_v3_bundle()['features'])
    return result
