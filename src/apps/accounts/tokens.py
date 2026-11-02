"""Sign and read JWTs. The signature is what makes a token proof: nobody without JWT_SECRET_KEY can change what it says."""

import hashlib
import hmac
import time
import uuid
from datetime import UTC, datetime, timedelta

import jwt
from django.core.exceptions import ImproperlyConfigured

from config.env import env
from core.limits import ACCESS_TOKEN_MINUTES, REFRESH_TOKEN_DAYS
from infra.cache import token_denylist

ALGORITHM = "HS256"
ISSUER = "opspilot"
ACCESS = "access"
REFRESH = "refresh"
ROLE_CUSTOMER = "customer"
ROLE_STAFF = "staff"
ACCESS_TOKEN_SECONDS = ACCESS_TOKEN_MINUTES * 60


def _secret() -> str:
    if env.jwt_secret_key is None:
        raise ImproperlyConfigured("JWT_SECRET_KEY is not set")
    return env.jwt_secret_key.get_secret_value()


def mint(claims: dict, token_type: str) -> str:
    now = datetime.now(UTC)
    lifetime = timedelta(minutes=ACCESS_TOKEN_MINUTES) if token_type == ACCESS else timedelta(days=REFRESH_TOKEN_DAYS)
    payload = {**claims, "type": token_type, "iss": ISSUER, "iat": now, "exp": now + lifetime, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def read(token: str, token_type: str) -> dict | None:
    """The claims of a valid token of this type, else None."""
    try:
        # A fixed algorithm list: the token's own header must never choose how it is checked ("alg: none" attack).
        claims = jwt.decode(
            token, _secret(), algorithms=[ALGORITHM], issuer=ISSUER, options={"require": ["exp", "iat", "sub", "jti"]}
        )
    except jwt.PyJWTError:
        return None
    if claims.get("type") != token_type or token_denylist.is_revoked(claims["jti"]):
        return None
    return claims


def revoke(claims: dict) -> None:
    token_denylist.revoke(claims["jti"], int(claims["exp"] - time.time()))


def password_fingerprint(password_hash: str) -> str:
    """Goes inside the token, so changing a password ends every session; keyed because anyone can read a token's payload."""
    return hmac.new(_secret().encode(), password_hash.encode(), hashlib.sha256).hexdigest()[:16]
