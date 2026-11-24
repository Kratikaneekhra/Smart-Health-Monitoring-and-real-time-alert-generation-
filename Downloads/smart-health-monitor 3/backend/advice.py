"""Rule-based clinical flags (standard reference ranges) and lifestyle advice.

The ML model gives a probability; these rules translate raw readings into plain-language
observations a patient can discuss with a doctor. Ranges follow widely used guidance
(ADA for glucose/HbA1c, AHA/ACC for blood pressure, WHO for BMI) and are screening aids only.
"""

URGENCY = {
    "High": "See a specialist within 1 to 2 weeks.",
    "Moderate": "Book a specialist visit within 4 to 6 weeks.",
    "Low": "Routine check-up every 6 to 12 months is enough.",
}

ADVICE = {
    "diabetes": {
        "High": ["Get a fasting glucose test and a repeat HbA1c confirmed by a doctor.",
                 "Cut sugary drinks and refined carbohydrates; build meals around vegetables, pulses and whole grains.",
                 "Aim for 150 minutes of brisk walking or similar activity each week."],
        "Moderate": ["Ask your doctor about a fasting glucose or OGTT test.",
                     "Lose 5 to 7 percent of body weight if you are overweight; it sharply lowers diabetes risk.",
                     "Walk for 30 minutes on most days and limit sweets and fried food."],
        "Low": ["Keep your weight in a healthy range and stay active.",
                "Repeat blood sugar screening every 1 to 3 years, sooner if you gain weight."],
    },
    "heart": {
        "High": ["Do not wait for symptoms to worsen: arrange an ECG, echocardiogram and stress test with a cardiologist.",
                 "Avoid heavy exertion until a doctor has reviewed you.",
                 "Stop smoking and keep salt, fried food and red meat low."],
        "Moderate": ["Ask a cardiologist whether a stress test or lipid profile is needed.",
                     "Exercise moderately and monitor blood pressure at home.",
                     "Eat more fruit, vegetables, nuts and fish; reduce salt."],
        "Low": ["Keep up regular exercise and a balanced diet.",
                "Check blood pressure and cholesterol at least once a year after age 35."],
    },
    "cardio": {
        "High": ["Have your blood pressure and lipid profile checked by a doctor soon.",
                 "Reduce salt, stay active, and manage weight.",
                 "Quit tobacco and limit alcohol."],
        "Moderate": ["Check blood pressure regularly and keep a log to show your doctor.",
                     "Increase daily activity and reduce processed food.",
                     "Have a lipid profile and fasting glucose test."],
        "Low": ["Maintain an active lifestyle and healthy weight.",
                "Re-check blood pressure and cholesterol once a year."],
    },
    "kidney": {
        "High": ["Get serum creatinine, eGFR and a urine albumin-to-creatinine ratio done urgently.",
                 "Avoid anti-inflammatory painkillers such as ibuprofen or diclofenac unless a doctor approves.",
                 "Control blood pressure and blood sugar tightly; drink water as advised by your doctor."],
        "Moderate": ["Repeat kidney function tests and a urine test within a few weeks.",
                     "Keep blood pressure below 130/80 and manage diabetes if present.",
                     "Limit salt and avoid unprescribed painkillers."],
        "Low": ["Stay hydrated and keep blood pressure and sugar under control.",
                "Have kidney function checked yearly if you have diabetes or high blood pressure."],
    },
}

EMERGENCY = ("If you have chest pain, severe breathlessness, fainting, sudden weakness or confusion, "
             "call emergency services (112 in India) instead of waiting for an appointment.")


def clinical_flags(key, d):
    out = []

    def add(level, text):
        out.append({"level": level, "text": text})

    g = lambda k: d.get(k)

    def bp_flag(sys_, dia):
        if sys_ is None or dia is None:
            return
        if sys_ >= 140 or dia >= 90:
            add("high", f"Blood pressure {sys_:g}/{dia:g} mmHg is in the stage 2 hypertension range (140/90 or above).")
        elif sys_ >= 130 or dia >= 80:
            add("moderate", f"Blood pressure {sys_:g}/{dia:g} mmHg is in the stage 1 hypertension range (130/80 or above).")

    def bmi_flag(b):
        if b is None:
            return
        if b >= 30:
            add("high", f"BMI {b:.1f} is in the obese range (30 or above).")
        elif b >= 25:
            add("moderate", f"BMI {b:.1f} is in the overweight range (25 to 29.9).")
        elif b < 18.5:
            add("moderate", f"BMI {b:.1f} is below the healthy range (under 18.5).")

    if key == "diabetes":
        a, glu = g("HbA1c_level"), g("blood_glucose_level")
        if a >= 6.5:
            add("high", f"HbA1c {a:g}% is in the diabetes range (6.5% or above).")
        elif a >= 5.7:
            add("moderate", f"HbA1c {a:g}% is in the prediabetes range (5.7 to 6.4%).")
        if glu >= 200:
            add("high", f"Blood glucose {glu:g} mg/dL is very high (200 or above).")
        elif glu >= 140:
            add("moderate", f"Blood glucose {glu:g} mg/dL is above the usual range.")
        bmi_flag(g("bmi"))
        if g("hypertension") == 1:
            add("moderate", "You reported high blood pressure, which commonly occurs with diabetes.")
    elif key == "heart":
        bp = g("RestingBP")
        if bp >= 140:
            add("high", f"Resting systolic pressure {bp:g} mmHg is high (140 or above).")
        elif bp >= 130:
            add("moderate", f"Resting systolic pressure {bp:g} mmHg is elevated (130 or above).")
        c = g("Cholesterol")
        if c is not None and c >= 240:
            add("high", f"Total cholesterol {c:g} mg/dL is high (240 or above).")
        elif c is not None and c >= 200:
            add("moderate", f"Total cholesterol {c:g} mg/dL is borderline high (200 to 239).")
        if g("Oldpeak") >= 2:
            add("high", f"ST depression of {g('Oldpeak'):g} mm after exercise is marked.")
        elif g("Oldpeak") >= 1:
            add("moderate", f"ST depression of {g('Oldpeak'):g} mm after exercise is mildly raised.")
        if g("ExerciseAngina") == "Y":
            add("high", "Chest pain during exercise should be assessed by a cardiologist.")
        if g("FastingBS") == 1:
            add("moderate", "Fasting sugar above 120 mg/dL can increase heart risk.")
        if g("RestingECG") != "Normal":
            add("moderate", "Your resting ECG is not normal.")
    elif key == "cardio":
        bp_flag(g("ap_hi"), g("ap_lo"))
        h, w = g("height"), g("weight")
        bmi_flag(w / (h / 100) ** 2)
        if g("cholesterol") >= 2:
            add("high" if g("cholesterol") == 3 else "moderate", "Cholesterol is reported as above normal.")
        if g("gluc") >= 2:
            add("high" if g("gluc") == 3 else "moderate", "Glucose is reported as above normal.")
        if g("smoke") == 1:
            add("high", "Smoking greatly increases cardiovascular risk.")
        if g("alco") == 1:
            add("moderate", "Regular alcohol use can raise blood pressure.")
        if g("active") == 0:
            add("moderate", "Low physical activity raises cardiovascular risk.")
    elif key == "kidney":
        sc, hemo, al, pot, sod = g("sc"), g("hemo"), g("al"), g("pot"), g("sod")
        # Independent safety observations; these do not change the ML prediction.
        dbp, glu = g("bp"), g("bgr")
        if dbp is not None and dbp >= 120:
            add("high", f"Diastolic blood pressure {dbp:g} mmHg is extremely high. If this is a real reading, seek urgent medical assessment; emergency symptoms require emergency care.")
        elif dbp is not None and dbp >= 90:
            add("moderate", f"Diastolic blood pressure {dbp:g} mmHg is high and should be reviewed by a clinician.")
        if glu is not None and glu < 54:
            add("high", f"Blood glucose {glu:g} mg/dL is dangerously low if accurate. Treat this as a separate safety concern and seek immediate medical help.")
        elif glu is not None and glu < 70:
            add("moderate", f"Blood glucose {glu:g} mg/dL is low. Recheck and follow appropriate medical guidance.")
        if sc is not None and sc > 1.3:
            add("high", f"Serum creatinine {sc:g} mg/dL is above the usual limit (about 1.3).")
        if al is not None and al >= 1:
            add("high", f"Albumin {al:g}+ in urine (protein leak) is a key early sign of kidney damage.")
        if hemo is not None and hemo < 12:
            add("moderate", f"Haemoglobin {hemo:g} g/dL is low, which is common in chronic kidney disease.")
        if pot is not None and pot > 5.0:
            add("moderate", f"Potassium {pot:g} mEq/L is above the usual range.")
        if sod is not None and sod < 135:
            add("moderate", f"Sodium {sod:g} mEq/L is below the usual range.")
        if g("htn") == "yes":
            add("moderate", "High blood pressure is both a cause and a result of kidney disease.")
        if g("dm") == "yes":
            add("moderate", "Diabetes is the leading cause of kidney damage; keep sugars well controlled.")
    return out


def advice_for(key, level):
    return ADVICE[key][level]
