"""Prediction utilities — used by main.py for inference."""
import numpy as np


RISK_LABELS = ["Faible", "Modéré", "Élevé", "Critique"]


def compute_risk_score(probabilities):
    """Convert class probabilities to 0-100 score."""
    weights = np.array([0, 33, 66, 100])
    return float(np.dot(probabilities, weights))


def get_risk_label(risk_class: int) -> str:
    return RISK_LABELS[risk_class]
