import base64
import hashlib
from cryptography.fernet import Fernet
from app.core.config import settings

def _get_fernet_key() -> bytes:
    """Derives a deterministic, 32-byte urlsafe base64 Fernet key."""
    seed = settings.NOTE_ENCRYPTION_KEY or settings.SECRET_KEY
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)

def encrypt_note(plaintext: str) -> str:
    """Encrypts private note text using AES/Fernet."""
    if not plaintext:
        return ""
    key = _get_fernet_key()
    f = Fernet(key)
    encrypted_bytes = f.encrypt(plaintext.encode("utf-8"))
    return encrypted_bytes.decode("utf-8")

def decrypt_note(ciphertext: str) -> str:
    """Decrypts private note text using AES/Fernet."""
    if not ciphertext:
        return ""
    key = _get_fernet_key()
    f = Fernet(key)
    try:
        decrypted_bytes = f.decrypt(ciphertext.encode("utf-8"))
        return decrypted_bytes.decode("utf-8")
    except Exception:
        return "[Decryption Error - Key Mismatch]"
