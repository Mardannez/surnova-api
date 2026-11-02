from .base import *  # noqa: F403
from .base import REST_FRAMEWORK

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {"login": "1000/min", "register": "1000/min", "checkout": "1000/min"},
}  # noqa: F405
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
