import hashlib
import secrets

_KEY_PREFIX = "rk_"
_TOKEN_BYTES = 32
_DISPLAY_PREFIX_LENGTH = 8


def generate_raw_key() -> str:
    """A new high-entropy API key, e.g. 'rk_AbCdEfGh...'. Returned only
    once by the caller that mints it - never stored anywhere in plaintext,
    only its hash (see `hash_key`)."""
    return f"{_KEY_PREFIX}{secrets.token_urlsafe(_TOKEN_BYTES)}"


def hash_key(raw_key: str) -> str:
    """SHA-256 hex digest of a raw key, for storage/lookup. No per-key salt
    needed - the token's own 256 bits of entropy already makes a rainbow-
    table or brute-force attack infeasible without one, the same reasoning
    Stripe/GitHub PATs use for their own high-entropy tokens."""
    return hashlib.sha256(raw_key.encode()).hexdigest()


def display_prefix(raw_key: str) -> str:
    """The first few characters of a raw key - safe to store/display for
    telling keys apart (e.g. after rotation) without ever exposing enough
    of the key to reconstruct or guess it."""
    return raw_key[:_DISPLAY_PREFIX_LENGTH]
