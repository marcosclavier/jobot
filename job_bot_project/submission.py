import os
import json
import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import smtplib

# Import shared utils from main.py
from file_utils import load_json_file, save_json_file, load_profile

SUBMISSION_LOG_FILE = 'submission_log.json'
OUTPUT_DIR = 'applications'

# Setup logging (consistent with bot.py)
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("job_bot.log"),
                        logging.StreamHandler()
                    ])

def get_webdriver():
    """Initialize a headless Chrome WebDriver."""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    return webdriver.Chrome(options=options)

def fill_greenhouse_form(driver, profile, materials, files):
    """Tailored form filling for Greenhouse ATS."""
    wait = WebDriverWait(driver, 10)
    
    try:
        # Fill personal info
        wait.until(EC.presence_of_element_located((By.ID, 'first_name'))).send_keys(profile.get('name', '').split()[0])
        driver.find_element(By.ID, 'last_name').send_keys(profile.get('name', '').split()[-1])
        driver.find_element(By.ID, 'email').send_keys(profile.get('contact_info', {}).get('email', ''))
        driver.find_element(By.ID, 'phone').send_keys(profile.get('contact_info', {}).get('phone', ''))
        
        # Upload resume
        resume_input = driver.find_element(By.ID, 'resume')
        resume_input.send_keys(files['resume'])
        
        # Cover letter (if textarea)
        try:
            cover_textarea = driver.find_element(By.ID, 'cover_letter')
            cover_textarea.send_keys(materials['cover_letter'])
        except NoSuchElementException:
            logging.warning("No cover letter field found; skipping.")
        
        # Answer questions (match by labels)
        questions = materials.get('question_answers', [])
        for qa in questions:
            question_text = qa['question'].lower()
            try:
                label = driver.find_element(By.XPATH, f"//label[contains(text(), '{question_text[:50]}')]")
                input_id = label.get_attribute('for')
                driver.find_element(By.ID, input_id).send_keys(qa['answer'])
            except NoSuchElementException:
                logging.warning(f"Question not found: {question_text}")
        
        # Submit
        submit_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[type="submit"]')))
        submit_btn.click()
        
        # Wait for confirmation
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Thank you') or contains(text(), 'submitted')]")))
        return True, "Submission successful via Greenhouse form"
    
    except TimeoutException as e:
        return False, f"Timeout during form filling: {str(e)}"
    except Exception as e:
        return False, f"Error filling Greenhouse form: {str(e)}"

def fill_bamboohr_form(driver, profile, materials, files):
    """Tailored form filling for BambooHR ATS."""
    wait = WebDriverWait(driver, 10)
    
    try:
        # Wait for form to load
        wait.until(EC.presence_of_element_located((By.ID, 'firstName')))
        
        # Parse name
        name_parts = profile.get('name', ' ').split()
        first_name = name_parts[0] if name_parts else ''
        last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''
        
        # Fill personal info
        driver.find_element(By.ID, 'firstName').send_keys(first_name)
        driver.find_element(By.ID, 'lastName').send_keys(last_name)
        driver.find_element(By.ID, 'email').send_keys(profile.get('contact_info', {}).get('email', ''))
        driver.find_element(By.ID, 'phone').send_keys(profile.get('contact_info', {}).get('phone', ''))
        
        # Address fields
        # Assuming profile['location'] is a string like "City, State Zip, Country" or dict; parse accordingly
        location = profile.get('location', '')
        # Simple parse example; adjust based on your profile format
        address_parts = location.split(', ')
        street = address_parts[0] if address_parts else ''
        city = address_parts[1] if len(address_parts) > 1 else ''
        state = address_parts[2] if len(address_parts) > 2 else ''
        zip_code = address_parts[3] if len(address_parts) > 3 else ''
        country = address_parts[4] if len(address_parts) > 4 else 'Canada'  # From job example
        
        driver.find_element(By.ID, 'streetAddress').send_keys(street)
        driver.find_element(By.ID, 'city').send_keys(city)
        driver.find_element(By.ID, 'zip').send_keys(zip_code)
        
        # State/Province select (name="state")
        try:
            state_select_elem = driver.find_element(By.NAME, 'state')
            state_select = Select(state_select_elem)
            state_select.select_by_visible_text(state)  # Or by value if known
        except NoSuchElementException:
            logging.warning("State select not found; skipping.")
        
        # Country select (name="countryId")
        try:
            country_select_elem = driver.find_element(By.NAME, 'countryId')
            country_select = Select(country_select_elem)
            country_select.select_by_visible_text(country)
        except NoSuchElementException:
            logging.warning("Country select not found; skipping.")
        
        # Resume upload: Find the file input
        try:
            resume_input = driver.find_element(By.CSS_SELECTOR, 'input[type="file"][aria-label="file-input"]')
            resume_input.send_keys(files['resume'])
        except NoSuchElementException:
            logging.warning("Resume file input not found; skipping.")
        
        # Date Available: id="dateAvailable", format mm/dd/yyyy
        # Set to current date as example
        current_date = datetime.now().strftime('%m/%d/%Y')
        driver.find_element(By.ID, 'dateAvailable').send_keys(current_date)
        
        # Desired Pay (optional)
        desired_pay = profile.get('salary_range', '')  # Use from profile if available
        driver.find_element(By.ID, 'desiredPay').send_keys(desired_pay)
        
        # Website/Portfolio
        driver.find_element(By.ID, 'websiteUrl').send_keys(profile.get('contact_info', {}).get('linkedin', ''))  # Or separate field
        
        # LinkedIn
        driver.find_element(By.ID, 'linkedinUrl').send_keys(profile.get('contact_info', {}).get('linkedin', ''))
        
        # Answer questions if any (not in provided HTML, but loop similar to Greenhouse)
        questions = materials.get('question_answers', [])
        for qa in questions:
            question_text = qa['question'].lower()
            try:
                label = driver.find_element(By.XPATH, f"//label[contains(text(), '{question_text[:50]}')]")
                input_id = label.get_attribute('for')
                driver.find_element(By.ID, input_id).send_keys(qa['answer'])
            except NoSuchElementException:
                logging.warning(f"Question not found: {question_text}")
        
        # Submit: Find button with text "Submit Application"
        submit_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'Submit Application')]")))
        submit_btn.click()
        
        # Wait for confirmation
        wait.until(EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Thank You') or contains(text(), 'Your application was submitted successfully')]")))
        return True, "Submission successful via BambooHR form"
    
    except TimeoutException as e:
        return False, f"Timeout during form filling: {str(e)}"
    except Exception as e:
        return False, f"Error filling BambooHR form: {str(e)}"

def fill_generic_form(driver, profile, materials, files):
    """Generic form filling for unknown or other ATS."""
    # Similar to above, but with more flexible locators (e.g., name attributes)
    # Implement basic fields; can expand based on testing
    try:
        driver.find_element(By.NAME, 'first_name').send_keys(profile.get('name', '').split()[0])
        # etc.
        return True, "Generic submission attempted"
    except Exception as e:
        return False, f"Generic form filling failed: {str(e)}"

def ats_submit_via_browser(item, files, materials):
    """Submit via browser automation based on ATS platform."""
    job_details = item.get('job_details', {})
    ats_url = job_details.get('ats_url')
    ats_platform = job_details.get('ats_platform', 'Unknown')
    
    if not ats_url:
        return False, "No ATS URL available"
    
    profile = load_profile()  # Load for personal info
    driver = get_webdriver()
    
    try:
        driver.get(ats_url)
        if ats_platform == 'Greenhouse':
            return fill_greenhouse_form(driver, profile, materials, files)
        elif ats_platform == 'BambooHR':
            return fill_bamboohr_form(driver, profile, materials, files)
        elif ats_platform == 'Lever':
            # Add Lever-specific logic (e.g., IDs like 'resume-upload-input')
            return fill_generic_form(driver, profile, materials, files)
        else:
            return fill_generic_form(driver, profile, materials, files)
    finally:
        driver.quit()

def mock_email_submission(item, files):
    """Fallback: Mock email submission with attachments."""
    try:
        msg = MIMEMultipart()
        msg['From'] = os.getenv('SMTP_USER')
        msg['To'] = os.getenv('MOCK_HR_EMAIL', 'mock-hr@example.com')
        job_details = item.get('job_details', {})
        msg['Subject'] = f"Application for {job_details.get('title', 'Unknown')} at {job_details.get('company', {}).get('display_name', 'Unknown')}"

        body = "Please find attached the application materials."
        msg.attach(MIMEText(body, 'plain'))

        for name, path in files.items():
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f"attachment; filename={os.path.basename(path)}")
                    msg.attach(part)

        server = smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT', 587)))
        server.starttls()
        server.login(os.getenv('SMTP_USER'), os.getenv('SMTP_PASS'))
        server.send_message(msg)
        server.quit()

        return True, "Fallback email submission successful"
    except Exception as e:
        return False, str(e)

def submit_application(item):
    """Handles submission: Tries ATS browser automation first, falls back to email."""
    job_details = item.get('job_details', {})
    materials = item.get('generated_materials', {})
    company = job_details.get('company', {}).get('display_name', 'Unknown').replace(' ', '_').replace('/', '_')
    title = job_details.get('title', 'Unknown').replace(' ', '_').replace('/', '_')

    cl_path = os.path.join(OUTPUT_DIR, f"{company}_{title}_CoverLetter.docx")
    res_path = os.path.join(OUTPUT_DIR, f"{company}_{title}_Resume.docx")
    qa_path = os.path.join(OUTPUT_DIR, f"{company}_{title}_Questions.json")

    files = {
        'cover_letter': cl_path,
        'resume': res_path,
    }
    if os.path.exists(qa_path):
        files['questions'] = qa_path

    missing = [name for name, path in files.items() if not os.path.exists(path)]
    if missing:
        return False, f"Missing files: {', '.join(missing)}"

    max_retries = 3
    for attempt in range(max_retries):
        success, message = ats_submit_via_browser(item, files, materials)
        if success:
            log_submission(job_details.get('id'), 'success', message)
            return True, message
        
        logging.warning(f"ATS submission attempt {attempt + 1} failed: {message}")
        time.sleep(2 ** attempt)  # Exponential backoff

    # Fallback to email if ATS fails
    success, message = mock_email_submission(item, files)
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