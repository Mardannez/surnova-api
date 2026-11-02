"""Create a private local .env once; never echo generated secrets."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / ".env"
if target.exists():
    raise SystemExit(".env ya existe; no se modificó.")
text = (root / ".env.example").read_text(encoding="utf-8")
password = secrets.token_urlsafe(32)
text = text.replace("DJANGO_SECRET_KEY=\n", f"DJANGO_SECRET_KEY={secrets.token_urlsafe(64)}\n")
text = text.replace("POSTGRES_PASSWORD=\n", f"POSTGRES_PASSWORD={password}\n")
text = text.replace("surnova:CHANGE_ME@", f"surnova:{password}@")
target.write_text(text, encoding="utf-8")
print(".env creado con secretos locales aleatorios. No lo publiques.")
