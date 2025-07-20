import os
import json
import logging
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from dotenv import load_dotenv
import re
from urllib.parse import urlencode, quote

# Custom quoting function to ensure spaces are %20
def quote_plus_to_percent_20(s, safe='/'):
    return quote(s, safe=safe).replace('+', '%20')

load_dotenv() # Load environment variables here

# --- Constants (from cli-based-tool/job_bot_project/config.py) ---
MAX_WORKERS = 5
SCRAPE_TIMEOUT = 30
MAX_PAGES = 3
MAX_DAYS_OLD = 15

# --- API Clients (adapted from cli-based-tool/job_bot_project/api_clients.py) ---
def scrape_full_description(job):
    """
    Scrapes the full job description from the redirect URL provided in the job data.
    Uses requests with retries and BeautifulSoup for parsing.
    """
    redirect_url = job.get('redirect_url')
    original_description = job.get('description', '')

    if not redirect_url:
        job['full_description'] = original_description
        return job

    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    session.mount('http://', adapter)

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1', # Do Not Track
            'Upgrade-Insecure-Requests': '1'
        }
        page_response = session.get(redirect_url, headers=headers, timeout=SCRAPE_TIMEOUT)
        page_response.raise_for_status()
        soup = BeautifulSoup(page_response.text, 'html.parser')
        
        description_div = soup.find('section', class_='adp-body') or soup.find('div', class_='job-description')
        job['full_description'] = description_div.get_text(separator='\n', strip=True) if description_div else original_description
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch {redirect_url}: {e}", exc_info=True)
        job['full_description'] = original_description
        
    return job

def fetch_adzuna_jobs(profile, primary_keyword, secondary_keywords):
    """
    Fetches job listings from the Adzuna API.
    """
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    logging.info(f"Adzuna API credentials being used: APP_ID={app_id}, APP_KEY={app_key}")

    if not app_id or not app_key:
        logging.error(f"Adzuna API credentials not found. APP_ID: {app_id}, APP_KEY: {app_key}")
        return []

    # Determine country code from profile location
    location_str = profile.get('location', 'remote').lower()
    country_code = 'us' # Default to US
    if 'canada' in location_str or 'ca' in location_str or 'calgary' in location_str or 'toronto' in location_str or 'montreal' in location_str or 'vancouver' in location_str:
        country_code = 'ca'
    # Add more country mappings as needed

    base_url = f"https://api.adzuna.com/v1/api/jobs/{country_code}/search"
    
    all_jobs = []
    for page in range(1, MAX_PAGES + 1):
        try:
            # Prepare parameters as a list of tuples for manual encoding
            params_to_encode = [
                ('app_id', app_id),
                ('app_key', app_key),
                ('results_per_page', 50),
                ('what', primary_keyword),
                ('what_or', ' '.join(secondary_keywords)), # This value will be manually encoded
                ('sort_by', 'date'),
                ('max_days_old', MAX_DAYS_OLD),
                ('page', page) # Page parameter is also part of the query string
            ]

            # Manually build the query string to ensure %20 for spaces
            encoded_params = []
            for key, value in params_to_encode:
                # Special handling for 'what_or' to force %20
                if key == 'what_or':
                    encoded_value = quote(str(value), safe='')
                else:
                    encoded_value = quote(str(value))
                encoded_params.append(f"{key}={encoded_value}")
            
            query_string = "&".join(encoded_params)
            request_url = f"{base_url}/{page}?{query_string}"

            logging.info(f"Requesting Adzuna URL: {request_url}")
            response = requests.get(request_url)
            response.raise_for_status()
            data = response.get('results', [])
            all_jobs.extend(data)
            if len(data) < 50:
                break
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching from Adzuna on page {page}: {e}", exc_info=True)
            if hasattr(e, 'response') and e.response is not None:
                logging.error(f"Adzuna API raw response: {e.response.text}")
            break
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error from Adzuna on page {page}: {e}", exc_info=True)
            if hasattr(response, 'text'):
                logging.error(f"Adzuna API raw response (JSONDecodeError): {response.text}")
            break

    return all_jobs

def fetch_indeed_jobs(profile, keywords):
    """
    Fetches job listings from the Indeed API.
    """
    api_key = os.getenv("INDEED_API_KEY")
    logging.info(f"Indeed API key being used: {api_key}")
    if not api_key:
        logging.warning("Indeed API key not found, skipping Indeed search.")
        return []

    base_url = "https://api.indeed.com/ads/apisearch"
    params = {
        "publisher": api_key,
        "q": ' '.join(keywords),
        "l": profile.get('location', 'remote'),
        "sort": "date",
        "limit": 50,
        "v": "2",
        "format": "json",
        "jt": profile.get('work_type', 'fulltime'),
    }

    all_jobs = []
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)

    try:
        response = session.get(base_url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        for item in data.get('results', []):
            all_jobs.append({
                'id': item.get('jobkey'),
                'title': item.get('jobtitle'),
                'description': item.get('snippet'),
                'redirect_url': item.get('url'),
                'company': {'display_name': item.get('company')}
            })
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        logging.error(f"Error fetching from Indeed: {e}", exc_info=True)

    return all_jobs

# --- AI-Powered Content Generation (adapted from cli-based-tool/job_bot_project/gemini_services.py) ---
def expand_keywords_with_gemini(base_keywords):
    """Expands a list of keywords using Gemini for better search results."""
    logging.info("Calling Gemini to expand keywords...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Given the following list of skills, generate a list of 20-30 related and synonymous keywords to improve job search results.
        Return only a comma-separated list of keywords.

        Skills: {', '.join(base_keywords)}
        """
        response = model.generate_content(prompt)
        expanded_keywords = [k.strip() for k in response.text.split(',')]
        logging.info("Successfully expanded keywords with Gemini.")
        return list(set(base_keywords + expanded_keywords)) # Combine and remove duplicates
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded: {e}", exc_info=True)
        return base_keywords
    except Exception as e:
        logging.error(f"Error expanding keywords with Gemini: {e}", exc_info=True)
        return base_keywords # Fallback to original keywords

def evaluate_job_fit(job, user_profile):
    """Evaluates job fit using Gemini and calculates skill match."""
    job_description = job.get('full_description', job.get('description', ''))
    user_skills = set(skill.lower() for skill in user_profile.get('skills', []))
    
    found_skills = {skill for skill in user_skills if skill in job_description.lower()}
    skill_match_percentage = (len(found_skills) / len(user_skills) * 100) if user_skills else 0

    logging.info(f"Calling Gemini to evaluate job fit for: {job.get('title', '')}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        # Sanitize profile for Gemini to prevent personal info duplication
        sanitized_profile = user_profile.copy()
        if '_id' in sanitized_profile:
            sanitized_profile['_id'] = str(sanitized_profile['_id'])
        sanitized_profile.pop('name', None)
        sanitized_profile.pop('contact_info', None)
        sanitized_profile.pop('location', None)

        prompt = f"""
        User Profile: {json.dumps(sanitized_profile, indent=2)}
        Job Description: {job_description}

        Based on the user profile and job description, perform the following tasks:
        1. Rate the job fit on a scale of 1-10.
        2. Provide a brief explanation for the rating.
        3. Write a concise one-paragraph summary of the job role and its key responsibilities.

        Return a JSON object with the keys: "fit_score", "explanation", and "summary".
        Example: {{"fit_score": 8, "explanation": "The role aligns well...", "summary": "This is a software engineering role..."}}
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        evaluation = json.loads(cleaned_response)
        
        evaluation['skill_match_percentage'] = round(skill_match_percentage, 2)
        evaluation['matched_skills'] = list(found_skills)
        
        logging.info(f"Successfully evaluated job fit for: {job.get('title', '')}")
        return evaluation
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded while evaluating job fit: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Error evaluating job fit with Gemini: {e}", exc_info=True)
        return None

# --- Job Matching Orchestration ---
async def run_job_matching_for_user(user_id, profiles_collection, seen_jobs_collection, recommended_jobs_collection):
    logging.info(f"Starting job matching for user: {user_id}")
    
    profile = await profiles_collection.find_one({"user_id": user_id})
    if not profile:
        logging.warning(f"No profile found for user {user_id}. Skipping job matching.")
        return

    logging.info(f"User profile for job matching: {profile}")

    # Load seen job IDs for this user
    seen_jobs_doc = await seen_jobs_collection.find_one({"user_id": user_id})
    seen_job_ids = seen_jobs_doc.get("job_ids", []) if seen_jobs_doc else []

    all_skills = profile.get('enhanced_skills', [])
    suggested_keywords = profile.get('suggested_keywords', [])

    # Function to clean and split skill strings into individual keywords
    def clean_keywords(skill_list):
        cleaned_words = []
        for phrase in skill_list:
            # Replace non-alphanumeric characters (except spaces) with spaces
            processed_phrase = re.sub(r'[^a-zA-Z0-9\s]', ' ', phrase)
            # Split by spaces and filter out short/common words
            words = [word.strip().lower() for word in processed_phrase.split() if len(word.strip()) > 2 and word.lower() not in ['the', 'and', 'for', 'with', 'from', 'to', 'in', 'of', 'a', 'an', 'or', 'is', 'are', 'be', 'has', 'have', 'had', 'do', 'does', 'did', 'not', 'on', 'at', 'by', 'as', 'if', 'it', 'its', 'that', 'this', 'these', 'those', 'can', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'any', 'are', 'aren', 'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'cannot', 'could', 'did', 'do', 'does', 'doing', 'don', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'has', 'have', 'having', 'he', 'her', 'here', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'i', 'if', 'in', 'into', 'is', 'isn', 'it', 'its', 'itself', 'just', 'll', 'm', 'ma', 'me', 'more', 'most', 'my', 'myself', 'no', 'nor', 'not', 'now', 'o', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 're', 's', 'same', 'she', 'should', 'so', 'some', 'such', 't', 'than', 'that', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 'these', 'they', 'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 've', 'very', 'was', 'we', 'were', 'what', 'when', 'where', 'which', 'while', 'who', 'whom', 'why', 'will', 'with', 'won', 'y', 'you', 'your', 'yours', 'yourself', 'yourselves']]
            cleaned_words.extend(words)
        return list(set(cleaned_words)) # Remove duplicates

    processed_skills = clean_keywords(all_skills)
    processed_suggested_keywords = clean_keywords(suggested_keywords)

    # Combine and ensure uniqueness
    combined_keywords = list(set(processed_skills + processed_suggested_keywords))

    # Select primary keyword (first non-empty, cleaned keyword)
    primary_keyword = ''
    if combined_keywords:
        primary_keyword = combined_keywords.pop(0) # Use and remove from list

    secondary_keywords = combined_keywords # Remaining keywords are secondary

    # Limit the length of secondary keywords for the 'what_or' parameter
    safe_secondary_keywords = []
    current_length = 0
    # Adzuna 'what_or' parameter has a limit, typically around 512 characters.
    # Let's be conservative and aim for less.
    MAX_WHAT_OR_LENGTH = 100 # Reduced for testing
    for keyword in secondary_keywords:
        if current_length + len(keyword) + 1 > MAX_WHAT_OR_LENGTH: # +1 for space
            break
        safe_secondary_keywords.append(keyword)
        current_length += len(keyword) + 1

    logging.info(f"Primary keyword: '{primary_keyword}'. Using {len(safe_secondary_keywords)} secondary keywords: {safe_secondary_keywords}")

    logging.info(f"Primary keyword for Adzuna: '{primary_keyword}'")
    logging.info(f"Secondary keywords for Adzuna (safe): {safe_secondary_keywords}")

    adzuna_jobs = fetch_adzuna_jobs(profile, primary_keyword, safe_secondary_keywords)
    indeed_keywords = [primary_keyword] + safe_secondary_keywords
    indeed_jobs = fetch_indeed_jobs(profile, indeed_keywords)
    all_jobs = adzuna_jobs + indeed_jobs

    if all_jobs:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Scrape full descriptions in parallel
            future_to_job = {executor.submit(scrape_full_description, job): job for job in all_jobs}
            scraped_jobs = []
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    scraped_jobs.append(future.result())
                except Exception as exc:
                    logging.error(f'{job.get("redirect_url")} generated an exception: {exc}')

        new_jobs = [job for job in scraped_jobs if job.get('id') and job.get('id') not in seen_job_ids]
        if new_jobs:
            logging.info(f"Found {len(new_jobs)} new jobs to evaluate for user {user_id}.")
            for job in new_jobs:
                title = job.get('title', '')
                company = job.get('company', {}).get('display_name', '')
                logging.info(f"--- Evaluating: {title} at {company} for user {user_id} ---")
                
                evaluation = evaluate_job_fit(job, profile)
                if not evaluation:
                    logging.error(f"Could not evaluate job: {title} for user {user_id}")
                    continue

                fit_score = evaluation.get('fit_score', 0)
                logging.info(f"  - Fit Score: {fit_score}/10")
                logging.info(f"  - Skill Match: {evaluation.get('skill_match_percentage')}% ")

                if fit_score >= 7:
                    logging.info(f"  - Recommendation: Saving job - {title} for user {user_id}")
                    # Save recommended job to MongoDB
                    await recommended_jobs_collection.insert_one({
                        "user_id": user_id,
                        "job_id": job['id'],
                        "job_details": job,
                        "evaluation": evaluation,
                        "timestamp": datetime.utcnow()
                    })
                else:
                    logging.warning(f"  - Recommendation: Skipping job due to low fit score for user {user_id}.")
            
            # Update seen jobs for this user
            newly_seen_ids = [job['id'] for job in new_jobs if job.get('id')]
            await seen_jobs_collection.update_one(
                {"user_id": user_id},
                {"$addToSet": {"job_ids": {"$each": newly_seen_ids}}},
                upsert=True
            )
        else:
            logging.info(f"No new jobs found for user {user_id}.")
    else:
        logging.warning(f"No jobs found from any source for user {user_id}.")

    logging.info(f"--- Job search finished for user {user_id} ---")

async def run_job_matching_for_all_users(users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection):
    logging.info("Starting periodic job matching for all users.")
    async for user in users_collection.find({}):
        user_id = user["_id"]
        await run_job_matching_for_user(user_id, profiles_collection, seen_jobs_collection, recommended_jobs_collection)
    logging.info("Finished periodic job matching for all users.")
