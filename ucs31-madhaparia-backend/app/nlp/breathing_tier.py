"""Graded breathing tier, independent of the model score.

Tier E (emergency): can't breathe / gasping / cannot speak / difficulty at rest.
Tier U (urgent same-day): difficulty breathing only on exertion, can speak a
full sentence, after exactly one severity check.
No tier: no breathing difficulty, or a negated statement such as
"I can breathe fine" / "napumua vizuri".

This is wording + one severity check only. It never uses a model score, and
it never turns a Tier U case into a prediction without urgent guidance.
"""
import re

def _norm(text):
    return re.sub(r"\s+", " ", (text or "").lower().replace("\u2019", "'").replace("\u2018", "'")).strip()

_NEGATIVES = (
    "can breathe fine", "breathe fine", "breathing fine", "breathe normally",
    "breathing normally", "no difficulty breathing", "no shortness of breath",
    "not short of breath", "sina shida ya kupumua", "napumua vizuri",
    "hakuna shida ya kupumua",
)
_EMERGENCY = (
    "can't breathe", "cannot breathe", "can not breathe", "unable to breathe",
    "can't catch my breath", "cannot catch my breath", "gasping",
    "cannot speak", "can't speak", "unable to speak", "cannot talk",
    "siwezi kupumua", "ninashindwa kupumua", "nashindwa kupumua",
    "kushindwa kupumua", "siwezi kuongea", "siwezi kuzungumza",
)
_DIFFICULTY = (
    "difficulty breathing", "shortness of breath", "hard to breathe",
    "trouble breathing", "struggling to breathe", "breathless",
    "napumua kwa shida", "ninapumua kwa shida", "kupumua kwa shida",
    "shida ya kupumua", "kifua kinabana", "kifua kubana",
)
_AT_REST = (
    "at rest", "even at rest", "when resting", "while resting",
    "wakati ninapumzika", "bila kufanya kazi", "nimekaa tu",
)
_EXERTION = (
    "on exertion", "when i walk", "when walking", "when climbing",
    "when working", "when exercising", "nikitembea", "nikifanya kazi",
)
_CAN_SPEAK = ("can speak a full sentence", "can speak normally", "can talk normally")

def classify_breathing_tier(text):
    """Return 'emergency', 'urgent', or None for free text."""
    t = _norm(text)
    if any(p in t for p in _NEGATIVES):
        return None
    if any(p in t for p in _EMERGENCY):
        return "emergency"
    if any(p in t for p in _DIFFICULTY):
        if any(p in t for p in _AT_REST):
            return "emergency"
        return "urgent"
    return None

def classify_breathing_with_check(text, at_rest=None, can_speak_full_sentence=None):
    """Apply the one severity check to a difficulty-breathing report.

    at_rest=True or can_speak_full_sentence=False -> emergency.
    at_rest=False and can_speak_full_sentence=True -> urgent.
    Otherwise -> 'needs_severity_check'.
    """
    tier = classify_breathing_tier(text)
    if tier == "emergency":
        return "emergency"
    if tier is None:
        return None
    if at_rest is True or can_speak_full_sentence is False:
        return "emergency"
    if at_rest is False and can_speak_full_sentence is True:
        return "urgent"
    return "needs_severity_check"
