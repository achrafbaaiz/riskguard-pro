"""Feature engineering utilities."""


def get_feature_groups(feature_names):
    """Group features by category for better UI display."""
    groups = {
        "Rentabilité": [],
        "Liquidité": [],
        "Endettement": [],
        "Activité": [],
        "Croissance": [],
        "Autres": []
    }
    
    keywords = {
        "Rentabilité": ["ROA", "profit", "income", "margin", "EPS", "return"],
        "Liquidité": ["current ratio", "quick", "cash", "working capital"],
        "Endettement": ["debt", "liability", "borrowing", "leverage", "interest"],
        "Activité": ["turnover", "collection", "inventory", "revenue per"],
        "Croissance": ["growth", "growth rate"],
    }
    
    for feat in feature_names:
        placed = False
        for group, kws in keywords.items():
            if any(kw.lower() in feat.lower() for kw in kws):
                groups[group].append(feat)
                placed = True
                break
        if not placed:
            groups["Autres"].append(feat)
    
    return {k: v for k, v in groups.items() if v}
