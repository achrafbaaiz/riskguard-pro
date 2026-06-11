# 🛡️ RiskGuard Pro

**Plateforme de Détection de Risque Bancaire pour Entreprises**

Une plateforme web complète utilisant XGBoost pour évaluer le profil de risque financier des entreprises. Interface moderne (HTML/CSS/JS pur), API FastAPI, et pipeline ML complet.

---

## 📋 Prérequis

- Python 3.9+
- pip
- Navigateur moderne (Chrome, Firefox, Edge)

---

## 🚀 Installation & Lancement

### 1. Installer les dépendances

```bash
cd riskguard-pro
pip install -r backend/requirements.txt
```

### 2. Entraîner le modèle

```bash
python train_model.py
```

> Ce script lit automatiquement `data_1.csv`, effectue l'exploration des données, entraîne un modèle XGBoost avec optimisation Optuna (30 essais), et sauvegarde le modèle dans `backend/model/`.

### 3. Démarrer le backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 4. Ouvrir le frontend

Ouvrez `frontend/index.html` dans votre navigateur (ou utilisez Live Server dans VS Code).

> **Mode démo** : Si le backend n'est pas lancé, l'interface fonctionne en mode démo avec des données simulées de 15 entreprises marocaines.

---

## 📡 API Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/health` | État du serveur et du modèle |
| GET | `/api/model/features` | Liste des features du modèle |
| GET | `/api/model/metrics` | Métriques de performance (accuracy, F1, AUC...) |
| POST | `/api/analyze` | Analyse de risque d'une entreprise |
| POST | `/api/analyze/batch` | Analyse batch (fichier CSV/XLSX) |
| GET | `/api/history` | Historique des analyses (paginé, filtrable) |
| GET | `/api/export/{id}` | Export PDF d'une analyse |
| DELETE | `/api/history/{id}` | Supprimer une analyse |

---

## 📊 Format du Dataset

Le fichier `data_1.csv` contient :
- **96 colonnes** de ratios financiers (ROA, liquidité, endettement, activité, etc.)
- **1 colonne cible** : `Bankrupt?` (0 = sain, 1 = défaillant)
- Le script d'entraînement crée automatiquement 4 classes de risque : Faible, Modéré, Élevé, Critique

---

## 🔄 Ré-entraînement

Pour ré-entraîner avec de nouvelles données :

1. Placez votre fichier CSV à la racine sous le nom `data_1.csv`
2. Exécutez `python train_model.py`
3. Redémarrez le backend

---

## 🛠️ Dépannage

| Problème | Solution |
|----------|----------|
| "Model not loaded" | Lancez `python train_model.py` d'abord |
| CORS errors | Vérifiez que le backend tourne sur le port 8000 |
| Frontend blanc | Ouvrez la console pour voir les erreurs JS |
| Import SHAP lent | Normal au premier lancement, patience |

---

## 🏗️ Structure

```
riskguard-pro/
├── frontend/          # Interface web (HTML/CSS/JS pur)
├── backend/           # API FastAPI + modèle ML
│   ├── model/         # Pipeline XGBoost sauvegardé
│   ├── utils/         # Préprocessing, validation, PDF
│   └── data/          # Base SQLite + rapports
├── train_model.py     # Script d'entraînement
└── README.md
```

---

**Développé avec ❤️ pour l'analyse de risque bancaire au Maroc**
