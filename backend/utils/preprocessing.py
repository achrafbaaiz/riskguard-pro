"""Data preprocessing helpers."""
import pandas as pd
import numpy as np


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Clean input dataframe: handle missing values, fix dtypes."""
    # Convert columns that should be numeric
    for col in df.columns:
        if df[col].dtype == object:
            try:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            except Exception:
                pass
    
    # Fill numeric missing with median
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].median())
    
    return df


def validate_features(features: dict, expected: list) -> dict:
    """Ensure all expected features are present, fill missing with 0."""
    cleaned = {}
    for feat in expected:
        val = features.get(feat, 0)
        try:
            cleaned[feat] = float(val)
        except (ValueError, TypeError):
            cleaned[feat] = 0.0
    return cleaned
