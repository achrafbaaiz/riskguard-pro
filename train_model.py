"""
RiskGuard Pro - Training Pipeline
Trains XGBoost on data_1.csv for bankruptcy risk prediction.
Binary classification (bankrupt/not bankrupt) with probability-based risk scoring.
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
import joblib
import optuna
from datetime import datetime
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, confusion_matrix, classification_report
)
from xgboost import XGBClassifier

warnings.filterwarnings('ignore')
optuna.logging.set_verbosity(optuna.logging.WARNING)

# --- Config ---
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "model")
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_1.csv")
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "data", "raw", "data_1.csv")

RISK_LABELS = ["Faible", "Modere", "Eleve", "Critique"]
RANDOM_STATE = 42


def load_data():
    print("=" * 60)
    print("  RiskGuard Pro - Training Pipeline")
    print("=" * 60)
    
    df = pd.read_csv(DATA_PATH)
    print(f"\n[DATA] Loaded: {DATA_PATH}")
    print(f"   Shape: {df.shape[0]} rows x {df.shape[1]} columns")
    print(f"   Target: 'Bankrupt?' -> {df['Bankrupt?'].value_counts().to_dict()}")
    print(f"   Missing: {df.isnull().sum().sum()}")
    return df


def build_preprocessor(X):
    numeric_cols = X.select_dtypes(include=[np.number]).columns.tolist()
    preprocessor = ColumnTransformer([
        ('num', Pipeline([
            ('imputer', SimpleImputer(strategy='median')),
            ('scaler', StandardScaler())
        ]), numeric_cols)
    ], remainder='drop')
    return preprocessor, numeric_cols


def objective(trial, X_train, y_train, preprocessor):
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 500),
        'max_depth': trial.suggest_int('max_depth', 3, 8),
        'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.2, log=True),
        'subsample': trial.suggest_float('subsample', 0.6, 1.0),
        'colsample_bytree': trial.suggest_float('colsample_bytree', 0.6, 1.0),
        'min_child_weight': trial.suggest_int('min_child_weight', 1, 10),
        'gamma': trial.suggest_float('gamma', 0, 5),
        'reg_alpha': trial.suggest_float('reg_alpha', 1e-8, 10, log=True),
        'reg_lambda': trial.suggest_float('reg_lambda', 1e-8, 10, log=True),
        'scale_pos_weight': trial.suggest_float('scale_pos_weight', 10, 40),
    }
    
    model = XGBClassifier(
        **params,
        objective='binary:logistic',
        eval_metric='auc',
        use_label_encoder=False,
        random_state=RANDOM_STATE,
        verbosity=0
    )
    
    pipe = Pipeline([('preprocessor', preprocessor), ('classifier', model)])
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring='roc_auc')
    return scores.mean()


def train():
    df = load_data()
    
    y = df['Bankrupt?'].values
    X = df.drop(columns=['Bankrupt?'])
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\n[SPLIT] Train: {len(X_train)} | Test: {len(X_test)}")
    print(f"   Train pos rate: {y_train.mean():.3f} | Test pos rate: {y_test.mean():.3f}")
    
    preprocessor, feature_names = build_preprocessor(X_train)
    
    # Optuna tuning (15 trials for speed)
    print(f"\n[OPTUNA] Hyperparameter tuning (15 trials)...")
    study = optuna.create_study(direction='maximize')
    study.optimize(
        lambda trial: objective(trial, X_train, y_train, preprocessor),
        n_trials=15, show_progress_bar=True
    )
    
    best_params = study.best_params
    print(f"   Best AUC (CV): {study.best_value:.4f}")
    
    # Train final model
    print(f"\n[TRAIN] Training final model...")
    final_model = XGBClassifier(
        **best_params,
        objective='binary:logistic',
        eval_metric='auc',
        use_label_encoder=False,
        random_state=RANDOM_STATE,
        verbosity=0
    )
    
    pipeline = Pipeline([('preprocessor', preprocessor), ('classifier', final_model)])
    pipeline.fit(X_train, y_train)
    
    # Evaluate
    y_pred = pipeline.predict(X_test)
    y_proba = pipeline.predict_proba(X_test)[:, 1]  # P(bankrupt)
    
    accuracy = accuracy_score(y_test, y_pred)
    precision = precision_score(y_test, y_pred, zero_division=0)
    recall = recall_score(y_test, y_pred, zero_division=0)
    f1 = f1_score(y_test, y_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_proba)
    cm = confusion_matrix(y_test, y_pred).tolist()
    
    # Convert to 4-class for display (based on probability thresholds)
    # P(default) -> risk class: <0.15=Faible, 0.15-0.40=Modere, 0.40-0.70=Eleve, >0.70=Critique
    risk_classes_pred = np.digitize(y_proba, bins=[0.15, 0.40, 0.70])
    risk_classes_true = np.digitize(y_test.astype(float), bins=[0.15, 0.40, 0.70])
    cm4 = confusion_matrix(risk_classes_true, risk_classes_pred, labels=[0,1,2,3]).tolist()
    
    # Feature importance
    xgb_model = pipeline.named_steps['classifier']
    importance = xgb_model.feature_importances_
    feat_importance = sorted(
        zip(feature_names, importance.tolist()),
        key=lambda x: x[1], reverse=True
    )[:20]
    
    print(f"\n{'='*60}")
    print(f"  EVALUATION RESULTS")
    print(f"{'='*60}")
    print(f"   Accuracy:  {accuracy:.4f}")
    print(f"   Precision: {precision:.4f}")
    print(f"   Recall:    {recall:.4f}")
    print(f"   F1-Score:  {f1:.4f}")
    print(f"   AUC-ROC:   {auc:.4f}")
    print(f"\n   Confusion Matrix (binary):")
    for row in cm:
        print(f"   {row}")
    print(f"\n   Top 10 Features:")
    for name, imp in feat_importance[:10]:
        print(f"   {imp:.4f} - {name}")
    
    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "xgboost_pipeline.pkl")
    joblib.dump(pipeline, model_path)
    print(f"\n[SAVED] Model: {model_path}")
    
    # Save metadata
    metadata = {
        "training_date": datetime.now().isoformat(),
        "dataset_shape": list(df.shape),
        "n_features": len(feature_names),
        "feature_names": feature_names,
        "risk_labels": RISK_LABELS,
        "model_type": "binary_classification",
        "risk_thresholds": [0.15, 0.40, 0.70],
        "feature_medians": X_train.median().to_dict(),
        "metrics": {
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "auc_roc": round(auc, 4),
            "confusion_matrix": cm,
            "confusion_matrix_4class": cm4
        },
        "feature_importance": [{"feature": n, "importance": round(v, 6)} for n, v in feat_importance],
        "best_params": best_params
    }
    
    meta_path = os.path.join(MODEL_DIR, "model_metadata.json")
    with open(meta_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    print(f"[SAVED] Metadata: {meta_path}")
    
    print(f"\n[DONE] Training complete!")
    print(f"   cd backend && uvicorn main:app --reload --port 8000")
    print(f"{'='*60}")


if __name__ == "__main__":
    train()
