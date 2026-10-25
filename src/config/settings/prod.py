"""Production settings: every secret comes from environment variables."""

import os

from .base import *  # noqa: F403

DEBUG = False

# Square brackets on purpose: a missing variable must crash startup (fail fast), not run with a blank key.
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

ALLOWED_HOSTS = os.environ['DJANGO_ALLOWED_HOSTS'].split(',')

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
