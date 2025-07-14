import json
import os
import hashlib
import logging
from .encryption_utils import load_key, encrypt_data, decrypt_data
from .config import PROFILE_FILE, PROFILE_HASH_FILE

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

def save_profile(profile_data):
    """Encrypts and saves the user profile. Returns True on success, False on failure."""
    try:
        key = load_key()
        profile_json = json.dumps(profile_data, indent=4)
        encrypted_data = encrypt_data(profile_json, key)
        with open(PROFILE_FILE, 'wb') as f:
            f.write(encrypted_data)
        logging.info(f"Profile successfully encrypted and saved to {PROFILE_FILE}.")
        update_profile_hash()
        return True
    except (IOError, ValueError) as e:
        logging.error(f"Error saving profile: {e}", exc_info=True)
        return False

def validate_profile(profile):
    """Validates that the profile has essential fields."""
    required_fields = ['skills', 'location']
    missing_fields = [field for field in required_fields if not profile.get(field)]
    if missing_fields:
        logging.warning(f"Profile is incomplete. Missing fields: {', '.join(missing_fields)}.")
        return False
    return True

def get_file_hash(file_path):
    """Computes the SHA256 hash of a file."""
    if not os.path.exists(file_path):
        return None
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def has_profile_changed():
    """Checks if profile.json has changed since the last run."""
    current_hash = get_file_hash(PROFILE_FILE)
    if not os.path.exists(PROFILE_HASH_FILE):
        return True  # Hash file doesn't exist, assume change

    with open(PROFILE_HASH_FILE, 'r') as f:
        stored_hash = f.read().strip()
    
    return current_hash != stored_hash

def update_profile_hash():
    """Updates the stored hash of the profile."""
    current_hash = get_file_hash(PROFILE_FILE)
    if current_hash:
        with open(PROFILE_HASH_FILE, 'w') as f:
            f.write(current_hash)
        logging.info("Updated profile hash.")
