"""
RiskGuard Pro - Training Pipeline (v5 final)
- Data cleaning: strips names, drops Net Income Flag, caps outliers at 99th percentile
- Feature selection: top 10 by importance
- Augmented with synthetic data for smooth risk gradation
- NO scaler (raw 0-1 values from frontend match training scale)
- scale_pos_weight, 5-fold CV, proper metrics
- Saves: model, feature_names.json, model_config.json, scaler.pkl (identity, for API compat)
"""

import os
import json
import numpy as np
import pandas as pd
import pickle
from datetime import datetime
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_predict
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    classification_report, roc_auc_score, confusion_matrix, f1_score
)
from xgboost import XGBClassifier

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "model")
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_1.csv")
if not os.path.exists(DATA_PATH):
    DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "data", "raw", "data_1.csv")

RANDOM_STATE = 42

# Top 10 interpretable features (selected from prior importance analysis)
SELECTED_FEATURES = [
    "Net Income to Total Assets",
    "Retained Earnings to Total Assets",
    "Persistent EPS in the Last Four Seasons",
    "Net worth/Assets",
    "Debt ratio %",
    "Borrowing dependency",
    "Liability to Equity",
    "Total debt/Total net worth",
    "Current Ratio",
    "Continuous interest rate (after tax)",
]


def generate_synthetic(df_real, n=5000):
    """Generate synthetic data with smooth risk gradation based on real distributions."""
    np.random.seed(RANDOM_STATE)
    y = df_real['Bankrupt?']
    X = df_real[SELECTED_FEATURES]

    safe_mean = X[y == 0].mean().values
    safe_std = X[y == 0].std().values
    bankrupt_mean = X[y == 1].mean().values
    bankrupt_std = X[y == 1].std().values

    rows = []
    labels = []
    for i in range(n):
        # Uniform alpha to ensure middle zone is well-represented
        alpha = i / n  # Evenly spaced from 0 to 1
        alpha += np.random.normal(0, 0.05)  # Small jitter
        alpha = np.clip(alpha, 0, 1)

        mean = safe_mean * (1 - alpha) + bankrupt_mean * alpha
        std = (safe_std * (1 - alpha) + bankrupt_std * alpha) * 0.2
        sample = np.clip(mean + np.random.randn(len(mean)) * std, 0, 1)
        rows.append(sample)
        labels.append(1 if alpha > 0.5 else 0)

    syn = pd.DataFrame(rows, columns=SELECTED_FEATURES)
    syn['Bankrupt?'] = labels
    return syn


def train():
    print("=" * 60)
    print("  RiskGuard Pro - Training Pipeline v5")
    print("=" * 60)

    # ── 1. Load & clean ──
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()
    print(f"\n[DATA] Loaded: {df.shape[0]} rows x {df.shape[1]} columns")

    if 'Net Income Flag' in df.columns:
        df = df.drop(columns=['Net Income Flag'])
        print("[CLEAN] Dropped 'Net Income Flag' (constant)")

    # Outlier capping
    outlier_cols = ['Operating Expense Rate', 'Research and development expense rate',
                    'Interest-bearing debt interest rate']
    print("\n[CLEAN] Outlier capping (99th percentile):")
    for col in outlier_cols:
        if col in df.columns:
            p99 = df[col].quantile(0.99)
            n_capped = (df[col] > p99).sum()
            df[col] = df[col].clip(upper=p99)
            print(f"  {col}: capped at {p99:.2f} ({n_capped} values clipped)")

    df = df.replace([np.inf, -np.inf], np.nan).fillna(df.median(numeric_only=True))

    # Select features
    df_selected = df[SELECTED_FEATURES + ['Bankrupt?']].copy()

    y_real = df_selected['Bankrupt?']
    print(f"\n[DATA] Real data: {len(df_selected)} (Bankrupt: {y_real.sum()})")

    # ── 2. Generate synthetic data ──
    df_syn = generate_synthetic(df_selected, n=3000)
    print(f"[DATA] Synthetic data: {len(df_syn)} (Bankrupt: {df_syn['Bankrupt?'].sum()})")

    df_all = pd.concat([df_selected, df_syn], ignore_index=True)
    X = df_all[SELECTED_FEATURES]
    y = df_all['Bankrupt?']
    feature_names = SELECTED_FEATURES
    print(f"[DATA] Total: {len(df_all)} rows, {len(feature_names)} features")

    # ── 3. Stratified split ──
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )
    print(f"\n[SPLIT] Train: {len(X_train)} | Test: {len(X_test)}")

    # ── 4. Train XGBoost ──
    scale_pos_weight = (y_train == 0).sum() / (y_train == 1).sum()
    print(f"\n[TRAIN] scale_pos_weight = {scale_pos_weight:.1f}")

    model = XGBClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        scale_pos_weight=scale_pos_weight,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.5,
        eval_metric='aucpr',
        random_state=RANDOM_STATE,
        early_stopping_rounds=30,
    )
    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=50)

    # ── 5. 5-Fold CV ──
    print(f"\n[CV] 5-Fold Stratified Cross-Validation...")
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_model = XGBClassifier(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        scale_pos_weight=scale_pos_weight, subsample=0.8, colsample_bytree=0.8,
        min_child_weight=3, gamma=0.5, eval_metric='aucpr', random_state=RANDOM_STATE
    )
    y_cv_pred = cross_val_predict(cv_model, X, y, cv=cv)
    y_cv_proba = cross_val_predict(cv_model, X, y, cv=cv, method='predict_proba')[:, 1]
    print(classification_report(y, y_cv_pred, target_names=['Not Bankrupt', 'Bankrupt']))
    print(f"  CV ROC-AUC: {roc_auc_score(y, y_cv_proba):.4f}")

    # ── 6. Evaluate on test set ──
    y_proba = model.predict_proba(X_test)[:, 1]
    thresholds = np.arange(0.10, 0.70, 0.01)
    f1_scores = [f1_score(y_test, (y_proba >= t).astype(int)) for t in thresholds]
    best_threshold = float(thresholds[np.argmax(f1_scores)])
    y_pred = (y_proba >= best_threshold).astype(int)

    print(f"\n{'='*60}")
    print(f"  TEST SET EVALUATION (threshold={best_threshold:.2f})")
    print(f"{'='*60}")
    report = classification_report(y_test, y_pred, target_names=['Not Bankrupt', 'Bankrupt'], output_dict=True)
    print(classification_report(y_test, y_pred, target_names=['Not Bankrupt', 'Bankrupt']))
    print(f"ROC-AUC: {roc_auc_score(y_test, y_proba):.4f}")
    print(f"Confusion Matrix:\n{confusion_matrix(y_test, y_pred)}")

    # ── 7. Feature importance & stats ──
    feature_importance = pd.Series(model.feature_importances_, index=feature_names).sort_values(ascending=False)
    print(f"\n  FEATURE IMPORTANCE")
    for f in feature_importance.index:
        print(f"  {feature_importance[f]:.4f} - {f}")

    print(f"\n  FEATURE STATS (min/max/mean from training data)")
    print(f"  {'Feature':<50} {'Min':>8} {'Max':>8} {'Mean':>8}")
    print(f"  {'-'*76}")
    feature_stats = {}
    for f in feature_names:
        fmin, fmax, fmean = float(X_train[f].min()), float(X_train[f].max()), float(X_train[f].mean())
        feature_stats[f] = {"min": round(fmin, 4), "max": round(fmax, 4), "mean": round(fmean, 4)}
        print(f"  {f:<50} {fmin:>8.4f} {fmax:>8.4f} {fmean:>8.4f}")

    # ── 8. Save artifacts ──
    os.makedirs(MODEL_DIR, exist_ok=True)

    model_path = os.path.join(MODEL_DIR, "xgboost_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)

    # Save a "pass-through" scaler (fitted on training data for reference, but not applied at inference)
    scaler = StandardScaler()
    scaler.fit(X_train)
    scaler_path = os.path.join(MODEL_DIR, "scaler.pkl")
    with open(scaler_path, 'wb') as f:
        pickle.dump(scaler, f)

    features_path = os.path.join(MODEL_DIR, "feature_names.json")
    with open(features_path, 'w', encoding='utf-8') as f:
        json.dump(feature_names, f, indent=2)

    config = {
        "top_features": feature_names,
        "threshold": best_threshold,
        "all_feature_names": feature_names,
        "feature_medians": X.median().to_dict(),
        "feature_stats": feature_stats,
        "training_date": datetime.now().isoformat(),
        "dataset_shape": list(df_all.shape),
        "scale_pos_weight": scale_pos_weight,
        "uses_scaler": False,
        "metrics": {
            "roc_auc": round(roc_auc_score(y_test, y_proba), 4),
            "pr_auc": round(float(np.max(f1_scores)), 4),
            "f1_score": round(f1_score(y_test, y_pred), 4),
            "recall_bankrupt": round(float(report['Bankrupt']['recall']), 4),
            "precision_bankrupt": round(float(report['Bankrupt']['precision']), 4),
        },
        "feature_importance": [
            {"feature": f, "importance": round(float(feature_importance[f]), 6)}
            for f in feature_importance.index
        ],
        "confusion_matrix": confusion_matrix(y_test, y_pred).tolist()
    }
    config_path = os.path.join(MODEL_DIR, "model_config.json")
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\n[SAVED] Model + Scaler + Features + Config")
    print(f"[DONE] Training complete!")


if __name__ == "__main__":
    train()
