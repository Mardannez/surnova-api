from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403
from .base import CACHES, DATABASES, SECRET_KEY, env

DEBUG = False
if len(SECRET_KEY) < 50:
    raise ImproperlyConfigured("Production requires a random SECRET_KEY of at least 50 characters.")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production requires PostgreSQL.")
if env.bool("DATABASE_SSL_REQUIRE", default=True):
    DATABASES["default"].setdefault("OPTIONS", {})["sslmode"] = "require"
if CACHES["default"]["BACKEND"] == "django.core.cache.backends.locmem.LocMemCache":
    raise ImproperlyConfigured(
        "Production requires a shared cache for throttling; configure Redis."
    )
if env.bool("DJANGO_TRUST_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
