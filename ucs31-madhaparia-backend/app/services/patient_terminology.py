"""Maintainable localized patient terminology; never changes model classes."""
import json
from functools import lru_cache
from pathlib import Path

TERMINOLOGY_PATH = Path(__file__).resolve().parents[1] / 'data/patient_terminology.json'


@lru_cache(maxsize=1)
def terminology():
    data = json.loads(TERMINOLOGY_PATH.read_text(encoding='utf-8'))
    if data.get('schema_version') != 1 or not isinstance(data.get('conditions'), dict):
        raise ValueError('Invalid patient terminology dictionary')
    return data


def patient_term(condition, language='en'):
    entry = terminology()['conditions'].get(condition)
    if not entry:
        raise ValueError(f'No patient terminology entry for model class: {condition}')
    lang = 'sw' if language == 'sw' else 'en'
    display = entry['display_name'][lang]
    # Stable dual format, enforced: simple Kenyan-known name or plain
    # meaning first, medical name in parentheses, never one alone.
    if '(' not in display or not display.endswith(')'):
        raise ValueError(f'Patient terminology entry is not in dual format: {condition} ({lang})')
    simple = display.rsplit(' (', 1)[0]
    return {'condition': condition, 'medical_name': entry['medical_name'],
            'display_name': display, 'dual_name': display, 'simple_name': simple,
            'description': entry['description'][lang]}
