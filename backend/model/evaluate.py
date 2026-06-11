"""Model evaluation metrics utilities."""
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix
)


def compute_all_metrics(y_true, y_pred, y_proba):
    """Compute all evaluation metrics."""
    return {
        "accuracy": round(accuracy_score(y_true, y_pred), 4),
        "precision": round(precision_score(y_true, y_pred, average='macro', zero_division=0), 4),
        "recall": round(recall_score(y_true, y_pred, average='macro', zero_division=0), 4),
        "f1_score": round(f1_score(y_true, y_pred, average='macro', zero_division=0), 4),
        "auc_roc": round(roc_auc_score(y_true, y_proba, multi_class='ovr', average='macro'), 4),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist()
    }
