"""
Single source of truth for the four disease models.

The web form, server-side validation, ML training pipeline, explanations and
doctor matching ALL read from this file, so a feature is defined exactly once.
Feature names match the columns used in your research notebooks.
"""


def _o(*items):
    """Build select options from (value, label[, tag]) tuples."""
    return [{"value": i[0], "label": i[1], **({"tag": i[2]} if len(i) > 2 else {})} for i in items]


def num(name, label, unit, lo, hi, step=1, required=True, shared=None, help=None):
    return dict(name=name, label=label, kind="number", unit=unit, min=lo, max=hi,
                step=step, required=required, shared=shared, help=help)


def sel(name, label, options, required=True, shared=None, help=None):
    return dict(name=name, label=label, kind="select", options=options,
                required=required, shared=shared, help=help)


def is_numeric(f):
    return f["kind"] == "number" or all(isinstance(o["value"], (int, float)) for o in f["options"])


YESNO01 = _o((0, "No", "no"), (1, "Yes", "yes"))
YESNO = _o(("yes", "Yes", "yes"), ("no", "No", "no"))

DISEASES = {
    "diabetes": {
        "title": "Diabetes",
        "specialty": "Endocrinologist",
        "target": "diabetes",
        "data_file": "diabetes_prediction_dataset.csv",
        "thresholds": [0.15, 0.50],
        "summary": "Blood sugar, HbA1c, BMI and history",
        "fields": [
            sel("gender", "Sex", _o(("Female", "Female", "female"), ("Male", "Male", "male"), ("Other", "Other", "other")), shared="sex"),
            num("age", "Age", "years", 1, 100, shared="age"),
            sel("hypertension", "High blood pressure diagnosed", YESNO01, shared="htn"),
            sel("heart_disease", "Heart disease diagnosed", YESNO01),
            sel("smoking_history", "Smoking history", _o(
                ("never", "Never smoked"), ("No Info", "No information"), ("current", "Current smoker"),
                ("former", "Former smoker"), ("ever", "Smoked at some point"), ("not current", "Not a current smoker"))),
            num("bmi", "Body mass index", "kg/m²", 10, 70, 0.1, shared="bmi"),
            num("HbA1c_level", "HbA1c", "%", 3, 14, 0.1, help="Average blood sugar over about 3 months."),
            num("blood_glucose_level", "Blood glucose", "mg/dL", 50, 400, shared="glucose"),
        ],
        "sample_high": dict(gender="Male", age=58, hypertension=1, heart_disease=0, smoking_history="former",
                            bmi=33.1, HbA1c_level=8.2, blood_glucose_level=240),
        "sample_low": dict(gender="Female", age=29, hypertension=0, heart_disease=0, smoking_history="never",
                           bmi=22.4, HbA1c_level=5.1, blood_glucose_level=92),
    },
    "heart": {
        "title": "Heart disease",
        "specialty": "Cardiologist",
        "target": "HeartDisease",
        "data_file": "heart.csv",
        "thresholds": [0.35, 0.65],
        "summary": "ECG, chest pain, exercise response and lipids",
        "fields": [
            num("Age", "Age", "years", 18, 100, shared="age"),
            sel("Sex", "Sex", _o(("F", "Female", "female"), ("M", "Male", "male")), shared="sex"),
            sel("ChestPainType", "Chest pain type", _o(
                ("TA", "Typical angina"), ("ATA", "Atypical angina"), ("NAP", "Non-anginal pain"), ("ASY", "No chest pain symptoms"))),
            num("RestingBP", "Resting systolic BP", "mmHg", 70, 230, shared="sbp"),
            num("Cholesterol", "Total cholesterol", "mg/dL", 80, 600, required=False, help="Leave blank if unknown."),
            sel("FastingBS", "Fasting sugar above 120 mg/dL", YESNO01),
            sel("RestingECG", "Resting ECG", _o(("Normal", "Normal"), ("ST", "ST-T wave abnormality"), ("LVH", "Left ventricular hypertrophy"))),
            num("MaxHR", "Maximum heart rate reached", "bpm", 60, 220),
            sel("ExerciseAngina", "Chest pain during exercise", _o(("N", "No"), ("Y", "Yes"))),
            num("Oldpeak", "ST depression after exercise", "mm", -3, 7, 0.1, help="Reported on a stress-test ECG."),
            sel("ST_Slope", "ST segment slope", _o(("Up", "Upsloping"), ("Flat", "Flat"), ("Down", "Downsloping"))),
        ],
        "sample_high": dict(Age=61, Sex="M", ChestPainType="ASY", RestingBP=150, Cholesterol=285, FastingBS=1,
                            RestingECG="ST", MaxHR=108, ExerciseAngina="Y", Oldpeak=2.4, ST_Slope="Flat"),
        "sample_low": dict(Age=35, Sex="F", ChestPainType="ATA", RestingBP=118, Cholesterol=190, FastingBS=0,
                           RestingECG="Normal", MaxHR=172, ExerciseAngina="N", Oldpeak=0.0, ST_Slope="Up"),
    },
    "cardio": {
        "title": "Cardiovascular screening",
        "specialty": "Cardiologist",
        "target": "cardio",
        "data_file": "Health Screening Data.csv",
        "thresholds": [0.40, 0.65],
        "summary": "Blood pressure, weight, lifestyle and routine labs",
        "fields": [
            num("AgeinYr", "Age", "years", 18, 100, shared="age"),
            sel("gender", "Sex", _o((1, "Female", "female"), (2, "Male", "male")), shared="sex"),
            num("height", "Height", "cm", 120, 220),
            num("weight", "Weight", "kg", 30, 200),
            num("ap_hi", "Systolic BP (upper)", "mmHg", 80, 250, shared="sbp"),
            num("ap_lo", "Diastolic BP (lower)", "mmHg", 40, 150, shared="dbp"),
            sel("cholesterol", "Cholesterol level", _o((1, "Normal"), (2, "Above normal"), (3, "Well above normal"))),
            sel("gluc", "Glucose level", _o((1, "Normal"), (2, "Above normal"), (3, "Well above normal"))),
            sel("smoke", "Smoker", YESNO01),
            sel("alco", "Drinks alcohol", YESNO01),
            sel("active", "Physically active", YESNO01),
        ],
        "derived": ["BMI"],
        "sample_high": dict(AgeinYr=58, gender=2, height=168, weight=88, ap_hi=160, ap_lo=100, cholesterol=3,
                            gluc=2, smoke=1, alco=0, active=0),
        "sample_low": dict(AgeinYr=32, gender=1, height=165, weight=58, ap_hi=112, ap_lo=72, cholesterol=1,
                           gluc=1, smoke=0, alco=0, active=1),
    },
    "kidney": {
        "title": "Kidney disease",
        "specialty": "Nephrologist",
        "target": "classification",
        "data_file": "kidney_disease.csv",
        "thresholds": [0.30, 0.70],
        "min_filled": 8,
        "summary": "Urine and blood tests, anaemia and related conditions",
        "fields": [
            num("age", "Age", "years", 1, 100, shared="age"),
            num("bp", "Diastolic blood pressure", "mmHg", 40, 180, shared="dbp"),
            sel("sg", "Urine specific gravity", _o((1.005, "1.005"), (1.010, "1.010"), (1.015, "1.015"), (1.020, "1.020"), (1.025, "1.025")), required=False),
            sel("al", "Urine albumin (dipstick)", _o((0, "0"), (1, "1+"), (2, "2+"), (3, "3+"), (4, "4+"), (5, "5+")), required=False),
            sel("su", "Urine sugar (dipstick)", _o((0, "0"), (1, "1+"), (2, "2+"), (3, "3+"), (4, "4+"), (5, "5+")), required=False),
            sel("rbc", "Red blood cells in urine", _o(("normal", "Normal"), ("abnormal", "Abnormal")), required=False),
            sel("pc", "Pus cells in urine", _o(("normal", "Normal"), ("abnormal", "Abnormal")), required=False),
            sel("pcc", "Pus cell clumps", _o(("notpresent", "Not present"), ("present", "Present")), required=False),
            sel("ba", "Bacteria in urine", _o(("notpresent", "Not present"), ("present", "Present")), required=False),
            num("bgr", "Random blood glucose", "mg/dL", 20, 500, required=False, shared="glucose"),
            num("bu", "Blood urea", "mg/dL", 1, 400, 0.1, required=False),
            num("sc", "Serum creatinine", "mg/dL", 0.3, 80, 0.1, required=False),
            num("sod", "Sodium", "mEq/L", 100, 170, 0.1, required=False),
            num("pot", "Potassium", "mEq/L", 2, 50, 0.1, required=False),
            num("hemo", "Haemoglobin", "g/dL", 3, 19, 0.1, required=False),
            num("pcv", "Packed cell volume", "%", 8, 60, required=False),
            num("wc", "White blood cell count", "cells/cumm", 2000, 30000, 100, required=False),
            num("rc", "Red blood cell count", "million/cmm", 2, 8.5, 0.1, required=False),
            sel("htn", "High blood pressure diagnosed", YESNO, required=False, shared="htn"),
            sel("dm", "Diabetes diagnosed", YESNO, required=False),
            sel("cad", "Coronary artery disease", YESNO, required=False),
            sel("appet", "Appetite", _o(("good", "Good"), ("poor", "Poor")), required=False),
            sel("pe", "Swelling in feet (pedal oedema)", YESNO, required=False),
            sel("ane", "Anaemia diagnosed", YESNO, required=False),
        ],
        "sample_high": dict(age=62, bp=90, sg=1.010, al=3, su=1, rbc="abnormal", pc="abnormal", pcc="present", ba="notpresent",
                            bgr=160, bu=80, sc=4.2, sod=134, pot=5.2, hemo=9.8, pcv=30, wc=9800, rc=3.4, htn="yes",
                            dm="yes", cad="no", appet="poor", pe="yes", ane="yes"),
        "sample_low": dict(age=34, bp=70, sg=1.020, al=0, su=0, rbc="normal", pc="normal", pcc="notpresent", ba="notpresent",
                           bgr=98, bu=28, sc=0.9, sod=140, pot=4.4, hemo=15.2, pcv=46, wc=7600, rc=5.3, htn="no",
                           dm="no", cad="no", appet="good", pe="no", ane="no"),
    },
}

SPECIALTIES = ["Endocrinologist", "Cardiologist", "Nephrologist", "General Physician"]


def add_derived(key, df):
    """Derived columns shared by training and prediction (keeps them identical)."""
    if key == "cardio":
        df["BMI"] = (df["weight"] / (df["height"] / 100) ** 2).round(1)
    return df


def model_columns(key):
    d = DISEASES[key]
    derived = d.get("derived", [])
    cols = [f["name"] for f in d["fields"]] + derived
    num_cols = [f["name"] for f in d["fields"] if is_numeric(f)] + derived
    cat_cols = [f["name"] for f in d["fields"] if not is_numeric(f)]
    return cols, num_cols, cat_cols


def public_schema():
    keys = ("title", "specialty", "summary", "thresholds", "fields", "sample_high", "sample_low")
    out = {}
    for k, d in DISEASES.items():
        out[k] = {x: d[x] for x in keys}
        out[k]["min_filled"] = d.get("min_filled")
    return out
