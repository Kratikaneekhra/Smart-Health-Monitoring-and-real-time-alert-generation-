"""One-command launcher:  python run.py   ->  http://127.0.0.1:5000"""
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))


def ensure_ready():
    raw = os.path.join(ROOT, "data", "raw")
    models = os.path.join(ROOT, "models")
    if not os.path.exists(os.path.join(ROOT, "data", "doctors.csv")):
        subprocess.check_call([sys.executable, os.path.join(ROOT, "data", "generate_doctors.py")])
    if not os.path.isdir(raw) or not any(f.endswith(".csv") for f in os.listdir(raw)):
        subprocess.check_call([sys.executable, os.path.join(ROOT, "ml", "generate_demo_data.py")])
    if not os.path.isdir(models) or not any(f.endswith(".joblib") for f in os.listdir(models)):
        print("No trained models found - training now (about a minute)...")
        subprocess.check_call([sys.executable, os.path.join(ROOT, "ml", "train_models.py")])


if __name__ == "__main__":
    ensure_ready()
    from backend.app import app
    port = int(os.environ.get("PORT", 5000))
    print(f"\nSmart Health Monitor running at http://127.0.0.1:{port}\n")
    app.run(host="127.0.0.1", port=port, debug=False)
