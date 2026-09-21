"""
Ensure the School Timetable FastAPI service is running on TIMETABLE_API_PORT (default 8001).

Used by deploy/run_https.py and Django views when an app is opened.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'app' / 'School_timetable' / 'backend'
VENV_DIR = BACKEND / '.venv'
if sys.platform == 'win32':
    VENV_PYTHON = VENV_DIR / 'Scripts' / 'python.exe'
    VENV_PIP = VENV_DIR / 'Scripts' / 'pip.exe'
else:
    VENV_PYTHON = VENV_DIR / 'bin' / 'python'
    VENV_PIP = VENV_DIR / 'bin' / 'pip'

HOST = os.getenv('TIMETABLE_API_HOST', '127.0.0.1')
PORT = int(os.getenv('TIMETABLE_API_PORT', os.getenv('INTERNAL_TIMETABLE_PORT', '8001')))
HEALTH_URL = f'http://{HOST}:{PORT}/api/health'
_LOG = BACKEND / 'timetable-service.log'
_PROC: subprocess.Popen | None = None


def is_running(timeout: float = 1.5) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as resp:
            return 200 <= resp.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def ensure_venv() -> Path:
    if not VENV_PYTHON.is_file():
        print(f'[timetable] Creating venv at {VENV_DIR} ...')
        subprocess.check_call([sys.executable, '-m', 'venv', str(VENV_DIR)])
        subprocess.check_call(
            [str(VENV_PIP), 'install', '--upgrade', 'pip'],
            cwd=str(BACKEND),
        )
        print('[timetable] Installing backend requirements (first run may take a few minutes)...')
        subprocess.check_call(
            [str(VENV_PIP), 'install', '-r', 'requirements.txt'],
            cwd=str(BACKEND),
        )
    return VENV_PYTHON


def start_process() -> subprocess.Popen:
    global _PROC
    python = ensure_venv()
    env = os.environ.copy()
    env.setdefault('PORTAL_SSO_SECRET', os.getenv('PORTAL_SSO_SECRET', 'sanjivani-portal-sso-change-me'))
    env.setdefault('BOOTSTRAP_SUPER_USERNAME', 'superAdmin')
    env.setdefault('BOOTSTRAP_SUPER_PASSWORD', 'sanjeev@5585')
    env.setdefault('APP_ENV', 'development')
    # Allow SSO / embeds from the portal domains
    env.setdefault(
        'CORS_ORIGINS',
        'http://127.0.0.1:8000,http://localhost:8000,'
        'https://127.0.0.1,https://localhost,'
        'https://sanjivanione.com,https://www.sanjivanione.com,'
        'https://sanjivanione.in,https://www.sanjivanione.in,'
        'https://sanjivani.com,https://www.sanjivani.com',
    )
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(_LOG, 'a', encoding='utf-8')
    creationflags = 0
    if sys.platform == 'win32':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    _PROC = subprocess.Popen(
        [
            str(python),
            '-m',
            'uvicorn',
            'app.main:app',
            '--host',
            HOST,
            '--port',
            str(PORT),
            '--log-level',
            'info',
        ],
        cwd=str(BACKEND),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        creationflags=creationflags,
    )
    print(f'[timetable] Started uvicorn pid={_PROC.pid} on http://{HOST}:{PORT}')
    return _PROC


def ensure_running(wait_seconds: float = 90.0) -> bool:
    """Start the timetable API if needed. Returns True when healthy."""
    if is_running():
        return True
    try:
        start_process()
    except Exception as exc:
        print(f'[timetable] Failed to start: {exc}')
        return False
    deadline = time.time() + wait_seconds
    while time.time() < deadline:
        if is_running(timeout=2.0):
            print('[timetable] Health check OK')
            return True
        if _PROC is not None and _PROC.poll() is not None:
            print(f'[timetable] Process exited early (code {_PROC.returncode}). See {_LOG}')
            return False
        time.sleep(0.8)
    print(f'[timetable] Timed out waiting for {HEALTH_URL}. See {_LOG}')
    return False


if __name__ == '__main__':
    ok = ensure_running()
    sys.exit(0 if ok else 1)
