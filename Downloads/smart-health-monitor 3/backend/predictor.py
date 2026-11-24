"""Loads the trained pipelines, validates patient input, predicts risk and explains the result."""
import json
import os

import joblib
import numpy as np
import pandas as pd

from .schemas import DISEASES, add_derived, model_columns

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models")


# Public datasets contain statistical artifacts (e.g. smokers having slightly LOWER disease rates in the
# cardiovascular screening data). A model learns these, but telling a patient that smoking "lowered" their
# risk would be wrong, so known risk exposures are never shown as protective (and healthy habits never as harmful).
ADVERSE = {"smoke": [1], "alco": [1], "active": [0], "smoking_history": ["current", "former", "ever"],
           "hypertension": [1], "heart_disease": [1], "htn": ["yes"], "dm": ["yes"], "cad": ["yes"], "ane": ["yes"],
           "pe": ["yes"], "appet": ["poor"], "FastingBS": [1], "ExerciseAngina": ["Y"]}
HEALTHY = {"smoke": [0], "alco": [0], "active": [1], "smoking_history": ["never"], "hypertension": [0],
           "heart_disease": [0], "htn": ["no"], "dm": ["no"], "cad": ["no"], "ane": ["no"], "pe": ["no"],
           "appet": ["good"], "FastingBS": [0], "ExerciseAngina": ["N"]}


class ValidationError(Exception):
    def __init__(self, errors):
        super().__init__("Invalid input")
        self.errors = errors


class DiseaseModel:
    def __init__(self, key):
        self.key, self.cfg = key, DISEASES[key]
        self.pipe = joblib.load(os.path.join(MODEL_DIR, f"{key}.joblib"))
        self.meta = json.load(open(os.path.join(MODEL_DIR, f"{key}_meta.json")))
        self.fields = {f["name"]: f for f in self.cfg["fields"]}
        self.columns, _, _ = model_columns(key)

    # ------------------------------------------------------------------ validation
    def validate(self, raw):
        clean, errors = {}, {}
        for name, f in self.fields.items():
            v = raw.get(name)
            if v is None or v == "":
                if f["required"]:
                    errors[name] = "This value is required."
                clean[name] = None
                continue
            if f["kind"] == "number":
                try:
                    x = float(v)
                except (TypeError, ValueError):
                    errors[name] = "Enter a number."
                    continue
                if not (f["min"] <= x <= f["max"]):
                    errors[name] = f"Enter a value between {f['min']} and {f['max']} {f.get('unit') or ''}.".strip()
                    continue
                clean[name] = x
            else:
                match = next((o for o in f["options"] if str(o["value"]) == str(v)), None)
                if match is None:
                    errors[name] = "Choose one of the listed options."
                    continue
                clean[name] = match["value"]
        if not errors and self.key == "cardio" and clean["ap_hi"] <= clean["ap_lo"]:
            errors["ap_hi"] = "Systolic pressure must be higher than diastolic."
        need = self.cfg.get("min_filled")
        if not errors and need and sum(v is not None for v in clean.values()) < need:
            errors["_form"] = f"Fill in at least {need} fields so the model has enough information."
        if errors:
            raise ValidationError(errors)
        return clean

    # ------------------------------------------------------------------ prediction
    def _frame(self, rows):
        df = add_derived(self.key, pd.DataFrame(rows))[self.columns].copy()
        for c in self.meta["numeric"]:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        for c in self.meta["categorical"]:
            df[c] = df[c].astype(object).where(df[c].notna(), np.nan)
        return df

    def _proba(self, rows):
        return self.pipe.predict_proba(self._frame(rows))[:, 1]

    def level(self, p):
        lo, hi = self.cfg["thresholds"]
        return "Low" if p < lo else "Moderate" if p < hi else "High"

    def describe(self, name, value):
        f = self.fields.get(name)
        if f is None:
            return f"{value:g}"
        if f["kind"] == "select":
            return next((o["label"] for o in f["options"] if o["value"] == value), str(value))
        return f"{value:g} {f['unit']}".strip()

    def explain(self, clean, base_p, top=4):
        """Reference-value occlusion: replace inputs with training reference values and
        measure change in model log-odds. This is not SHAP, causal evidence, or clinical advice."""
        names = [n for n, v in clean.items() if v is not None]
        ref = self.meta["reference"]
        variants = []
        for n in names:
            row = dict(clean)
            row[n] = ref.get(n, clean[n])
            variants.append(row)
        probs = self._proba(variants) if variants else []
        logit = lambda p: float(np.log(np.clip(p, 1e-7, 1 - 1e-7) / (1 - np.clip(p, 1e-7, 1 - 1e-7))))
        impacts = []
        for n, p in zip(names, probs):
            delta = logit(base_p) - logit(p)  # positive: this input raises the risk
            if abs(delta) >= 0.1:
                impacts.append(dict(feature=n, label=self.fields[n]["label"],
                                    value=self.describe(n, clean[n]), impact=round(delta, 3)))
        peak = max([abs(i["impact"]) for i in impacts] or [1])
        for i in impacts:
            i["strength"] = round(abs(i["impact"]) / peak, 3)
        impacts = [i for i in impacts if not (
            (i["impact"] < 0 and clean[i["feature"]] in ADVERSE.get(i["feature"], []))
            or (i["impact"] > 0 and clean[i["feature"]] in HEALTHY.get(i["feature"], [])))]
        up = sorted([i for i in impacts if i["impact"] > 0], key=lambda i: -i["impact"])[:top]
        down = sorted([i for i in impacts if i["impact"] < 0], key=lambda i: i["impact"])[:3]
        return up, down

    def predict(self, raw, explain=True):
        clean = self.validate(raw)
        p = float(self._proba([clean])[0])
        out = dict(disease=self.key, title=self.cfg["title"], specialty=self.cfg["specialty"],
                   probability=round(p, 4), percent=min(99.9, max(0.1, round(p * 100, 1))), risk_level=self.level(p),
                   thresholds=self.cfg["thresholds"], inputs=clean,
                   model=self._model_info())
        if explain:
            out["factors_up"], out["factors_down"] = self.explain(clean, p)
        return out

    def _model_info(self):
        best = next(m for m in self.meta["all_models"] if m["model"] == self.meta["deployed"])
        return dict(name=self.meta["deployed"], roc_auc=best["roc_auc"], recall=best["recall"],
                    accuracy=best["accuracy"], data_source=self.meta["data_source"], n_train=self.meta["n_train"])


class ModelRegistry:
    def __init__(self):
        self.models = {}
        for k in DISEASES:
            if os.path.exists(os.path.join(MODEL_DIR, f"{k}.joblib")):
                self.models[k] = DiseaseModel(k)

    def get(self, key):
        if key not in self.models:
            raise KeyError(key)
        return self.models[key]

    def ready(self):
        return sorted(self.models)
