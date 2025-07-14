# Job Application Automation Bot

This project is a Python-based automation bot that streamlines the job application process for remote positions.

## Project Structure

```
job_bot_project/
├── applications/          # Output directory for generated DOCX files
├── main.py                # The main script with the CLI commands
├── config.py              # All constants (PROFILE_FILE, MAX_WORKERS, etc.)
├── encryption_utils.py    # load_key, encrypt_data, decrypt_data functions
├── profile_manager.py     # load_profile, save_profile, validate_profile
├── resume_parser.py       # PDF and DOCX text extraction functions
├── api_clients.py         # fetch_adzuna_jobs, fetch_indeed_jobs, scrape_full_description
├── gemini_services.py     # All functions that call the Gemini API
├── file_utils.py          # load_json_file, save_json_file, and hash functions
├── .env                   # Environment variables (API keys, encryption key)
├── .gitignore             # Git ignore file
├── profile.json           # Encrypted user profile
├── job_bot.log            # Log file for bot operations
└── requirements.txt       # Python dependencies
```

## Setup

1.  Navigate into the `job_bot_project` directory:
    `cd job_bot_project`
2.  Install dependencies:
    `pip install -r requirements.txt`
3.  Generate an encryption key and add it to your `.env` file:
    `python main.py generate-key`
    Copy the output `ENCRYPTION_KEY` and paste it into the `.env` file.
4.  Add your API keys (e.g., ADZUNA_APP_ID, ADZUNA_APP_KEY, INDEED_API_KEY) to the `.env` file.
5.  Update `profile.json` with your information. You can do this manually or by running:
    `python main.py update-profile <path_to_your_resume.pdf_or_docx>`
    or manually:
    `python main.py manual-update --skill "Python" --location "Remote"`

## Usage

Navigate to the `job_bot_project` directory and run the bot commands:

-   **Search for jobs:**
    `python main.py search`
-   **Review recommended jobs:**
    `python main.py review`
-   **Generate application materials:**
    `python main.py generate`
-   **Refine generated materials:**
    `python main.py refine`
-   **Export documents:**
    `python main.py export-docs`
-   **Update profile with resume:**
    `python main.py update-profile <path_to_your_resume.pdf_or_docx>`
-   **Manually update profile:**
    `python main.py manual-update --help`
-   **Generate encryption key:**
    `python main.py generate-key`

## Disclaimer

This bot is for personal use only. Use it at your own risk. The author is not responsible for any consequences of using this bot.