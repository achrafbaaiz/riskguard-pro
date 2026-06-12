"""
RiskGuard Pro - Inference Test Script
Loads saved model, scaler, and feature list. Tests with real bankrupt + healthy samples.
"""

import json
import pickle
import numpy as np
import pandas as pd
import os

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend", "model")
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_1.csv")


def load_artifacts():
    with open(os.path.join(MODEL_DIR, "xgboost_model.pkl"), 'rb') as f:
        model = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "scaler.pkl"), 'rb') as f:
        scaler = pickle.load(f)
    with open(os.path.join(MODEL_DIR, "feature_names.json"), 'r') as f:
        feature_names = json.load(f)
    with open(os.path.join(MODEL_DIR, "model_config.json"), 'r') as f:
        config = json.load(f)
    return model, scaler, feature_names, config


def predict(model, scaler, feature_names, input_dict):
    """Apply saved preprocessing and predict."""
    # Build feature vector in correct order, fill missing with 0
    values = [float(input_dict.get(f, 0)) for f in feature_names]
    X = pd.DataFrame([values], columns=feature_names)

    # Apply scaler only if model was trained with it
    if config.get('uses_scaler', True):
        X_scaled = scaler.transform(X)
    else:
        X_scaled = X.values

    # Predict
    proba = float(model.predict_proba(X_scaled)[0][1])
    pred_class = int(proba >= config['threshold'])
    return pred_class, proba


if __name__ == "__main__":
    model, scaler, feature_names, config = load_artifacts()

    print("=" * 60)
    print("  RiskGuard Pro - Inference Test")
    print(f"  Model threshold: {config['threshold']:.2f}")
    print(f"  Features: {len(feature_names)}")
    print("=" * 60)

    # Load real data to get actual examples
    df = pd.read_csv(DATA_PATH)
    df.columns = df.columns.str.strip()

    # Drop Net Income Flag if present
    if 'Net Income Flag' in df.columns:
        df = df.drop(columns=['Net Income Flag'])

    # Cap outliers same as training
    outlier_caps = config.get('outlier_caps', {})
    for col, cap in outlier_caps.items():
        if col in df.columns:
            df[col] = df[col].clip(upper=cap)

    df = df.replace([np.inf, -np.inf], np.nan).fillna(df.median(numeric_only=True))

    # Example 1: Real bankrupt company (label=1)
    bankrupt_rows = df[df['Bankrupt?'] == 1]
    bankrupt_sample = bankrupt_rows.iloc[0].drop('Bankrupt?').to_dict()

    print("\n--- Example 1: Real BANKRUPT company (row 0 of bankrupt set) ---")
    pred_class, proba = predict(model, scaler, feature_names, bankrupt_sample)
    print(f"  Predicted class: {pred_class} ({'Bankrupt' if pred_class == 1 else 'Not Bankrupt'})")
    print(f"  Predicted probability: {proba*100:.1f}%")
    print(f"  Expected: Bankrupt (class 1)")
    print(f"  {'CORRECT' if pred_class == 1 else 'WRONG'}")

    # Example 2: Real healthy company (label=0)
    safe_rows = df[df['Bankrupt?'] == 0]
    safe_sample = safe_rows.iloc[50].drop('Bankrupt?').to_dict()

    print("\n--- Example 2: Real HEALTHY company (row 50 of safe set) ---")
    pred_class, proba = predict(model, scaler, feature_names, safe_sample)
    print(f"  Predicted class: {pred_class} ({'Bankrupt' if pred_class == 1 else 'Not Bankrupt'})")
    print(f"  Predicted probability: {proba*100:.1f}%")
    print(f"  Expected: Not Bankrupt (class 0)")
    print(f"  {'CORRECT' if pred_class == 0 else 'WRONG'}")

    # Example 3: Another bankrupt company
    bankrupt_sample2 = bankrupt_rows.iloc[5].drop('Bankrupt?').to_dict()

    print("\n--- Example 3: Real BANKRUPT company (row 5 of bankrupt set) ---")
    pred_class, proba = predict(model, scaler, feature_names, bankrupt_sample2)
    print(f"  Predicted class: {pred_class} ({'Bankrupt' if pred_class == 1 else 'Not Bankrupt'})")
    print(f"  Predicted probability: {proba*100:.1f}%")
    print(f"  Expected: Bankrupt (class 1)")
    print(f"  {'CORRECT' if pred_class == 1 else 'WRONG'}")

    # Example 4: Another healthy company
    safe_sample2 = safe_rows.iloc[100].drop('Bankrupt?').to_dict()

    print("\n--- Example 4: Real HEALTHY company (row 100 of safe set) ---")
    pred_class, proba = predict(model, scaler, feature_names, safe_sample2)
    print(f"  Predicted class: {pred_class} ({'Bankrupt' if pred_class == 1 else 'Not Bankrupt'})")
    print(f"  Predicted probability: {proba*100:.1f}%")
    print(f"  Expected: Not Bankrupt (class 0)")
    print(f"  {'CORRECT' if pred_class == 0 else 'WRONG'}")

    print("\n" + "=" * 60)
