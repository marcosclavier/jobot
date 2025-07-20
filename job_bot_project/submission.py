import os
import json
import logging
from datetime import datetime

# Import shared utils from bot.py
from main import load_json_file, save_json_file, load_profile

SUBMISSION_LOG_FILE = 'submission_log.json'
OUTPUT_DIR = 'applications'

# Setup logging (consistent with bot.py)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("job_bot.log"),
                        logging.StreamHandler()
                    ])

def export_for_plugin(item):
    """Export data for Chrome plugin."""
    job_details = item.get('job_details', {})
    materials = item.get('generated_materials', {})
    profile = load_profile()
    
    plugin_data = {
        'profile': profile,
        'materials': materials,
        'job_details': job_details
    }
    
    company = job_details.get('company', {}).get('display_name', 'Unknown').replace(' ', '_').replace('/', '_')
    title = job_details.get('title', 'Unknown').replace(' ', '_').replace('/', '_')
    path = os.path.join(OUTPUT_DIR, f"{company}_{title}_plugin_data.json")
    save_json_file(plugin_data, path)
    logging.info(f"Exported plugin data to {path}")
    return True, f"Data exported for plugin: {path}"

def submit_application(item):
    """Handles submission: Exports data for Chrome plugin."""
    success, message = export_for_plugin(item)
    job_details = item.get('job_details', {})
    if success:
        log_submission(job_details.get('id'), 'success', message)
        return True, message
    else:
        log_submission(job_details.get('id'), 'error', message)
        return False, message

def log_submission(job_id, status, message):
    """Logs submission results to submission_log.json."""
    logs = load_json_file(SUBMISSION_LOG_FILE)
    logs.append({
        'timestamp': datetime.now().isoformat(),
        'job_id': job_id,
        'status': status,
        'message': message
    })
    save_json_file(logs, SUBMISSION_LOG_FILE)