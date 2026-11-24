"""Smart Health Monitor - Flask REST API + static frontend."""
import json
import os
import re
import uuid
from datetime import datetime
from functools import wraps

from flask import Flask, Response, jsonify, request, send_from_directory

from . import db
from .advice import EMERGENCY, URGENCY, advice_for, clinical_flags
from .pdf_report import build_pdf
from .predictor import ModelRegistry, ValidationError
from .recommender import DoctorRecommender
from .schemas import DISEASES, public_schema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = Flask(__name__, static_folder=os.path.join(ROOT, "frontend"), static_url_path="")
db.init()
registry = ModelRegistry()
doctors = DoctorRecommender()
NOTEBOOK = json.load(open(os.path.join(ROOT, "data", "notebook_results.json")))
RANK = {"Low": 1, "Moderate": 2, "High": 3}


# ------------------------------------------------------------------ helpers
def current_user():
    h = request.headers.get("Authorization", "")
    uid = db.read_token(h[7:]) if h.startswith("Bearer ") else None
    return db.get_user(uid) if uid else None


def login_required(fn):
    @wraps(fn)
    def wrapper(*a, **kw):
        u = current_user()
        if not u:
            return jsonify(error="Please sign in to use this feature."), 401
        return fn(u, *a, **kw)
    return wrapper


NOUN = {"diabetes": "diabetes", "heart": "heart disease", "cardio": "cardiovascular disease", "kidney": "kidney disease"}


def join(items):
    items = list(items)
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def overall_summary(results):
    high = [r for r in results if r["risk_level"] == "High"]
    mod = [r for r in results if r["risk_level"] == "Moderate"]
    names = lambda rs: join(NOUN[r["disease"]] for r in rs)
    specs = lambda rs: join(sorted({r["specialty"] for r in rs}))
    if high:
        level = "High"
        headline = f"High risk found for {names(high)}."
        detail = f"{URGENCY['High']} Suggested: {specs(high)}."
        if mod:
            detail += f" Moderate risk was also found for {names(mod)}."
    elif mod:
        level = "Moderate"
        headline = f"Moderate risk found for {names(mod)}."
        detail = f"{URGENCY['Moderate']} Suggested: {specs(mod)}."
    else:
        level = "Low"
        headline = f"All {len(results)} screening{'s' if len(results) > 1 else ''} show low risk."
        detail = URGENCY["Low"]
    return dict(level=level, headline=headline, detail=detail)


def build_report(payload):
    patient = payload.get("patient") or {}
    assessments = payload.get("assessments") or {}
    if not assessments:
        return None, ({"error": "Choose at least one screening and fill in its details."}, 400)
    results, errors = [], {}
    for key, raw in assessments.items():
        if key not in DISEASES or key not in registry.models:
            errors[key] = {"_form": "This screening is not available."}
            continue
        try:
            r = registry.get(key).predict(raw)
        except ValidationError as e:
            errors[key] = e.errors
            continue
        r["flags"] = clinical_flags(key, r["inputs"])
        r["advice"] = advice_for(key, r["risk_level"])
        r["urgency"] = URGENCY[r["risk_level"]]
        # Independent safety observations can override the routine follow-up text,
        # but never alter the ML score or classification.
        critical_kidney_flags = [
            f for f in r["flags"] if key == "kidney" and f["level"] == "high"
            and ("blood pressure" in f["text"].lower() or "blood glucose" in f["text"].lower())
        ]
        if critical_kidney_flags:
            r["urgency"] = "Urgent medical assessment is advised for the separate safety alert(s); do not rely on the kidney model score to determine urgency."
        results.append(r)
    if errors:
        return None, ({"error": "Some values need attention.", "fields": errors}, 422)
    results.sort(key=lambda r: -RANK[r["risk_level"]])
    city = (patient.get("city") or "").strip() or None
    report = dict(
        report_id="HR-" + uuid.uuid4().hex[:8].upper(),
        created=datetime.now().strftime("%d %b %Y, %H:%M"),
        patient=dict(name=(patient.get("name") or "").strip()[:80], city=city or "", mode=patient.get("mode") or ""),
        results=results, overall=overall_summary(results),
        doctor_groups=doctors.recommend(results, city=city, mode=patient.get("mode") or None),
        emergency=EMERGENCY)
    return report, None


# ------------------------------------------------------------------ public API
@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    src = {k: m.meta["data_source"] for k, m in registry.models.items()}
    return jsonify(status="ok", models_ready=registry.ready(), doctors=len(doctors.df), data_source=src)


@app.get("/api/schema")
def schema():
    return jsonify(diseases=public_schema(), cities=doctors.cities(), emergency=EMERGENCY)


@app.post("/api/predict/<key>")
def predict(key):
    if key not in registry.models:
        return jsonify(error="Unknown screening."), 404
    try:
        return jsonify(registry.get(key).predict(request.get_json(force=True, silent=True) or {}))
    except ValidationError as e:
        return jsonify(error="Some values need attention.", fields=e.errors), 422


@app.post("/api/report")
def report():
    rep, err = build_report(request.get_json(force=True, silent=True) or {})
    if err:
        return jsonify(err[0]), err[1]
    u = current_user()
    rep["saved"] = bool(u)
    if u:
        db.save_report(u["id"], rep)
    return jsonify(rep)


@app.post("/api/report/pdf")
def report_pdf():
    rep = request.get_json(force=True, silent=True) or {}
    if not all(k in rep for k in ("report_id", "patient", "overall", "results", "doctor_groups")):
        return jsonify(error="Invalid report."), 400
    rep["report_id"] = re.sub(r"[^A-Za-z0-9-]", "", str(rep["report_id"]))[:20]
    return Response(build_pdf(rep), mimetype="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=health-report-{rep['report_id']}.pdf"})


@app.get("/api/doctors")
def list_doctors():
    a = request.args
    return jsonify(doctors=doctors.search(a.get("specialization"), a.get("city"), a.get("q"), a.get("mode"), a.get("sort", "rating")))


@app.get("/api/models")
def models_info():
    live = {k: {"deployed": m.meta["deployed"], "data_source": m.meta["data_source"], "n_train": m.meta["n_train"],
                "n_test": m.meta["n_test"], "prevalence": m.meta["prevalence"], "trained_at": m.meta["trained_at"],
                "all_models": m.meta["all_models"]} for k, m in registry.models.items()}
    titles = {k: d["title"] for k, d in DISEASES.items()}
    return jsonify(research=NOTEBOOK, live=live, titles=titles)


# ------------------------------------------------------------------ accounts
@app.post("/api/auth/register")
def register():
    d = request.get_json(force=True, silent=True) or {}
    name, email, pw = (d.get("name") or "").strip(), (d.get("email") or "").strip(), d.get("password") or ""
    if len(name) < 2 or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email) or len(pw) < 6:
        return jsonify(error="Enter your name, a valid email and a password of at least 6 characters."), 400
    try:
        uid = db.create_user(name, email, pw)
    except Exception:
        return jsonify(error="An account with this email already exists."), 409
    return jsonify(token=db.make_token(uid), user=db.get_user(uid))


@app.post("/api/auth/login")
def login():
    d = request.get_json(force=True, silent=True) or {}
    u = db.check_login(d.get("email") or "", d.get("password") or "")
    if not u:
        return jsonify(error="Email or password is incorrect."), 401
    return jsonify(token=db.make_token(u["id"]), user=u)


@app.get("/api/auth/me")
@login_required
def me(u):
    return jsonify(user=u)


@app.get("/api/history")
@login_required
def history(u):
    return jsonify(reports=db.list_reports(u["id"]), appointments=db.list_appointments(u["id"]))


@app.get("/api/reports/<rid>")
@login_required
def get_saved(u, rid):
    r = db.get_report(u["id"], rid)
    return (jsonify(r), 200) if r else (jsonify(error="Report not found."), 404)


@app.post("/api/appointments")
@login_required
def book(u):
    d = request.get_json(force=True, silent=True) or {}
    if not all(d.get(k) for k in ("doctor_id", "doctor_name", "preferred_date")):
        return jsonify(error="Choose a preferred date."), 400
    if not doctors.df["doctor_id"].eq(d["doctor_id"]).any():
        return jsonify(error="Unknown doctor."), 404
    row = doctors.df[doctors.df["doctor_id"] == d["doctor_id"]].iloc[0]
    d.update(doctor_name=row["name"], specialization=row["specialization"], hospital=row["hospital"],
             note=str(d.get("note", ""))[:300])
    db.add_appointment(u["id"], d)
    return jsonify(ok=True, message=f"Appointment request sent to {row['name']}. The clinic will confirm the time.")
