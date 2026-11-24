"""Doctor recommendation engine.

1. From the health report decide WHICH specialties are needed (rule: moderate/high risk -> that
   disease's specialist; all low -> general physician).
2. Turn the patient's findings into a short text query (e.g. "diabetes hba1c glucose hypertension").
3. Rank doctors of that specialty with a weighted score:
       0.30  TF-IDF cosine similarity between the query and the doctor's expertise text
       0.35  location (same city = 1, teleconsult from elsewhere = 0.5)
       0.20  patient rating            0.10  years of experience        0.05  preferred consultation mode
"""
import os

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .advice import URGENCY

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "doctors.csv")

DISEASE_TERMS = {
    "diabetes": "diabetes blood sugar hba1c glucose",
    "heart": "heart cardiac angina ecg chest pain coronary",
    "cardio": "hypertension blood pressure cholesterol cardiovascular risk",
    "kidney": "kidney creatinine proteinuria albumin renal",
}
FEATURE_TERMS = {
    "HbA1c_level": "hba1c diabetes", "blood_glucose_level": "glucose blood sugar", "bgr": "glucose",
    "hypertension": "hypertension blood pressure", "RestingBP": "hypertension blood pressure",
    "ap_hi": "hypertension blood pressure", "ap_lo": "hypertension", "bp": "hypertension blood pressure",
    "htn": "hypertension", "bmi": "obesity weight metabolic", "weight": "obesity weight", "BMI": "obesity weight",
    "Cholesterol": "cholesterol lipid", "cholesterol": "cholesterol lipid",
    "ChestPainType": "chest pain angina", "ExerciseAngina": "angina stress test", "ST_Slope": "ecg stress test",
    "Oldpeak": "ecg stress test", "RestingECG": "ecg", "MaxHR": "ecg stress test",
    "sc": "creatinine kidney function", "bu": "kidney function", "al": "proteinuria albumin",
    "hemo": "anaemia kidney", "pcv": "anaemia", "pot": "electrolyte potassium", "sod": "electrolyte sodium",
    "dm": "diabetic nephropathy diabetes", "smoking_history": "lifestyle risk", "smoke": "lifestyle risk",
}
GENERIC = {"blood", "function", "risk"}
SPEC_PRIORITY = {"High": 3, "Moderate": 2, "Low": 1}


class DoctorRecommender:
    def __init__(self, path=DATA):
        self.df = pd.read_csv(path)
        self.df["text"] = self.df["specialization"].str.lower() + " " + self.df["expertise"].str.lower()
        self.vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vec.fit_transform(self.df["text"])

    # ------------------------------------------------------------------ directory search
    def search(self, specialization=None, city=None, q=None, mode=None, sort="rating", limit=60):
        d = self.df
        if specialization:
            d = d[d["specialization"].str.lower() == specialization.lower()]
        if city:
            d = d[d["city"].str.lower() == city.lower()]
        if mode:
            d = d[d["mode"].str.contains(mode, case=False)]
        if q:
            d = d[d[["name", "hospital", "expertise", "specialization"]].astype(str).agg(" ".join, axis=1)
                  .str.contains(q, case=False, regex=False)]
        key = {"rating": "rating", "experience": "experience_years", "fee": "consultation_fee_inr"}.get(sort, "rating")
        d = d.sort_values(key, ascending=(sort == "fee"))
        return [self._row(r) for _, r in d.head(limit).iterrows()]

    def cities(self):
        return sorted(self.df["city"].unique())

    @staticmethod
    def _row(r, **extra):
        out = {k: (v.item() if hasattr(v, "item") else v) for k, v in r.items() if k != "text"}
        out.update(extra)
        return out

    # ------------------------------------------------------------------ recommendation
    def recommend(self, results, city=None, mode=None, per_group=3):
        need = {}
        for r in results:
            if r["risk_level"] == "Low":
                continue
            g = need.setdefault(r["specialty"], dict(reasons=[], terms=[], rank=0))
            g["reasons"].append(f"{r['title']}: {r['risk_level'].lower()} risk ({r['percent']:g}%)")
            g["terms"].append(DISEASE_TERMS[r["disease"]])
            g["terms"] += [FEATURE_TERMS.get(f["feature"], "") for f in r.get("factors_up", [])]
            g["rank"] = max(g["rank"], SPEC_PRIORITY[r["risk_level"]])
        if not need:
            need["General Physician"] = dict(reasons=["All screenings show low risk; a routine check-up keeps it that way"],
                                             terms=["preventive health check-up lifestyle screening"], rank=1)
        top_level = {3: "High", 2: "Moderate", 1: "Low"}
        groups = []
        for spec, g in sorted(need.items(), key=lambda kv: -kv[1]["rank"]):
            level = top_level[g["rank"]]
            groups.append(dict(specialty=spec, risk_level=level, urgency=URGENCY[level], reasons=g["reasons"],
                               doctors=self._rank(spec, " ".join(g["terms"]), city, mode, per_group)))
        return groups

    def _rank(self, spec, query, city, mode, n):
        idx = np.where(self.df["specialization"].values == spec)[0]
        if len(idx) == 0:
            return []
        sim = cosine_similarity(self.vec.transform([query.lower()]), self.matrix[idx]).ravel()
        sim = sim / sim.max() if sim.max() > 0 else sim
        pool = self.df.iloc[idx]
        rating = ((pool["rating"].values - 3.5) / 1.5).clip(0, 1)
        exp = (pool["experience_years"].values.clip(0, 30)) / 30
        same = (pool["city"].str.lower().values == (city or "").lower())
        tele = pool["mode"].str.contains("Teleconsult").values
        loc = np.where(same, 1.0, np.where(tele, 0.5, 0.0)) if city else np.full(len(pool), 0.5)
        mode_fit = (pool["mode"].str.contains(mode, case=False).values.astype(float) if mode else np.full(len(pool), 0.5))
        score = 0.30 * sim + 0.20 * rating + 0.10 * exp + 0.35 * loc + 0.05 * mode_fit
        out = []
        for i in np.argsort(-score)[:n]:
            r = pool.iloc[i]
            reasons = []
            hits = [t for t in set(query.lower().split()) if t in r["expertise"].split() and len(t) > 3 and t not in GENERIC]
            if hits:
                reasons.append("Expertise matches your findings: " + ", ".join(sorted(hits)[:3]))
            if same[i]:
                reasons.append(f"Practises in {r['city']}")
            elif city and tele[i]:
                reasons.append("Offers teleconsultation, so no travel is needed")
            out.append(self._row(r, match_percent=int(round(score[i] * 100)), reasons=reasons, same_city=bool(same[i])))
        return out
