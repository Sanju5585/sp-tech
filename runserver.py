"""
Start SP-Tech Software Solution over HTTPS.

Ports:
    80  HTTP  → redirects to HTTPS
    443 HTTPS (SSL terminator) → Waitress WSGI on 127.0.0.1:8000

Usage (from project root, as Administrator on Windows):
    python runserver.py
    start.bat
"""
import os
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sanjivani.settings")
os.environ.setdefault("PYTHONUNBUFFERED", "1")

if __name__ == "__main__":
    print("SP-Tech Software Solution")
    print("HTTPS production stack: HTTP :80 -> HTTPS :443")
    print("Local: https://127.0.0.1/   Domain: https://www.sanjivanione.com/")
    print("Timetable API starts automatically on http://127.0.0.1:8001")
    runpy.run_path(str(ROOT / "deploy" / "run_https.py"), run_name="__main__")
