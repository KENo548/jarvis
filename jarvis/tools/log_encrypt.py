import os
from cryptography.fernet import Fernet


KEY_PATH = os.path.join(os.path.dirname(__file__), '..', 'secrets', 'llm_logs.key')


def generate_key(path: str = KEY_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    key = Fernet.generate_key()
    with open(path, 'wb') as f:
        f.write(key)
    return key


def load_key(path: str = KEY_PATH):
    with open(path, 'rb') as f:
        return f.read()


def encrypt_bytes(data: bytes, key: bytes):
    f = Fernet(key)
    return f.encrypt(data)


def decrypt_bytes(token: bytes, key: bytes):
    f = Fernet(key)
    return f.decrypt(token)
