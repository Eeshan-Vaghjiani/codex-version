"""Register/activate the tested partial-evidence model in an explicitly chosen DB.

No network connection or activation occurs on import; callers own transactions.
"""
from sqlalchemy import select
from app.db.models import ModelVersion
from app.services.v3_prediction import get_v3_bundle
from app.services.consultation import V3_MODEL_VERSION


def registration_values():
    bundle = get_v3_bundle()
    metadata = bundle['metadata']
    if metadata['clinical_validation'] is not False or metadata['final_test_used_for_selection'] is not False:
        raise ValueError('Unexpected partial-evidence evaluation/validation metadata')
    if len(bundle['classes']) != 21 or len(bundle['features']) != 34:
        raise ValueError('Unexpected partial-evidence schema')
    return {
        'model_name': 'Partial-evidence likelihood', 'version': V3_MODEL_VERSION,
        'purpose': 'Tentative respiratory condition patterns from partial symptom reports; research, not diagnosis',
        'artifact_filename': 'v3_partial_evidence.json', 'feature_count': len(bundle['features']),
        'class_count': len(bundle['classes']), 'training_samples': metadata['training_count'],
        'validation_samples': metadata['validation_count'], 'test_samples': metadata['test_count'],
        'parameters': {'demographic_mode': bundle['demographic_mode'], 'age_edges': bundle['age_edges'],
                       'temperature': bundle['temperature'], 'demographic_shrinkage': bundle['demographic_shrinkage'],
                       'clinical_validation': False, 'negative_evidence_provenance': bundle['negative_evidence_provenance']},
        'validation_metrics': metadata['validation_metrics'], 'test_metrics': metadata['test_metrics'],
    }


def register_v3_model_version(db):
    values = registration_values()
    versions = list(db.scalars(select(ModelVersion).with_for_update()).all())
    found = [row for row in versions if row.version == V3_MODEL_VERSION and row.model_name == values['model_name']]
    if len(found) > 1:
        raise ValueError('Multiple partial-evidence registrations found')
    if found:
        row = found[0]
        for key, value in values.items():
            setattr(row, key, value)
    else:
        row = ModelVersion(**values, is_active=False)
        db.add(row)
    db.flush()
    return row


def activate_v3_model_version(db):
    row = register_v3_model_version(db)
    versions = list(db.scalars(select(ModelVersion).with_for_update()).all())
    if sum(item.is_active for item in versions) > 1:
        raise ValueError('Multiple active model versions; resolve before switching')
    for item in versions:
        item.is_active = item.id == row.id
    db.flush()
    return row
