"""
RiskGuard Pro — FastAPI Backend (Fixed)
Uses model_config.json for threshold, top features, and 4-level risk scoring.
"""

import os
import json
import uuid
import pickle
import numpy as np
import pandas as pd
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import io

# ─── App Setup ───────────────────────────────────────────────────
app = FastAPI(title="RiskGuard Pro API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Globals ─────────────────────────────────────────────────────
MODEL_DIR = os.path.join(os.path.dirname(__file__), "model")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "analyses.db")

model = None
config = None


# ─── Models ──────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    company_name: str
    sector: Optional[str] = "Autre"
    size: Optional[str] = "PME"
    features: dict


# ─── Database ────────────────────────────────────────────────────
def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            company_name TEXT,
            sector TEXT,
            size TEXT,
            probability REAL,
            risk_label TEXT,
            risk_color TEXT,
            features TEXT,
            recommendations TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


# ─── Startup ─────────────────────────────────────────────────────
@app.on_event("startup")
def load_model():
    global model, config

    model_path = os.path.join(MODEL_DIR, "xgboost_model.pkl")
    config_path = os.path.join(MODEL_DIR, "model_config.json")

    if os.path.exists(model_path):
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        print("✅ Model loaded")

    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        print(f"✅ Config loaded (threshold={config['threshold']}, {len(config['top_features'])} features)")

    get_db()


# ─── Helpers ─────────────────────────────────────────────────────
def get_risk_label(proba, threshold):
    """4-level risk from probability."""
    if proba >= 0.70:
        return "Très élevé", "red"
    elif proba >= 0.40:
        return "Élevé", "orange"
    elif proba >= 0.15:
        return "Modéré", "yellow"
    else:
        return "Faible", "green"


def generate_recommendations(label, features_dict):
    recs = []
    if label in ("Très élevé", "Élevé"):
        recs.append("Réduire le ratio d'endettement en restructurant la dette à long terme.")
        recs.append("Améliorer le fonds de roulement par une meilleure gestion des créances.")
        recs.append("Surveiller de près les indicateurs de trésorerie opérationnelle.")
    if label in ("Modéré", "Élevé", "Très élevé"):
        recs.append("Optimiser la rotation des stocks pour libérer de la trésorerie.")
        recs.append("Diversifier les sources de revenus pour réduire la dépendance sectorielle.")
    recs.append("Maintenir un ratio de liquidité supérieur à 1.5 pour assurer la solvabilité.")
    return recs[:5]


def predict_single(features_dict):
    """Run prediction - pass all features to model in correct order."""
    threshold = config['threshold']
    all_features = config['all_feature_names']
    medians = config['feature_medians']

    # Build input with ALL features in training order
    # User-provided values take priority, medians fill the rest
    X_input = np.array([[
        float(features_dict.get(f, medians.get(f, 0))) for f in all_features
    ]])

    proba = float(model.predict_proba(X_input)[0][1])
    label, color = get_risk_label(proba, threshold)
    recommendations = generate_recommendations(label, features_dict)

    return {
        "probability": round(proba * 100, 1),
        "risk_label": label,
        "color": color,
        "threshold_used": threshold
    , "recommendations": recommendations}


# ─── Routes ──────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": model is not None,
        "training_date": config.get("training_date") if config else None
    }


@app.get("/api/model/features")
def get_features():
    if not config:
        raise HTTPException(404, "Model not trained yet")
    return {
        "features": config["top_features"],
        "count": len(config["top_features"]),
        "defaults": config.get("feature_medians", {})
    }


@app.get("/api/model/metrics")
def get_metrics():
    if not config:
        raise HTTPException(404, "Model not trained yet")
    return {
        **config["metrics"],
        "feature_importance": config.get("feature_importance", []),
        "training_date": config["training_date"],
        "dataset_shape": config["dataset_shape"],
        "n_features": len(config["top_features"]),
        "threshold": config["threshold"],
        "confusion_matrix": config.get("confusion_matrix", [])
    }


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not model or not config:
        raise HTTPException(503, "Model not loaded")

    result = predict_single(req.features)

    # Save to DB
    analysis_id = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        """INSERT INTO analyses (id, company_name, sector, size, probability, risk_label, risk_color, features, recommendations, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (analysis_id, req.company_name, req.sector, req.size,
         result["probability"], result["risk_label"], result["color"],
         json.dumps(req.features), json.dumps(result["recommendations"]),
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

    result["analysis_id"] = analysis_id
    result["company_name"] = req.company_name
    return result


@app.post("/api/analyze/batch")
async def analyze_batch(file: UploadFile = File(...)):
    if not model or not config:
        raise HTTPException(503, "Model not loaded")

    content = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(content))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(400, "Format non supporté. Utilisez CSV ou XLSX.")

    results = []
    summary = {"total": len(df), "Faible": 0, "Modéré": 0, "Élevé": 0, "Très élevé": 0}

    for idx, row in df.iterrows():
        features = row.to_dict()
        company_name = features.pop("company_name", features.pop("Entreprise", f"Entreprise_{idx+1}"))
        result = predict_single(features)
        result["company_name"] = str(company_name)
        results.append(result)
        summary[result["risk_label"]] = summary.get(result["risk_label"], 0) + 1

    return {"results": results, "summary": summary}


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    risk_label: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_db()
    where = []
    params = []
    if risk_label:
        where.append("risk_label = ?")
        params.append(risk_label)
    if search:
        where.append("company_name LIKE ?")
        params.append(f"%{search}%")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""
    total = conn.execute(f"SELECT COUNT(*) FROM analyses {where_clause}", params).fetchone()[0]

    offset = (page - 1) * per_page
    rows = conn.execute(
        f"SELECT * FROM analyses {where_clause} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        params + [per_page, offset]
    ).fetchall()

    data = []
    for row in rows:
        data.append({
            "id": row["id"],
            "company_name": row["company_name"],
            "sector": row["sector"],
            "size": row["size"],
            "probability": row["probability"],
            "risk_label": row["risk_label"],
            "color": row["risk_color"],
            "created_at": row["created_at"]
        })

    conn.close()
    return {"data": data, "total": total, "page": page, "pages": max(1, (total + per_page - 1) // per_page)}


@app.get("/api/history/{analysis_id}")
def get_analysis(analysis_id: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "Analyse non trouvée")
    return {
        "id": row["id"],
        "company_name": row["company_name"],
        "sector": row["sector"],
        "probability": row["probability"],
        "risk_label": row["risk_label"],
        "color": row["risk_color"],
        "features": json.loads(row["features"]),
        "recommendations": json.loads(row["recommendations"]),
        "created_at": row["created_at"]
    }


@app.delete("/api/history/{analysis_id}")
def delete_analysis(analysis_id: str):
    conn = get_db()
    conn.execute("DELETE FROM analyses WHERE id = ?", (analysis_id,))
    conn.commit()
    conn.close()
    return {"success": True}


@app.delete("/api/history")
def delete_all_history():
    conn = get_db()
    conn.execute("DELETE FROM analyses")
    conn.commit()
    conn.close()
    return {"success": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
