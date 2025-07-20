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
from collections import Counter
from datetime import datetime

from .gemini_services import extract_keywords_from_job_description, evaluate_job_fit

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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1', # Do Not Track
            'Upgrade-Insecure-Requests': '1',
            'Connection': 'keep-alive',
            'Sec-Ch-Ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Linux"',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
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
    Fetches job listings from the Adzuna API using a primary and secondary keywords.
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
                ('what_or', ' '.join(secondary_keywords)),
                ('sort_by', 'date'),
                ('max_days_old', MAX_DAYS_OLD)
            ]

            # Manually build the query string to ensure %20 for spaces
            encoded_params = []
            for key, value in params_to_encode:
                encoded_value = quote(str(value), safe='')
                encoded_params.append(f"{key}={encoded_value}")
            
            query_string = "&".join(encoded_params)
            request_url = f"{base_url}/{page}?{query_string}"

            logging.info(f"Requesting Adzuna URL: {request_url}")
            response = requests.get(request_url)
            response.raise_for_status()
            data = response.json().get('results', []) # Access 'results' key
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
    Fetches job listings from the Indeed API using a single query string.
    """
    api_key = os.getenv("INDEED_API_KEY")
    logging.info(f"Indeed API key being used: {api_key}")
    if not api_key:
        logging.warning("Indeed API key not found, skipping Indeed search.")
        return []

    base_url = "https://api.indeed.com/ads/apisearch"
    params = {
        "publisher": api_key,
        "q": ' '.join(keywords), # Use the combined query here
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


# --- Job Matching Orchestration ---
async def run_job_matching_for_user(user_id, profiles_collection, seen_jobs_collection, recommended_jobs_collection, saved_jobs_collection):
    logging.info(f"Starting job matching for user: {user_id}")
    
    profile = await profiles_collection.find_one({"user_id": user_id})
    if not profile:
        logging.warning(f"No profile found for user {user_id}. Skipping job matching.")
        return

    logging.info(f"User profile for job matching: {profile}")

    # Load seen job IDs for this user
    seen_jobs_doc = await seen_jobs_collection.find_one({"user_id": user_id})
    seen_job_ids = seen_jobs_doc.get("job_ids", []) if seen_jobs_doc else []

    

    async def get_user_refined_search_keywords(user_id: str) -> list[str]:
        """
        Aggregates keywords from all jobs saved by the user.
        """
        saved_jobs_cursor = saved_jobs_collection.find({"user_id": user_id})
        all_keywords: list[str] = []
        async for job in saved_jobs_cursor:
            if "extracted_keywords" in job.get("job_details", {}):
                all_keywords.extend(job["job_details"]["extracted_keywords"])
            elif "full_description" in job.get("job_details", {}):
                extracted = extract_keywords_from_job_description(job["job_details"]["full_description"])
                all_keywords.extend(extracted)
                # Optionally, update the job document with extracted keywords for caching
                await saved_jobs_collection.update_one(
                    {"_id": job["_id"]},
                    {"$set": {"job_details.extracted_keywords": extracted}}
                )

        # Aggregate and filter keywords (e.g., top N most frequent, unique)
        keyword_counts = Counter(all_keywords)
        # Example: get top 10 keywords
        top_keywords = [kw for kw, count in keyword_counts.most_common(10)]

        return top_keywords

    # Get keywords from both profile and saved jobs
    profile_keywords = profile.get("enhanced_skills", []) + profile.get("suggested_keywords", [])
    saved_job_keywords = await get_user_refined_search_keywords(user_id)
    
    # Combine and deduplicate
    secondary_keywords = list(set(profile_keywords + saved_job_keywords))

    # Combine with user's primary search terms (e.g., from profile)
    primary_search_term = profile.get("preferred_role", "software engineer")

    logging.info(f"Primary Adzuna keyword: '{primary_search_term}', secondary: '{secondary_keywords}'")
    logging.info(f"Indeed keywords: '{[primary_search_term] + secondary_keywords}'")

    adzuna_jobs = fetch_adzuna_jobs(profile, primary_search_term, secondary_keywords)
    indeed_jobs = fetch_indeed_jobs(profile, [primary_search_term] + secondary_keywords)
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
                
                # Extract keywords from the job description and store them
                job_full_description = job.get('full_description', job.get('description', ''))
                extracted_keywords = extract_keywords_from_job_description(job_full_description)
                job['extracted_keywords'] = extracted_keywords

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
                        "job_details": job, # job now includes 'extracted_keywords'
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

async def run_job_matching_for_all_users(users_collection, profiles_collection, seen_jobs_collection, recommended_jobs_collection, saved_jobs_collection):
    logging.info("Starting periodic job matching for all users.")
    async for user in users_collection.find({}):
        user_id = user["_id"]
        await run_job_matching_for_user(user_id, profiles_collection, seen_jobs_collection, recommended_jobs_collection, saved_jobs_collection)
    logging.info("Finished periodic job matching for all users.")