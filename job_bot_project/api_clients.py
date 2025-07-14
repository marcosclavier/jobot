import os
import requests
import logging
import json
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .config import MAX_WORKERS, SCRAPE_TIMEOUT, MAX_PAGES, MAX_DAYS_OLD

def scrape_full_description(job):
    """Scrapes the full job description from the redirect URL."""
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
    """Fetches job listings from Adzuna with a primary and secondary keyword strategy."""
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")

    if not app_id or not app_key:
        logging.error("Adzuna API credentials not found.")
        return []

    base_url = "https://api.adzuna.com/v1/api/jobs/us/search"
    params = {
        'app_id': app_id,
        'app_key': app_key,
        'results_per_page': 50,
        'what': primary_keyword,
        'what_or': ' '.join(secondary_keywords),
        'where': profile.get('location', 'remote'),
        'sort_by': 'date',
        'max_days_old': MAX_DAYS_OLD
    }

    all_jobs = []
    for page in range(1, MAX_PAGES + 1):
        try:
            response = requests.get(f"{base_url}/{page}", params=params)
            response.raise_for_status()
            data = response.json()
            jobs = data.get('results', [])
            all_jobs.extend(jobs)
            if len(jobs) < params['results_per_page']:
                break
        except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
            logging.error(f"Error fetching from Adzuna on page {page}: {e}", exc_info=True)
            break

    return all_jobs

def fetch_indeed_jobs(profile, keywords):
    """Fetches job listings from Indeed API with retries."""
    api_key = os.getenv("INDEED_API_KEY")
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
