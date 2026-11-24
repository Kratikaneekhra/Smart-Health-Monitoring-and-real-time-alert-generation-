"""
Builds data/doctors.csv: a FICTIONAL sample doctor directory used by the recommender.

Names, hospitals and ratings are invented for demonstration. To use real data, replace
doctors.csv with your own file that has the same columns:
doctor_id, name, specialization, expertise, qualification, experience_years, hospital, city, state,
consultation_fee_inr, rating, patients_treated, available_days, mode, languages
"""
import csv
import os
import random

random.seed(7)
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "doctors.csv")

FIRST_M = ["Arjun", "Rohan", "Vikram", "Sanjay", "Nikhil", "Harsh", "Karan", "Manish", "Rahul", "Amit", "Devansh", "Imran", "Suresh", "Pranav", "Yash"]
FIRST_F = ["Priya", "Ananya", "Neha", "Kavita", "Meera", "Isha", "Sneha", "Riya", "Pooja", "Divya", "Nandini", "Farah", "Shalini", "Tanvi", "Aditi"]
LAST = ["Sharma", "Mehta", "Patel", "Iyer", "Nair", "Reddy", "Gupta", "Joshi", "Desai", "Kulkarni", "Banerjee", "Chauhan", "Shah", "Menon", "Verma", "Bhatt", "Rao", "Singh", "Kapoor", "Trivedi"]

CITIES = [("Ahmedabad", "Gujarat"), ("Rajkot", "Gujarat"), ("Surat", "Gujarat"), ("Vadodara", "Gujarat"),
          ("Mumbai", "Maharashtra"), ("Pune", "Maharashtra"), ("Delhi", "Delhi"), ("Bengaluru", "Karnataka"),
          ("Chennai", "Tamil Nadu"), ("Hyderabad", "Telangana"), ("Kolkata", "West Bengal"), ("Jaipur", "Rajasthan")]

HOSPITAL_A = ["Lifeline", "Sunrise", "Harmony", "Evergreen", "Trinity", "Nirmal", "Shreeji", "Medicare Plus", "Anand", "Pinnacle", "Zenith", "Greenfield"]
HOSPITAL_B = ["Multispeciality Hospital", "Heart & Diabetes Centre", "Institute of Medical Sciences", "Super Speciality Hospital", "Clinic & Research Centre"]

SPECIALTIES = {
    "Endocrinologist": dict(
        quals=["MBBS, MD (Medicine), DM (Endocrinology)", "MBBS, DNB (Endocrinology)", "MBBS, MD, Fellowship in Diabetology"],
        fee=(700, 1500),
        expertise=["type 2 diabetes insulin therapy hba1c management blood sugar",
                   "diabetes in pregnancy thyroid disorders hormone",
                   "obesity metabolic syndrome weight diabetes prevention prediabetes",
                   "diabetic complications diabetic foot kidney eye screening glucose"]),
    "Cardiologist": dict(
        quals=["MBBS, MD (Medicine), DM (Cardiology)", "MBBS, DNB (Cardiology)", "MBBS, MD, DM, FSCAI"],
        fee=(800, 1800),
        expertise=["preventive cardiology hypertension blood pressure cholesterol lipid",
                   "interventional cardiology angina chest pain angioplasty ecg stress test",
                   "heart failure cardiomyopathy ecg echocardiography cardiac",
                   "cardiac rehabilitation lifestyle risk assessment coronary artery disease"]),
    "Nephrologist": dict(
        quals=["MBBS, MD (Medicine), DM (Nephrology)", "MBBS, DNB (Nephrology)"],
        fee=(800, 1600),
        expertise=["chronic kidney disease proteinuria creatinine albumin kidney function",
                   "dialysis kidney transplant renal failure",
                   "hypertension and kidney diabetic nephropathy blood pressure",
                   "anaemia of kidney disease electrolyte potassium sodium disorders"]),
    "General Physician": dict(
        quals=["MBBS, MD (General Medicine)", "MBBS, DNB (Family Medicine)", "MBBS"],
        fee=(300, 800),
        expertise=["preventive health check-up lifestyle screening annual",
                   "hypertension diabetes chronic disease care blood pressure sugar",
                   "family medicine infections fever general illness",
                   "geriatric care elderly preventive screening"]),
}

rows, used, n = [], set(), 1
plan = [(city, spec) for city in CITIES for spec in SPECIALTIES] + \
       [(random.choice(CITIES), random.choice(list(SPECIALTIES))) for _ in range(14)]
for (city, state), spec in plan:
    cfg = SPECIALTIES[spec]
    female = random.random() < 0.42
    while True:
        name = f"Dr. {random.choice(FIRST_F if female else FIRST_M)} {random.choice(LAST)}"
        if name not in used:
            used.add(name)
            break
    exp = random.randint(6, 34)
    rows.append(dict(
        doctor_id=f"D{n:03d}", name=name, specialization=spec, expertise=cfg["expertise"][(n + random.randint(0, 3)) % 4],
        qualification=random.choice(cfg["quals"]), experience_years=exp,
        hospital=f"{random.choice(HOSPITAL_A)} {random.choice(HOSPITAL_B)}", city=city, state=state,
        consultation_fee_inr=round(random.randint(*cfg["fee"]) / 50) * 50,
        rating=round(min(4.9, max(3.9, random.gauss(4.5, 0.25))), 1),
        patients_treated=random.randint(8, 60) * 100 + exp * 50,
        available_days=random.choice(["Mon-Sat", "Mon-Fri", "Mon, Wed, Fri", "Tue-Sun", "Mon-Sat (evening)"]),
        mode=random.choice(["In-person", "Teleconsult", "In-person & Teleconsult", "In-person & Teleconsult"]),
        languages=", ".join(random.sample(["English", "Hindi", "Gujarati", "Marathi", "Tamil", "Telugu", "Kannada", "Bengali"], 2))))
    n += 1

with open(OUT, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
print(f"Wrote {len(rows)} fictional doctors to {OUT}")
