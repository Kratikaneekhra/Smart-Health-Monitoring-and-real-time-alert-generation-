"""
Train / retrain the four disease models.

    python ml/train_models.py                 # all four
    python ml/train_models.py diabetes heart  # only some

For each disease this follows the same recipe as your research notebooks:
  clean data -> 80/20 stratified split -> impute + scale + one-hot ->
  Logistic Regression, Decision Tree, Random Forest, XGBoost, ANN ->
  choose the best by validation ROC-AUC -> evaluate once on held-out test data -> save pipeline + metadata.

Put your real CSVs in data/raw/ (same file names as in the notebooks). If a file is
missing, run  python ml/generate_demo_data.py  to create synthetic demo data.
"""
import json
import os
import sys
import time
import warnings

import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss, confusion_matrix,
                             f1_score, precision_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backend.schemas import DISEASES, add_derived, model_columns  # noqa: E402

warnings.filterwarnings("ignore")
RAW, OUT, SEED = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "models"), 42


# ----------------------------------------------------------------------------- data loading
def load(key):
    cfg = DISEASES[key]
    path = os.path.join(RAW, cfg["data_file"])
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found. Add your CSV or run ml/generate_demo_data.py")
    df = pd.read_csv(path)
    df.columns = df.columns.astype(str).str.strip()
    df = df.loc[:, ~df.columns.str.match(r"^Unnamed")]

    if key == "diabetes":
        df = df.drop_duplicates().reset_index(drop=True)
    elif key == "heart":
        for c in ("Cholesterol", "RestingBP"):  # zeros are missing values, not real readings
            df[c] = df[c].replace(0, np.nan)
    elif key == "cardio":
        ok = (df["AgeinYr"].between(18, 100) & df["height"].between(120, 220) & df["weight"].between(30, 200)
              & df["ap_hi"].between(80, 250) & df["ap_lo"].between(40, 150) & (df["ap_hi"] > df["ap_lo"]))
        df = df[ok].reset_index(drop=True)
    elif key == "kidney":
        for c in df.select_dtypes(exclude="number").columns:
            df[c] = (df[c].astype(str).str.strip().str.lower()
                     .replace({"?": np.nan, "nan": np.nan, "none": np.nan, "": np.nan}))
        for c in ("pcv", "wc", "rc"):  # numeric lab values stored as text in the original file
            df[c] = pd.to_numeric(df[c], errors="coerce")
        df = df[df["classification"].isin(["ckd", "notckd"])].reset_index(drop=True)
        df["classification"] = (df["classification"] == "ckd").astype(int)

    df = add_derived(key, df)
    cols, _, _ = model_columns(key)
    return df[cols], df[cfg["target"]].astype(int), os.path.exists(path + ".demo")


# ----------------------------------------------------------------------------- models
def candidate_models(key):
    cw = "balanced" if key == "kidney" else None
    try:
        from xgboost import XGBClassifier
        boost = ("XGBoost", XGBClassifier(n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.9,
                                          colsample_bytree=0.9, eval_metric="logloss", random_state=SEED, n_jobs=-1))
    except ImportError:  # xgboost not installed: use scikit-learn's histogram gradient boosting
        boost = ("Gradient Boosting", HistGradientBoostingClassifier(max_depth=4, learning_rate=0.05, max_iter=300,
                                                                      random_state=SEED))
    return {
        "Logistic Regression": LogisticRegression(max_iter=2000, class_weight=cw, random_state=SEED),
        "Decision Tree": DecisionTreeClassifier(max_depth=8, min_samples_leaf=10, class_weight=cw, random_state=SEED),
        "Random Forest": RandomForestClassifier(n_estimators=150, max_depth=14, min_samples_leaf=3, class_weight=cw,
                                                random_state=SEED, n_jobs=-1),
        boost[0]: boost[1],
        "ANN": MLPClassifier(hidden_layer_sizes=(64, 32), max_iter=600, early_stopping=True, random_state=SEED),
    }


def preprocessor(num_cols, cat_cols):
    return ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num_cols),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="most_frequent")),
                          ("oh", OneHotEncoder(handle_unknown="ignore"))]), cat_cols),
    ])


def metrics(y, prob):
    pred = (prob >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return dict(accuracy=accuracy_score(y, pred), precision=precision_score(y, pred, zero_division=0),
                recall=recall_score(y, pred), specificity=tn / (tn + fp), f1=f1_score(y, pred),
                roc_auc=roc_auc_score(y, prob), pr_auc=average_precision_score(y, prob),
                brier=brier_score_loss(y, prob), tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp))


def jsonable(v):
    return v.item() if isinstance(v, np.generic) else v


# ----------------------------------------------------------------------------- main
def train(key):
    t0 = time.time()
    X, y, demo = load(key)
    _, num_cols, cat_cols = model_columns(key)
    Xdev, Xte, ydev, yte = train_test_split(X, y, test_size=0.2, stratify=y, random_state=SEED)
    Xtr, Xval, ytr, yval = train_test_split(Xdev, ydev, test_size=0.125, stratify=ydev, random_state=SEED)  # 70/10/20
    print(f"\n=== {DISEASES[key]['title']}  rows={len(X)}  positives={y.mean():.1%}  "
          f"source={'DEMO (synthetic)' if demo else 'your data'}")

    fitted, rows, val_rows = {}, [], []
    for name, est in candidate_models(key).items():
        pipe = Pipeline([("pre", preprocessor(num_cols, cat_cols)), ("model", est)]).fit(Xtr, ytr)
        mv = metrics(yval, pipe.predict_proba(Xval)[:, 1])
        val_rows.append(dict(model=name, **{k: round(float(v), 4) if isinstance(v, float) else v for k, v in mv.items()}))
        fitted[name] = pipe
        print(f"  {name:<20} validation AUC {mv['roc_auc']:.4f}")

    best = max(val_rows, key=lambda r: (r["roc_auc"], r["pr_auc"], -r["brier"]))["model"]
    # Refit chosen model on development data (train + validation); test remains untouched until final evaluation.
    final_pipe = Pipeline([("pre", preprocessor(num_cols, cat_cols)), ("model", candidate_models(key)[best])]).fit(Xdev, ydev)
    mtest = metrics(yte, final_pipe.predict_proba(Xte)[:, 1])
    rows = [dict(r, model=r["model"], test_metrics=(mtest if r["model"] == best else None)) for r in val_rows]
    print(f"  -> deployed: {best}; held-out test AUC {mtest['roc_auc']:.4f}  recall {mtest['recall']:.3f}  ({time.time() - t0:.0f}s)")

    # "healthy reference" profile used by the explanation step (median / mode of the negative class)
    healthy = Xdev[ydev == 0]
    reference = {c: jsonable(healthy[c].median()) for c in num_cols}
    reference.update({c: jsonable(healthy[c].mode().iloc[0]) for c in cat_cols})

    os.makedirs(OUT, exist_ok=True)
    joblib.dump(final_pipe, os.path.join(OUT, f"{key}.joblib"), compress=3)
    meta = dict(key=key, deployed=best, data_source="demo-synthetic" if demo else "user-provided",
                n_rows=len(X), n_train=len(Xdev), n_validation=len(Xval), n_test=len(Xte), prevalence=round(float(y.mean()), 4),
                split_strategy="stratified 70/10/20; model selection on validation; final metrics on untouched test", final_test_metrics=mtest,
                features=list(X.columns), numeric=num_cols, categorical=cat_cols, reference=reference,
                all_models=rows, trained_at=time.strftime("%Y-%m-%d %H:%M"))
    json.dump(meta, open(os.path.join(OUT, f"{key}_meta.json"), "w"), indent=2)


if __name__ == "__main__":
    for k in (sys.argv[1:] or DISEASES):
        train(k)
    print("\nDone. Start the app with:  python run.py")
