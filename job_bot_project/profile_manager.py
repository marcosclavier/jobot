import json
import os
import hashlib
import logging
from .encryption_utils import load_key, encrypt_data, decrypt_data
from .config import PROFILE_FILE, PROFILE_HASH_FILE

def load_profile():
    """
    Loads and decrypts the user profile from PROFILE_FILE.

    Inputs:
        - PROFILE_FILE (str): Path to the encrypted profile file.
        - ENCRYPTION_KEY (str): Encryption key from environment variables.

    Returns:
        dict: The decrypted user profile as a dictionary, or an empty dictionary if not found or on error.
    """
    try:
        with open(PROFILE_FILE, 'rb') as f:
            encrypted_data = f.read()
        if not encrypted_data:
            return {}
        key = load_key()
        decrypted_json = decrypt_data(encrypted_data, key)
        return json.loads(decrypted_json)
    except FileNotFoundError:
        logging.warning(f"Profile file not found at {PROFILE_FILE}. Returning empty profile.")
        return {}
    except Exception as e:
        logging.error(f"Failed to load or decrypt profile: {e}", exc_info=True)
        return {}

def save_profile(profile_data):
    """
    Encrypts and saves the user profile data to PROFILE_FILE.
    Also updates the profile hash after saving.

    Args:
        profile_data (dict): The user profile data to be saved.

    Inputs:
        - profile_data (dict): The profile data to encrypt and save.
        - ENCRYPTION_KEY (str): Encryption key from environment variables.

    Outputs:
        - Writes encrypted data to PROFILE_FILE.
        - Updates PROFILE_HASH_FILE with the new profile hash.

    Returns:
        bool: True if the profile was successfully saved, False otherwise.
    """
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
    """
    Validates that the given profile dictionary contains essential fields.

    Args:
        profile (dict): The user profile dictionary to validate.

    Inputs:
        - profile (dict): The profile data to check.

    Returns:
        bool: True if the profile contains all required fields, False otherwise.
    """
    required_fields = ['skills', 'location']
    missing_fields = [field for field in required_fields if not profile.get(field)]
    if missing_fields:
        logging.warning(f"Profile is incomplete. Missing fields: {', '.join(missing_fields)}.")
        return False
    return True

def get_file_hash(file_path):
    """
    Computes the SHA256 hash of a given file.

    Args:
        file_path (str): The path to the file for which to compute the hash.

    Inputs:
        - file_path (str): Path to the file.

    Returns:
        str or None: The SHA256 hash of the file as a hexadecimal string, or None if the file does not exist.
    """
    if not os.path.exists(file_path):
        return None
    hasher = hashlib.sha256()
    with open(file_path, 'rb') as f:
        buf = f.read()
        hasher.update(buf)
    return hasher.hexdigest()

def has_profile_changed():
    """
    Checks if the profile.json file has changed since the last recorded hash.

    Inputs:
        - PROFILE_FILE (str): Path to the profile file.
        - PROFILE_HASH_FILE (str): Path to the file storing the last profile hash.

    Returns:
        bool: True if the profile has changed or the hash file doesn't exist, False otherwise.
    """
    current_hash = get_file_hash(PROFILE_FILE)
    if not os.path.exists(PROFILE_HASH_FILE):
        logging.info(f"Profile hash file not found at {PROFILE_HASH_FILE}. Assuming profile has changed.")
        return True  # Hash file doesn't exist, assume change

    with open(PROFILE_HASH_FILE, 'r') as f:
        stored_hash = f.read().strip()
    
    return current_hash != stored_hash

def update_profile_hash():
    """
    Updates the stored hash of the profile.json file.

    Inputs:
        - PROFILE_FILE (str): Path to the profile file.

    Outputs:
        - Writes the current profile hash to PROFILE_HASH_FILE.

    Returns:
        None
    """
    current_hash = get_file_hash(PROFILE_FILE)
    if current_hash:
        with open(PROFILE_HASH_FILE, 'w') as f:
            f.write(current_hash)
        logging.info("Updated profile hash.")