import os
import json
import time
import schedule
import requests
import logging
import click
import PyPDF2
import docx
import google.generativeai as genai
import hashlib
import base64
from cryptography.fernet import Fernet
from dotenv import load_dotenv
from datetime import datetime
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FutureTimeoutError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from google.api_core import exceptions as google_exceptions

# --- Logging Configuration ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("job_bot.log"),
                        logging.StreamHandler()
                    ])

# Load environment variables from .env file
load_dotenv()

# --- Imports from new modules ---
from .config import (
    PROFILE_FILE, SEEN_JOBS_FILE, RECOMMENDED_JOBS_FILE, SELECTED_JOBS_FILE,
    GENERATED_MATERIALS_FILE, EDITED_MATERIALS_FILE, PROFILE_HASH_FILE,
    MAX_WORKERS, SCRAPE_TIMEOUT, MAX_PAGES, MAX_DAYS_OLD
)
from .encryption_utils import load_key, encrypt_data, decrypt_data
from .profile_manager import load_profile, save_profile, validate_profile, has_profile_changed, update_profile_hash
from .resume_parser import parse_resume
from .api_clients import scrape_full_description, fetch_adzuna_jobs, fetch_indeed_jobs
from .gemini_services import (
    enhance_profile_with_gemini, expand_keywords_with_gemini,
    generate_application_materials, simulate_ats_score,
    validate_materials_with_gemini, get_gemini_suggestions,
    apply_validation_feedback, generate_refined_resume, evaluate_job_fit
)
from .file_utils import load_json_file, save_json_file

def save_recommended_job(job_data):
    recommendations = load_json_file(RECOMMENDED_JOBS_FILE)
    recommendations.append(job_data)
    save_json_file(recommendations, RECOMMENDED_JOBS_FILE)

def save_selected_job(job_data):
    selections = load_json_file(SELECTED_JOBS_FILE)
    selections.append(job_data)
    save_json_file(selections, SELECTED_JOBS_FILE)

def filter_new_jobs(jobs, seen_job_ids):
    """Filters out jobs that have already been seen."""
    return [job for job in jobs if job.get('id') and job.get('id') not in seen_job_ids]

# --- CLI Command Group ---
@click.group()
def cli():
    """Job Application Bot CLI."""
    pass

@cli.command()
def search():
    """Fetches, filters, and evaluates new job listings from multiple sources."""
    logging.info("--- Running job search ---")
    profile = load_profile()
    if not validate_profile(profile):
        return

    if has_profile_changed():
        logging.info("Profile has changed. Clearing seen jobs to re-evaluate all.")
        save_json_file([], SEEN_JOBS_FILE) # Reset seen jobs
        update_profile_hash()

    all_skills = profile.get('skills', [])
    suggested_keywords = profile.get('suggested_keywords', [])
    primary_keyword = all_skills[0] if all_skills else ''
    secondary_keywords = all_skills[1:] + suggested_keywords

    safe_secondary_keywords = []
    current_length = 0
    for keyword in secondary_keywords:
        if current_length + len(keyword) + 1 > 512:
            break
        safe_secondary_keywords.append(keyword)
        current_length += len(keyword) + 1

    logging.info(f"Primary keyword: '{primary_keyword}'. Using {len(safe_secondary_keywords)} secondary keywords.")

    seen_job_ids = load_json_file(SEEN_JOBS_FILE)
    
    adzuna_jobs = fetch_adzuna_jobs(profile, primary_keyword, safe_secondary_keywords)
    indeed_keywords = [primary_keyword] + safe_secondary_keywords
    indeed_jobs = fetch_indeed_jobs(profile, indeed_keywords)
    all_jobs = adzuna_jobs + indeed_jobs

    if all_jobs:
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            all_jobs = list(executor.map(scrape_full_description, all_jobs))

        new_jobs = filter_new_jobs(all_jobs, seen_job_ids)
        if new_jobs:
            logging.info(f"Found {len(new_jobs)} new jobs to evaluate.")
            for job in new_jobs:
                title = job.get('title', 'N/A')
                company = job.get('company', {}).get('display_name', 'N/A')
                logging.info(f"--- Evaluating: {title} at {company} ---")
                
                evaluation = evaluate_job_fit(job, profile)
                if not evaluation:
                    logging.error(f"Could not evaluate job: {title}")
                    continue

                fit_score = evaluation.get('fit_score', 0)
                logging.info(f"  - Fit Score: {fit_score}/10")
                logging.info(f"  - Skill Match: {evaluation.get('skill_match_percentage')}%")

                if fit_score >= 7:
                    logging.info(f"  - Recommendation: Saving job - {title}")
                    save_recommended_job({"job_details": job, "evaluation": evaluation})
                else:
                    logging.warning(f"  - Recommendation: Skipping job due to low fit score.")
            
            seen_job_ids.extend([job['id'] for job in new_jobs if job.get('id')])
        else:
            logging.info("No new jobs found.")
    else:
        logging.warning("No jobs found from any source.")

    save_json_file(seen_job_ids, SEEN_JOBS_FILE)
    logging.info("--- Job search finished ---")

@cli.command()
def review():
    """Interactively review recommended jobs."""
    recommendations = load_json_file(RECOMMENDED_JOBS_FILE)
    if not recommendations:
        logging.info("No recommended jobs to review. Run `search` first.")
        return

    keep_jobs, selected_jobs = [], []
    for job_data in recommendations:
        job_details = job_data.get('job_details', {})
        evaluation = job_data.get('evaluation', {})

        click.echo("\n" + "-"*80)
        click.echo(f"Title: {job_details.get('title')}")
        click.echo(f"Company: {job_details.get('company', {}).get('display_name')}")
        click.echo(f"Fit Score: {evaluation.get('fit_score')}/10 | Skill Match: {evaluation.get('skill_match_percentage')}% ")
        click.echo(f"Summary: {evaluation.get('summary')}")
        click.echo("-"*80)

        choice = click.prompt("Action (i=Interested, n=Not Interested, s=Save for later)", type=str, default='s').lower()

        if choice == 'i':
            selected_jobs.append(job_data)
            logging.info(f"Marked as interested: {job_details.get('title')}")
        elif choice == 'n':
            logging.info(f"Marked as not interested: {job_details.get('title')}.")
        else:
            keep_jobs.append(job_data)

    if selected_jobs:
        for job in selected_jobs:
            save_selected_job(job)
    save_json_file(keep_jobs, RECOMMENDED_JOBS_FILE)
    logging.info("Review session finished.")

@cli.command()
def generate():
    """Interactively generates application materials for selected jobs."""
    selected_jobs = load_json_file(SELECTED_JOBS_FILE)
    if not selected_jobs:
        logging.info("No selected jobs to generate materials for. Run `review` first.")
        return

    profile = load_profile()
    all_generated_materials = []
    
    for job_data in selected_jobs:
        job_title = job_data.get('job_details', {}).get('title', 'N/A')
        click.echo("\n" + "="*80)
        click.echo(f"Preparing to generate materials for: {job_title}")
        click.echo("="*80)

        # Initial generation
        generated_job_data = generate_application_materials(job_data, profile)
        if not generated_job_data:
            continue # Skip if initial generation fails

        while True:
            materials = generated_job_data.get('generated_materials', {})
            click.echo("\n--- Generated Cover Letter ---")
            click.echo(materials.get('cover_letter', 'N/A'))
            click.echo("\n--- Generated Resume Suggestions ---")
            for suggestion in materials.get('resume_suggestions', []):
                click.echo(f"- {suggestion}")
            click.echo("\n" + "-"*80)

            action = click.prompt(
                "Action: [a]ccept, [r]egenerate, [s]kip", 
                type=click.Choice(['a', 'r', 's'], case_sensitive=False)
            ).lower()

            if action == 'a':
                all_generated_materials.append(generated_job_data)
                break
            elif action == 's':
                break
            elif action == 'r':
                custom_prompt = click.prompt("Enter your regeneration instructions (e.g., 'make the cover letter more formal')")
                generated_job_data = generate_application_materials(job_data, profile, custom_prompt=custom_prompt)
                if not generated_job_data:
                    click.echo("Failed to regenerate materials. Skipping this job.")
                    break
    
    save_json_file(all_generated_materials, GENERATED_MATERIALS_FILE)
    if all_generated_materials:
        logging.info(f"Finished generating materials for {len(all_generated_materials)} jobs.")
        click.echo(f"Run `refine` to edit and approve them, then `export-docs` to create DOCX files.")
    else:
        logging.info("No materials were generated in this session.")

@cli.command()
def refine():
    """Automatically refines, validates, and approves generated application materials."""
    generated_materials = load_json_file(GENERATED_MATERIALS_FILE)
    if not generated_materials:
        click.echo("No generated materials to refine. Run `generate` first.")
        logging.info("No generated materials to refine. Run `generate` first.")
        return

    approved_materials = []
    profile = load_profile()  # Load profile for refined resume generation
    
    for i, item in enumerate(generated_materials):
        job_details = item.get('job_details', {})
        materials = item.get('generated_materials', {}).copy() # Use a copy to edit
        job_data = item  # For refined resume
        job_title = job_details.get('title', 'N/A')

        click.echo(f"Refining {job_title}...")

        # Generate initial refined resume
        refined_resume = generate_refined_resume(profile, materials, item)
        materials['refined_resume'] = refined_resume

        # Simulate ATS
        ats_results = simulate_ats_score(job_details, materials)
        item['ats_score'] = ats_results

        # Validate
        validation_feedback = validate_materials_with_gemini(materials)

        # Apply feedback
        materials = apply_validation_feedback(materials, validation_feedback)

        # Re-simulate ATS after revision
        ats_results = simulate_ats_score(job_details, materials)
        item['ats_score'] = ats_results

        item['generated_materials'] = materials
        approved_materials.append(item)

    if approved_materials:
        save_json_file(approved_materials, EDITED_MATERIALS_FILE)
        click.echo(f"Saved {len(approved_materials)} approved material sets to {EDITED_MATERIALS_FILE}.")
    else:
        click.echo("No materials were approved in this session.")

@cli.command()
def export_docs():
    """Exports approved and edited materials to DOCX files."""
    approved_materials = load_json_file(EDITED_MATERIALS_FILE)
    if not approved_materials:
        click.echo("No approved materials to export. Run `refine` first.")
        logging.info("No approved materials to export. Run `refine` first.")
        return

    output_dir = "applications"
    os.makedirs(output_dir, exist_ok=True)

    for item in approved_materials:
        job_details = item.get('job_details', {})
        materials = item.get('generated_materials', {})
        company = job_details.get('company', {}).get('display_name', 'N/A').replace(' ', '_')
        title = job_details.get('title', 'N/A').replace(' ', '_')
        doc_path = os.path.join(output_dir, f"{company}_{title}.docx")

        doc = docx.Document()
        doc.add_heading(job_details.get('title'), level=1)
        doc.add_heading(f"Company: {job_details.get('company', {}).get('display_name')}", level=2)

        doc.add_heading("Cover Letter", level=2)
        doc.add_paragraph(materials.get('cover_letter', 'Not generated.'))

        doc.add_heading("Refined Resume", level=2)
        doc.add_paragraph(materials.get('refined_resume', 'Not generated.'))

        doc.add_heading("Question Answers", level=2)
        for qa in materials.get('question_answers', []):
            doc.add_heading(qa.get('question'), level=3)
            doc.add_paragraph(qa.get('answer'))
        
        doc.save(doc_path)
        logging.info(f"Exported materials to {doc_path}")
    click.echo(f"Successfully exported {len(approved_materials)} documents to the 'applications' folder.")

@cli.command()
@click.argument('resume_path', type=click.Path(exists=True))
def update_profile(resume_path):
    """Parses a resume and uses AI to update the profile.json."""
    logging.info(f"Starting profile update with resume: {resume_path}")
    resume_text = parse_resume(resume_path)
    if not resume_text:
        return

    enhanced_data = enhance_profile_with_gemini(resume_text)
    if not enhanced_data:
        return

    profile = load_profile()
    profile.update(enhanced_data)
    
    original_skills = set(profile.get('skills', []))
    enhanced_skills = set(enhanced_data.get('enhanced_skills', []))
    profile['skills'] = sorted(list(original_skills.union(enhanced_skills)))
    
    if save_profile(profile):
        logging.info("Profile has been successfully updated with AI enhancements.")
    else:
        logging.error("Failed to save the updated profile. Please ensure your encryption key is set.")

@cli.command()
@click.option('--skill', multiple=True, help='Add a skill to your profile.')
@click.option('--location', help='Set your preferred job location.')
@click.option('--industry', help='Set your preferred industry.')
@click.option('--work-type', help='Set your preferred work type (e.g., full_time, contract).')
@click.option('--salary-range', help='Set your desired salary range (e.g., "100000-120000").')
def manual_update(skill, location, industry, work_type, salary_range):
    """Manually update your profile."""
    profile = load_profile()
    updated = False
    if skill:
        current_skills = set(profile.get('skills', []))
        current_skills.update(skill)
        profile['skills'] = sorted(list(current_skills))
        updated = True
    if location:
        profile['location'] = location
        updated = True
    if industry:
        profile['industry'] = industry
        updated = True
    if work_type:
        profile['work_type'] = work_type
        updated = True
    if salary_range:
        profile['salary_range'] = salary_range
        updated = True
        
    if updated:
        if save_profile(profile):
            logging.info("Profile updated successfully.")
        else:
            logging.error("Failed to save the updated profile.")
    else:
        logging.warning("No updates provided.")

@cli.command()
def generate_key():
    """Generates a new encryption key and prints it."""
    key = Fernet.generate_key()
    click.echo("Generated Encryption Key (add this to your .env file):")
    click.echo(f"ENCRYPTION_KEY={key.decode()}")

if __name__ == "__main__":
    cli()