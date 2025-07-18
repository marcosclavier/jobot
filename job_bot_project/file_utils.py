import os
import json
import logging
from cryptography.fernet import Fernet

# --- Constants ---
PROFILE_FILE = 'profile.json'

# --- Encryption ---
def load_key():
    """Loads the encryption key from .env file."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        logging.error("ENCRYPTION_KEY not found in .env file. Generate one with `generate-key`.")
        raise ValueError("Encryption key not found.")
    return key.encode()

def decrypt_data(encrypted_data, key):
    """Decrypts data using the provided key."""
    f = Fernet(key)
    return f.decrypt(encrypted_data).decode()

def load_profile():
    """Loads and decrypts the user profile."""
    try:
        with open(PROFILE_FILE, 'rb') as f:
            encrypted_data = f.read()
        if not encrypted_data:
            return {}
        key = load_key()
        decrypted_json = decrypt_data(encrypted_data, key)
        return json.loads(decrypted_json)
    except FileNotFoundError:
        return {}
    except Exception as e:
        logging.error(f"Failed to load or decrypt profile: {e}", exc_info=True)
        return {}

def load_json_file(file_path):
    """Loads data from a JSON file."""
    if not os.path.exists(file_path):
        return []
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_json_file(data, file_path):
    """Saves data to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
    except IOError as e:
        logging.error(f"Error writing to {file_path}: {e}", exc_info=True)
