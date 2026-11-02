"""Serve disposable Admin previews and their static assets on localhost only."""

import os
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

import django  # noqa: E402

django.setup()
from django.contrib.staticfiles import finders  # noqa: E402


class PreviewHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path_part = unquote(urlsplit(path).path)
        if path_part.startswith("/static/"):
            found = finders.find(path_part.removeprefix("/static/"))
            return str(found or ROOT / ".artifacts" / "missing-static-resource")
        return super().translate_path(path)


if __name__ == "__main__":
    handler = partial(PreviewHandler, directory=str(ROOT / ".artifacts" / "admin-preview"))
    print("Demo-only Admin previews: http://127.0.0.1:8765/index.html", flush=True)
    ThreadingHTTPServer(("127.0.0.1", 8765), handler).serve_forever()
