"""SQLite storage + password hashing + signed tokens (standard library only)."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "instance", "health.db")
SECRET_PATH = os.path.join(ROOT, "instance", ".secret")
TOKEN_TTL = 7 * 24 * 3600

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
if not os.path.exists(SECRET_PATH):
    open(SECRET_PATH, "w").write(secrets.token_hex(32))
SECRET = open(SECRET_PATH).read().strip().encode()


def conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL, pw_hash TEXT NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS reports(
            id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, created TEXT DEFAULT CURRENT_TIMESTAMP,
            overall TEXT, summary TEXT, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS appointments(
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, doctor_id TEXT, doctor_name TEXT,
            specialization TEXT, hospital TEXT, preferred_date TEXT, note TEXT, report_id TEXT,
            status TEXT DEFAULT 'Requested', created TEXT DEFAULT CURRENT_TIMESTAMP);
        """)


# ------------------------------------------------------------------ users and tokens
def _hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def create_user(name, email, password):
    salt = secrets.token_hex(16)
    with conn() as c:
        cur = c.execute("INSERT INTO users(name,email,salt,pw_hash) VALUES(?,?,?,?)",
                        (name, email.lower(), salt, _hash(password, salt)))
        return cur.lastrowid


def check_login(email, password):
    with conn() as c:
        u = c.execute("SELECT * FROM users WHERE email=?", (email.lower(),)).fetchone()
    if u and hmac.compare_digest(u["pw_hash"], _hash(password, u["salt"])):
        return dict(id=u["id"], name=u["name"], email=u["email"])
    return None


def get_user(uid):
    with conn() as c:
        u = c.execute("SELECT id,name,email FROM users WHERE id=?", (uid,)).fetchone()
    return dict(u) if u else None


def make_token(uid):
    body = base64.urlsafe_b64encode(f"{uid}:{int(time.time()) + TOKEN_TTL}".encode()).decode()
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def read_token(token):
    try:
        body, sig = token.split(".")
        good = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, good):
            return None
        uid, exp = base64.urlsafe_b64decode(body).decode().split(":")
        return int(uid) if int(exp) > time.time() else None
    except Exception:
        return None


# ------------------------------------------------------------------ reports and appointments
def save_report(uid, report):
    rid = report["report_id"]
    with conn() as c:
        c.execute("INSERT OR REPLACE INTO reports(id,user_id,overall,summary,payload) VALUES(?,?,?,?,?)",
                  (rid, uid, report["overall"]["level"], report["overall"]["headline"], json.dumps(report)))


def list_reports(uid):
    with conn() as c:
        rows = c.execute("SELECT id,created,overall,summary,payload FROM reports WHERE user_id=? ORDER BY created DESC", (uid,)).fetchall()
    return [dict(id=r["id"], created=r["created"], overall=r["overall"], summary=r["summary"],
                 diseases=[x["title"] for x in json.loads(r["payload"])["results"]]) for r in rows]


def get_report(uid, rid):
    with conn() as c:
        r = c.execute("SELECT payload FROM reports WHERE id=? AND user_id=?", (rid, uid)).fetchone()
    return json.loads(r["payload"]) if r else None


def add_appointment(uid, d):
    with conn() as c:
        c.execute("""INSERT INTO appointments(user_id,doctor_id,doctor_name,specialization,hospital,preferred_date,note,report_id)
                     VALUES(?,?,?,?,?,?,?,?)""", (uid, d["doctor_id"], d["doctor_name"], d["specialization"], d["hospital"],
                                                  d["preferred_date"], d.get("note", ""), d.get("report_id")))


def list_appointments(uid):
    with conn() as c:
        return [dict(r) for r in c.execute("SELECT * FROM appointments WHERE user_id=? ORDER BY created DESC", (uid,))]
