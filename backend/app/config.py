import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


def _load_env_file(path: Path) -> None:
    """Baca backend/.env (KEY=VALUE per baris) tanpa menimpa variabel yang sudah ada."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip().strip('"').strip("'")
        if value:
            os.environ.setdefault(key.strip(), value)


_load_env_file(BACKEND_DIR / ".env")

DATABASE_URL = os.getenv("JUALANS_DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'jualans.db'}")
FRONTEND_FILE = ROOT_DIR / "index.html"
AI_MODEL = os.getenv("JUALANS_AI_MODEL", "claude-opus-5-5")
DEMO_ENABLED = os.getenv("JUALANS_DEMO", "1") == "1"

SESSION_DAYS = 30          # lama sesi login
HISTORY_DAYS = 90          # riwayat transaksi yang dikirim ke aplikasi: 3 bulan terakhir
MAX_UPLOAD_BYTES = 8 * 1024 * 1024
