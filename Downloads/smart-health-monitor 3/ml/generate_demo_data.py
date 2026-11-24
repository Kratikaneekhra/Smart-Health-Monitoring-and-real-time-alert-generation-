"""
Creates SYNTHETIC demo datasets with the same columns as the four public datasets
used in the research notebooks, so the project runs out of the box.

    python ml/generate_demo_data.py

IMPORTANT: this data is artificial. For real results copy your original CSVs into
data/raw/ (same file names) and run  python ml/train_models.py
The generator never overwrites a real file: it only writes missing ones.
"""
import os
import numpy as np
import pandas as pd

RAW = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
rng = np.random.default_rng(42)
sigmoid = lambda z: 1 / (1 + np.exp(-z))


def diabetes(n=30000):
    age = np.clip(rng.normal(42, 20, n), 1, 80).round(0)
    bmi = np.clip(rng.lognormal(3.3, 0.22, n), 12, 65).round(2)
    htn = rng.random(n) < (0.03 + 0.2 * (age > 50))
    hd = rng.random(n) < (0.01 + 0.09 * (age > 55))
    smoke = rng.choice(["never", "No Info", "current", "former", "ever", "not current"], n, p=[.35, .36, .09, .09, .04, .07])
    hba1c = np.clip(rng.normal(5.5, 1.05, n), 3.5, 9).round(1)
    glu = np.clip(rng.normal(138, 40, n), 80, 300).round(0)
    z = (-5.2 + 1.25 * (hba1c - 5.0) + 0.021 * (glu - 100) + 0.025 * (age - 40) + 0.05 * (bmi - 27)
         + 0.6 * htn + 0.6 * hd + 0.25 * (smoke == "current"))
    y = rng.random(n) < sigmoid(z)
    return pd.DataFrame(dict(gender=rng.choice(["Female", "Male", "Other"], n, p=[.585, .414, .001]), age=age,
                             hypertension=htn.astype(int), heart_disease=hd.astype(int), smoking_history=smoke,
                             bmi=bmi, HbA1c_level=hba1c, blood_glucose_level=glu.astype(int), diabetes=y.astype(int)))


def heart(n=918):
    age = np.clip(rng.normal(53, 9.5, n), 28, 77).round(0)
    sex = rng.choice(["M", "F"], n, p=[.79, .21])
    cp = rng.choice(["ASY", "NAP", "ATA", "TA"], n, p=[.54, .22, .19, .05])
    bp = np.clip(rng.normal(132, 18, n), 90, 200).round(0)
    chol = np.clip(rng.normal(245, 55, n), 100, 560).round(0)
    chol[rng.random(n) < 0.19] = 0  # the real heart.csv stores missing cholesterol as 0
    fbs = (rng.random(n) < 0.23).astype(int)
    ecg = rng.choice(["Normal", "LVH", "ST"], n, p=[.6, .2, .2])
    maxhr = np.clip(rng.normal(137, 25, n), 65, 200).round(0)
    ang = rng.choice(["N", "Y"], n, p=[.6, .4])
    old = np.clip(rng.gamma(1.4, 0.7, n) - 0.1, -1, 6).round(1)
    slope = rng.choice(["Flat", "Up", "Down"], n, p=[.5, .43, .07])
    z = (-3.6 + 0.04 * (age - 53) + 1.1 * (sex == "M") + 1.9 * (cp == "ASY") - 0.3 * (cp == "NAP") - 1.0 * (cp == "ATA")
         + 0.01 * (bp - 130) + 0.9 * fbs + 0.5 * (ecg == "ST") - 0.028 * (maxhr - 137) + 1.4 * (ang == "Y")
         + 0.65 * old + 1.1 * (slope == "Flat") + 1.4 * (slope == "Down") + 0.6 * (chol == 0))
    y = rng.random(n) < sigmoid(z)
    return pd.DataFrame(dict(Age=age, Sex=sex, ChestPainType=cp, RestingBP=bp, Cholesterol=chol, FastingBS=fbs,
                             RestingECG=ecg, MaxHR=maxhr, ExerciseAngina=ang, Oldpeak=old, ST_Slope=slope,
                             HeartDisease=y.astype(int)))


def cardio(n=30000):
    age = np.clip(rng.normal(53, 6.8, n), 30, 65).round(0)
    gender = rng.choice([1, 2], n, p=[.65, .35])
    height = np.clip(rng.normal(164.4, 8, n), 140, 200).round(0)
    weight = np.clip(rng.normal(74, 14, n), 40, 160).round(0)
    ap_hi = np.clip(rng.normal(127, 16, n), 90, 220).round(0)
    ap_lo = np.clip(ap_hi * 0.64 + rng.normal(0, 7, n), 55, 130).round(0)
    ap_lo = np.minimum(ap_lo, ap_hi - 15)
    chol = rng.choice([1, 2, 3], n, p=[.75, .13, .12])
    gluc = rng.choice([1, 2, 3], n, p=[.85, .07, .08])
    smoke = (rng.random(n) < .088).astype(int)
    alco = (rng.random(n) < .054).astype(int)
    active = (rng.random(n) < .80).astype(int)
    bmi = (weight / (height / 100) ** 2).round(1)
    z = (-0.4 + 0.075 * (age - 53) + 0.045 * (ap_hi - 127) + 0.02 * (ap_lo - 82) + 0.5 * (chol - 1) + 0.15 * (gluc - 1)
         + 0.04 * (bmi - 27) - 0.2 * active - 0.1 * smoke) / 1.1
    y = rng.random(n) < sigmoid(z)
    df = pd.DataFrame(dict(age=(age * 365).astype(int), gender=gender, height=height, weight=weight, ap_hi=ap_hi,
                           ap_lo=ap_lo, cholesterol=chol, gluc=gluc, smoke=smoke, alco=alco, active=active,
                           cardio=y.astype(int), AgeinYr=age.astype(int), BMI=bmi))
    df["BMICat"] = pd.cut(df.BMI, [0, 18.5, 25, 30, 99], labels=["Underweight", "Normal", "Over Weight", "Obese"])
    df.insert(0, "id", range(len(df)))
    return df


def kidney(n=400):
    ckd = rng.random(n) < 0.625
    c = lambda a, b: np.where(ckd, a, b)
    def noisy(x, frac):  # inject missing values like the real file
        x = x.astype(float); x[rng.random(n) < frac] = np.nan; return x
    yn = lambda p1, p0: np.where(rng.random(n) < c(p1, p0), "yes", "no")
    df = pd.DataFrame(dict(
        age=noisy(np.clip(rng.normal(c(55, 46), 15), 5, 90).round(0), .02),
        bp=noisy(np.clip(rng.normal(c(79, 72), 10), 50, 140).round(0), .03),
        sg=noisy(np.where(ckd, rng.choice([1.005, 1.010, 1.015, 1.020, 1.025], n, p=[.1, .45, .25, .15, .05]),
                          rng.choice([1.015, 1.020, 1.025], n, p=[.05, .35, .6])), .12),
        al=noisy(np.where(ckd, rng.choice([0, 1, 2, 3, 4], n, p=[.1, .2, .3, .25, .15]), rng.choice([0, 1], n, p=[.95, .05])), .12),
        su=noisy(np.where(ckd, rng.choice([0, 1, 2, 3], n, p=[.6, .15, .15, .1]), 0), .12),
        rbc=np.where(rng.random(n) < .38, None, np.where(rng.random(n) < c(.55, .02), "abnormal", "normal")),
        pc=np.where(rng.random(n) < .16, None, np.where(rng.random(n) < c(.5, .03), "abnormal", "normal")),
        pcc=np.where(rng.random(n) < c(.25, .01), "present", "notpresent"),
        ba=np.where(rng.random(n) < c(.12, .01), "present", "notpresent"),
        bgr=noisy(np.clip(rng.normal(c(160, 108), c(70, 18)), 60, 490).round(0), .11),
        bu=noisy(np.clip(rng.normal(c(75, 33), c(55, 9)), 10, 390).round(1), .05),
        sc=noisy(np.clip(rng.lognormal(c(1.0, -0.15), c(0.9, 0.2)), 0.4, 76).round(1), .04),
        sod=noisy(np.clip(rng.normal(c(136, 141), c(8, 3)), 110, 160).round(1), .22),
        pot=noisy(np.clip(rng.normal(c(4.6, 4.3), c(1.6, .5)), 2.5, 15).round(1), .22),
        hemo=noisy(np.clip(rng.normal(c(10.7, 15), c(2.2, 1.4)), 3.5, 17.8).round(1), .13),
        pcv=noisy(np.clip(rng.normal(c(33, 46), c(8, 4)), 10, 54).round(0), .17),
        wc=noisy(np.clip(rng.normal(c(9100, 7600), c(3300, 1500)), 2200, 26000).round(-2), .26),
        rc=noisy(np.clip(rng.normal(c(3.9, 5.3), c(0.9, 0.5)), 2.1, 8).round(1), .32),
        htn=yn(.55, .0), dm=yn(.5, .0), cad=yn(.1, .0),
        appet=np.where(rng.random(n) < c(.3, .0), "poor", "good"),
        pe=yn(.4, .0), ane=yn(.3, .0),
        classification=np.where(ckd, "ckd", "notckd")))
    df.insert(0, "id", range(n))
    return df


JOBS = {"diabetes_prediction_dataset.csv": diabetes, "heart.csv": heart,
        "Health Screening Data.csv": cardio, "kidney_disease.csv": kidney}

if __name__ == "__main__":
    os.makedirs(RAW, exist_ok=True)
    for fname, fn in JOBS.items():
        path = os.path.join(RAW, fname)
        if os.path.exists(path):
            print(f"skip   {fname} (already exists - real data is never overwritten)")
            continue
        df = fn()
        df.to_csv(path, index=False)
        open(path + ".demo", "w").write("synthetic demo data")
        print(f"wrote  {fname}: {df.shape}  positive rate {df.iloc[:, -1].mean() if fname != 'Health Screening Data.csv' else df.cardio.mean():.2%}"
              if fname not in ("kidney_disease.csv",) else f"wrote  {fname}: {df.shape}")
