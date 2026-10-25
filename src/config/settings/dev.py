"""Development settings: your own computer only."""

from .base import *  # noqa: F403

# SECURITY WARNING: this key is for local development only, production reads its own from the environment.
SECRET_KEY = 'django-insecure-)d&sfdgu6c86vrx#*bt*_@w%t9zl!z%))fa22+ln%0n4*ij#c@'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']
