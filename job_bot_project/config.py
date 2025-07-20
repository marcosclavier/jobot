# --- Constants ---
PROFILE_FILE = 'profile.json'
SEEN_JOBS_FILE = 'seen_jobs.json'
RECOMMENDED_JOBS_FILE = 'recommended_jobs.json'
SELECTED_JOBS_FILE = 'selected_jobs.json'
GENERATED_MATERIALS_FILE = 'generated_materials.json'
import os

# Security
SECRET_KEY = os.environ.get("SECRET_KEY", "a_very_secret_and_insecure_default_key_for_dev")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Database
MONGO_URI = os.environ.get("MONGO_URI", "mongodb://localhost:27017")

# File System
PROFILE_FILE = "user_profile.json"
EDITED_MATERIALS_FILE = "edited_materials.json"

# Testing
TESTING = os.environ.get("TESTING", "False").lower() == "true"
PROFILE_HASH_FILE = '.profile_hash'
MAX_WORKERS = 5
SCRAPE_TIMEOUT = 30
MAX_PAGES = 3
MAX_DAYS_OLD = 15
