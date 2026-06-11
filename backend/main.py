"""
RiskGuard Pro — FastAPI Backend
Banking Risk Detection API with XGBoost predictions, SHAP explanations, and history.
"""

import os
import json
import uuid
import joblib
import numpy as np
import pandas as pd
try:
    import shap
    HAS_SHAP = True
except ImportError:
    HAS_SHAP = False
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import sqlite3
import io

# ─── App Setup ───────────────────────────────────────────────────
app = FastAPI(title="RiskGuard Pro API", version="1.0.0")

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
RISK_LABELS = ["Faible", "Modéré", "Élevé", "Critique"]

pipeline = None
metadata = None
explainer = None


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
            risk_score REAL,
            risk_class INTEGER,
            probabilities TEXT,
            features TEXT,
            shap_values TEXT,
            recommendations TEXT,
            created_at TEXT
        )
    """)
    conn.commit()
    return conn


# ─── Startup ─────────────────────────────────────────────────────
@app.on_event("startup")
def load_model():
    global pipeline, metadata, explainer
    
    model_path = os.path.join(MODEL_DIR, "xgboost_pipeline.pkl")
    meta_path = os.path.join(MODEL_DIR, "model_metadata.json")
    
    if os.path.exists(model_path):
        pipeline = joblib.load(model_path)
        print("✅ Model loaded")
    
    if os.path.exists(meta_path):
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        print("✅ Metadata loaded")
    
    # Initialize SHAP explainer (optional)
    if pipeline and HAS_SHAP:
        try:
            xgb_model = pipeline.named_steps['classifier']
            explainer = shap.TreeExplainer(xgb_model)
        except Exception as e:
            print(f"SHAP init warning: {e}")
    
    get_db()


# ─── Helpers ─────────────────────────────────────────────────────
def compute_risk_score(prob_default):
    """Convert P(default) to 0-100 risk score."""
    # Scale more reasonably: most companies have low P(default)
    # Use log-scale mapping for better spread
    import math
    if prob_default < 0.01:
        return prob_default * 500  # 0-5 range
    elif prob_default < 0.05:
        return 5 + (prob_default - 0.01) * 500  # 5-25 range
    elif prob_default < 0.15:
        return 25 + (prob_default - 0.05) * 250  # 25-50 range
    elif prob_default < 0.40:
        return 50 + (prob_default - 0.15) * 100  # 50-75 range
    else:
        return min(100, 75 + (prob_default - 0.40) * 42)  # 75-100 range


def prob_to_risk_class(risk_score):
    """Convert risk score (0-100) to 4-class risk level."""
    if risk_score < 25:
        return 0
    elif risk_score < 50:
        return 1
    elif risk_score < 75:
        return 2
    return 3


def generate_recommendations(risk_class, shap_top):
    """Generate financial recommendations based on risk factors."""
    recs = []
    if risk_class >= 2:
        recs.append("Reduire le ratio d'endettement en restructurant la dette a long terme.")
        recs.append("Ameliorer le fonds de roulement par une meilleure gestion des creances.")
    if risk_class >= 1:
        recs.append("Optimiser la rotation des stocks pour liberer de la tresorerie.")
        recs.append("Diversifier les sources de revenus pour reduire la dependance sectorielle.")
    recs.append("Maintenir un ratio de liquidite superieur a 1.5 pour assurer la solvabilite.")
    
    for item in shap_top[:3]:
        feat = item["feature"]
        if "debt" in feat.lower() or "liability" in feat.lower():
            recs.append(f"Surveiller l'indicateur '{feat}' - impact significatif sur le risque.")
        elif "profit" in feat.lower() or "income" in feat.lower():
            recs.append(f"Renforcer la rentabilite mesuree par '{feat}'.")
    
    return recs[:5]


def predict_single(features_dict):
    """Run prediction for a single company."""
    feature_names = metadata["feature_names"]
    
    input_data = {}
    for col in feature_names:
        input_data[col] = [float(features_dict.get(col, 0))]
    
    df = pd.DataFrame(input_data)
    
    # Binary prediction - get P(default)
    prob_default = float(pipeline.predict_proba(df)[0][1])
    risk_score = compute_risk_score(prob_default)
    risk_class = prob_to_risk_class(risk_score)
    
    # Build 4-class probabilities from the default probability
    # Distribute across 4 risk levels based on where prob_default falls
    probs_4class = [0.0, 0.0, 0.0, 0.0]
    probs_4class[risk_class] = 0.6
    for i in range(4):
        if i != risk_class:
            probs_4class[i] = 0.4 / 3
    # More nuanced: scale by proximity
    probs_4class = [max(0, 1 - abs(prob_default - t)) for t in [0.05, 0.25, 0.55, 0.85]]
    total = sum(probs_4class)
    probs_4class = [p/total for p in probs_4class] if total > 0 else [0.25]*4
    
    # SHAP or fallback to XGBoost feature importance
    shap_values_list = []
    if explainer:
        try:
            preprocessed = pipeline.named_steps['preprocessor'].transform(df)
            sv = explainer.shap_values(preprocessed)
            if isinstance(sv, list):
                sv_arr = sv[1][0] if len(sv) > 1 else sv[0][0]
            elif sv.ndim == 3:
                sv_arr = sv[0, :, 1]
            else:
                sv_arr = sv[0]
            
            for i, feat in enumerate(feature_names):
                if i < len(sv_arr):
                    shap_values_list.append({
                        "feature": feat,
                        "value": float(df[feat].iloc[0]),
                        "impact": float(sv_arr[i])
                    })
            shap_values_list.sort(key=lambda x: abs(x["impact"]), reverse=True)
            shap_values_list = shap_values_list[:15]
        except Exception:
            pass
    
    # Fallback: use XGBoost feature importance if SHAP failed
    if not shap_values_list:
        xgb_model = pipeline.named_steps['classifier']
        importances = xgb_model.feature_importances_
        for i, feat in enumerate(feature_names):
            if i < len(importances):
                shap_values_list.append({
                    "feature": feat,
                    "value": float(df[feat].iloc[0]),
                    "impact": float(importances[i]) * (1 if df[feat].iloc[0] > 0.5 else -1)
                })
        shap_values_list.sort(key=lambda x: abs(x["impact"]), reverse=True)
        shap_values_list = shap_values_list[:15]
    
    recommendations = generate_recommendations(risk_class, shap_values_list)
    
    return {
        "risk_score": round(risk_score, 2),
        "risk_class": risk_class,
        "risk_label": RISK_LABELS[risk_class],
        "probabilities": [round(p, 4) for p in probs_4class],
        "shap_values": shap_values_list,
        "recommendations": recommendations
    }


# ─── Routes ──────────────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "model_loaded": pipeline is not None,
        "training_date": metadata.get("training_date") if metadata else None
    }


@app.get("/api/model/features")
def get_features():
    if not metadata:
        raise HTTPException(404, "Model not trained yet")
    return {
        "features": metadata["feature_names"],
        "count": metadata["n_features"],
        "defaults": metadata.get("feature_medians", {})
    }


@app.get("/api/model/metrics")
def get_metrics():
    if not metadata:
        raise HTTPException(404, "Model not trained yet")
    return {
        **metadata["metrics"],
        "feature_importance": metadata.get("feature_importance", []),
        "risk_labels": RISK_LABELS,
        "training_date": metadata["training_date"],
        "dataset_shape": metadata["dataset_shape"],
        "n_features": metadata["n_features"]
    }


@app.post("/api/analyze")
def analyze(req: AnalyzeRequest):
    if not pipeline:
        raise HTTPException(503, "Model not loaded")
    
    result = predict_single(req.features)
    
    # Save to DB
    analysis_id = str(uuid.uuid4())[:8]
    conn = get_db()
    conn.execute(
        """INSERT INTO analyses (id, company_name, sector, size, risk_score, risk_class,
           probabilities, features, shap_values, recommendations, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (analysis_id, req.company_name, req.sector, req.size,
         result["risk_score"], result["risk_class"],
         json.dumps(result["probabilities"]),
         json.dumps(req.features),
         json.dumps(result["shap_values"]),
         json.dumps(result["recommendations"]),
         datetime.now().isoformat())
    )
    conn.commit()
    conn.close()
    
    result["analysis_id"] = analysis_id
    result["company_name"] = req.company_name
    return result


@app.post("/api/analyze/batch")
async def analyze_batch(file: UploadFile = File(...)):
    if not pipeline:
        raise HTTPException(503, "Model not loaded")
    
    content = await file.read()
    
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(content))
    elif file.filename.endswith(('.xlsx', '.xls')):
        df = pd.read_excel(io.BytesIO(content))
    else:
        raise HTTPException(400, "Format non supporté. Utilisez CSV ou XLSX.")
    
    results = []
    summary = {"total": len(df), "Faible": 0, "Modéré": 0, "Élevé": 0, "Critique": 0}
    
    for idx, row in df.iterrows():
        features = row.to_dict()
        company_name = features.pop("company_name", features.pop("Entreprise", f"Entreprise_{idx+1}"))
        result = predict_single(features)
        result["company_name"] = str(company_name)
        results.append(result)
        summary[RISK_LABELS[result["risk_class"]]] += 1
    
    return {"results": results, "summary": summary}


@app.get("/api/history")
def get_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    risk_class: Optional[int] = None,
    sector: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_db()
    
    where = []
    params = []
    if risk_class is not None:
        where.append("risk_class = ?")
        params.append(risk_class)
    if sector:
        where.append("sector = ?")
        params.append(sector)
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
            "risk_score": row["risk_score"],
            "risk_class": row["risk_class"],
            "risk_label": RISK_LABELS[row["risk_class"]],
            "probabilities": json.loads(row["probabilities"]),
            "created_at": row["created_at"]
        })
    
    conn.close()
    return {
        "data": data,
        "total": total,
        "page": page,
        "pages": max(1, (total + per_page - 1) // per_page)
    }


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
        "size": row["size"],
        "risk_score": row["risk_score"],
        "risk_class": row["risk_class"],
        "risk_label": RISK_LABELS[row["risk_class"]],
        "probabilities": json.loads(row["probabilities"]),
        "features": json.loads(row["features"]),
        "shap_values": json.loads(row["shap_values"]),
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


@app.get("/api/export/{analysis_id}")
def export_pdf(analysis_id: str):
    """Generate PDF report for an analysis."""
    conn = get_db()
    row = conn.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(404, "Analyse non trouvée")
    
    from utils.report_generator import generate_report
    
    analysis_data = {
        "id": row["id"],
        "company_name": row["company_name"],
        "sector": row["sector"],
        "risk_score": row["risk_score"],
        "risk_class": row["risk_class"],
        "risk_label": RISK_LABELS[row["risk_class"]],
        "probabilities": json.loads(row["probabilities"]),
        "shap_values": json.loads(row["shap_values"]),
        "recommendations": json.loads(row["recommendations"]),
        "created_at": row["created_at"]
    }
    
    pdf_path = generate_report(analysis_data)
    return FileResponse(pdf_path, filename=f"RiskGuard_{row['company_name']}_{row['id']}.pdf")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
