import os
from cryptography.fernet import Fernet
import logging

def load_key():
    """Loads the encryption key from .env file."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        logging.error("ENCRYPTION_KEY not found in .env file. Generate one with `generate-key`.")
        raise ValueError("Encryption key not found.")
    return key.encode()

def encrypt_data(data, key):
    """Encrypts data using the provided key."""
    f = Fernet(key)
    return f.encrypt(data.encode())

def decrypt_data(encrypted_data, key):
    """Decrypts data using the provided key."""
    f = Fernet(key)
    return f.decrypt(encrypted_data).decode()
