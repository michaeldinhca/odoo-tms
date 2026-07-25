from cryptography.fernet import Fernet

from app.core.config import settings


def _get_fernet() -> Fernet:
    try:
        return Fernet(settings.fernet_key.encode())
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "FERNET_KEY is not a valid Fernet key. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; "
            'print(Fernet.generate_key().decode())"'
        ) from exc


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    return _get_fernet().decrypt(ciphertext.encode()).decode()
