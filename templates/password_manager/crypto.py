import os
import base64
import secrets
import string
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

MASTER_PASSWORD = os.environ.get('PASSWORD_MANAGER_KEY', 'default-key-change-me!')
SALT = os.environ.get('PASSWORD_MANAGER_SALT', 'salt_1234567890').encode()

def _derive_key(password: str = MASTER_PASSWORD, salt: bytes = SALT) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    return kdf.derive(password.encode())

def encrypt_password(plain: str) -> str:
    if not plain:
        return ''
    key = _derive_key()
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    padded = plain.encode() + b'\x00' * (16 - len(plain) % 16)
    encrypted = encryptor.update(padded) + encryptor.finalize()
    return base64.b64encode(iv + encrypted).decode()

def decrypt_password(encrypted: str) -> str:
    if not encrypted:
        return ''
    key = _derive_key()
    raw = base64.b64decode(encrypted)
    iv = raw[:16]
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(raw[16:]) + decryptor.finalize()
    return decrypted.rstrip(b'\x00').decode()

def generate_password(length: int = 16, use_uppercase: bool = True,
                      use_digits: bool = True, use_symbols: bool = True) -> str:
    chars = string.ascii_lowercase
    if use_uppercase:
        chars += string.ascii_uppercase
    if use_digits:
        chars += string.digits
    if use_symbols:
        chars += '!@#$%^&*()_+-='
    return ''.join(secrets.choice(chars) for _ in range(length))