import base64
import hashlib
from typing import List
from cryptography.fernet import Fernet, MultiFernet
from app.core.config import settings

def _derive_fernet_key(seed: str) -> bytes:
    """Derives a deterministic 32-byte urlsafe base64 Fernet key from any string."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)

def _get_multi_fernet() -> MultiFernet:
    """
    Constructs a MultiFernet instance supporting zero-downtime key rotation.
    Primary key is TOKEN_ENCRYPTION_KEY (or fallback to SECRET_KEY).
    Rotation keys can be supplied via comma-separated TOKEN_ROTATION_KEYS.
    """
    primary_seed = settings.TOKEN_ENCRYPTION_KEY or settings.SECRET_KEY
    fernets: List[Fernet] = [Fernet(_derive_fernet_key(primary_seed))]

    if settings.TOKEN_ROTATION_KEYS:
        for rot_seed in settings.TOKEN_ROTATION_KEYS.split(","):
            rot_seed = rot_seed.strip()
            if rot_seed:
                fernets.append(Fernet(_derive_fernet_key(rot_seed)))

    return MultiFernet(fernets)

def encrypt_token(token: str) -> str:
    """Encrypts a sensitive OAuth token (refresh token) at rest."""
    if not token:
        return ""
    mf = _get_multi_fernet()
    encrypted = mf.encrypt(token.encode("utf-8"))
    return encrypted.decode("utf-8")

def decrypt_token(cipher_text: str) -> str:
    """Decrypts a sensitive OAuth token using primary or rotated keys."""
    if not cipher_text:
        return ""
    mf = _get_multi_fernet()
    try:
        decrypted = mf.decrypt(cipher_text.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        # Never log raw cipher or plain token
        raise ValueError("Token decryption failed: key mismatch or corrupted cipher text.")

def rotate_token_cipher(cipher_text: str) -> str:
    """Re-encrypts a cipher text with the current primary key (rotation migration)."""
    if not cipher_text:
        return ""
    mf = _get_multi_fernet()
    try:
        rotated = mf.rotate(cipher_text.encode("utf-8"))
        return rotated.decode("utf-8")
    except Exception:
        raise ValueError("Token re-encryption rotation failed.")
