# Product Requirements Document: Job Application Automation Bot

## 1. Introduction

### 1.1 Purpose
This document outlines the requirements for the Job Application Automation Bot, a command-line interface (CLI) tool designed to streamline and automate the job search and application process for users. The bot leverages AI (specifically Google Gemini) to enhance user profiles, evaluate job fit, and generate tailored application materials, significantly reducing the manual effort involved in job applications.

### 1.2 Goals
*   **Automate Job Discovery:** Efficiently find relevant job postings from multiple sources.
*   **Personalize Applications:** Generate highly customized application materials (cover letters, resumes, Q&A) based on user profiles and specific job descriptions.
*   **Optimize for ATS:** Improve the chances of applications passing Applicant Tracking Systems (ATS) through AI-driven keyword matching and material refinement.
*   **Simplify Profile Management:** Provide tools for users to easily manage and enhance their professional profiles.
*   **User-Friendly Interface:** Offer a straightforward CLI for all bot operations.

## 2. Features

### 2.1 User Profile Management
*   **Profile Creation/Loading:** Load and save encrypted user profiles (`profile.json`).
*   **Resume Parsing:** Extract text from PDF and DOCX resume files.
*   **AI-Powered Profile Enhancement:** Utilize Gemini to analyze resume text and enrich the user's profile with:
    *   Name, contact information (phone, email, LinkedIn)
    *   Enhanced skills list
    *   Professional experience summary
    *   Suggested job search keywords
    *   Suggested salary range
*   **Manual Profile Update:** Allow users to manually add/update skills, location, industry, work type, and salary range.
*   **Profile Change Detection:** Monitor `profile.json` for changes to trigger re-evaluation of seen jobs.
*   **Data Encryption:** Encrypt sensitive user profile data for security.

### 2.2 Job Search and Evaluation
*   **Multi-Source Job Fetching:** Integrate with job boards (e.g., Adzuna, Indeed) to fetch job listings.
*   **Keyword Expansion:** Use Gemini to expand user-defined skills into a broader set of job search keywords.
*   **Job Filtering:** Filter out already "seen" jobs to avoid duplicates.
*   **Full Description Scraping:** Scrape full job descriptions from redirect URLs for comprehensive analysis.
*   **AI-Powered Job Fit Evaluation:** Employ Gemini to assess job fit based on user profile and job description, providing:
    *   A fit score (1-10)
    *   An explanation for the score
    *   A concise summary of the job role
    *   Skill match percentage and matched/missing keywords (ATS simulation)
*   **Job Recommendation System:** Recommend jobs with a fit score of 7 or higher.
*   **Interactive Job Review:** Allow users to review recommended jobs and mark them as "Interested," "Not Interested," or "Save for later."

### 2.3 Application Material Generation and Refinement
*   **AI-Powered Material Generation:** Generate tailored application materials using Gemini:
    *   Customized cover letters (body content only, personal info added separately)
    *   Specific, actionable resume adjustment suggestions
    *   Answers to potential application questions extracted from job descriptions
*   **Refined Resume Generation:** Create a full, professional resume based on the user's profile and AI-generated suggestions, formatted for ATS optimization.
*   **Material Validation and Feedback:** Use Gemini to validate generated materials for completeness, quality, and professionalism, providing actionable suggestions for improvement.
*   **Automated Feedback Application:** Automatically apply Gemini's validation feedback to refine generated materials.
*   **ATS Score Simulation:** Re-evaluate ATS compatibility after material refinement.

### 2.4 Export and Output
*   **DOCX Export:** Export generated cover letters and refined resumes as professional DOCX files.
*   **JSON Export:** Export question-and-answer sets as JSON files.
*   **Organized Output:** Save all generated application materials into a dedicated `applications` folder, named logically by company and job title.

### 2.5 Command-Line Interface (CLI)
*   **Intuitive Commands:** Provide clear and concise CLI commands for all functionalities (e.g., `search`, `review`, `generate`, `refine`, `export-docs`, `update-profile`, `manual-update`, `generate-key`).
*   **Logging:** Comprehensive logging for all operations to `job_bot.log`.

## 3. User Stories

*   As a **job seeker**, I want to **automatically find relevant job postings** so I don't have to manually browse multiple job boards.
*   As a **job seeker**, I want the bot to **tailor my application materials** to each job so my applications stand out.
*   As a **job seeker**, I want my **resume and cover letter to be ATS-friendly** so they pass initial screening.
*   As a **job seeker**, I want to **easily update my professional profile** using my resume or manual input.
*   As a **job seeker**, I want to **review and approve generated materials** before sending them out.
*   As a **job seeker**, I want to **export my application documents** in standard formats (DOCX, JSON) for easy submission.
*   As a **security-conscious user**, I want my **personal profile data to be encrypted** when stored.

## 4. Technical Considerations

### 4.1 Architecture
*   **Python-based CLI:** Core application developed in Python using `click` for the CLI.
*   **Modular Design:** Separation of concerns into modules (e.g., `api_clients.py`, `profile_manager.py`, `resume_parser.py`, `gemini_services.py`, `file_utils.py`, `encryption_utils.py`, `config.py`).
*   **External APIs:** Integration with job board APIs (Adzuna, Indeed) and Google Gemini API.
*   **Web Scraping:** Use `requests` and `BeautifulSoup` for scraping full job descriptions.
*   **Document Generation:** Utilize `python-docx` for creating DOCX files.
*   **Concurrency:** Employ `ThreadPoolExecutor` for parallel processing of job scraping.

### 4.2 Data Storage
*   `profile.json`: Encrypted user profile data.
*   `seen_jobs.json`: List of job IDs already processed.
*   `recommended_jobs.json`: Jobs recommended by the bot for review.
*   `selected_jobs.json`: Jobs selected by the user for material generation.
*   `generated_materials.json`: Raw AI-generated application materials.
*   `edited_materials.json`: Refined and approved application materials.
*   `.profile_hash`: Stores a hash of `profile.json` for change detection.
*   `job_bot.log`: Application logs.

### 4.3 Dependencies
*   `requests`: For HTTP requests to APIs and web scraping.
*   `beautifulsoup4`: For parsing HTML content.
*   `google-generativeai`: For interacting with Google Gemini API.
*   `python-dotenv`: For managing environment variables (API keys, encryption key).
*   `click`: For building the command-line interface.
*   `PyPDF2`: For extracting text from PDF files.
*   `python-docx`: For creating and manipulating DOCX files.
*   `cryptography`: For data encryption/decryption.
*   `schedule`: For scheduling automated tasks (if implemented).
*   `pandas`: (Existing dependency, usage not explicitly clear from `main.py` but noted).
*   `pytest`: For testing.

## 5. Future Enhancements

*   **Scheduled Runs:** Implement automated daily/weekly job searches using `schedule`.
*   **Application Submission:** Develop functionality to automatically submit applications to job boards (requires careful consideration of anti-bot measures and user consent).
*   **More Job Board Integrations:** Expand to other popular job platforms.
*   **Advanced Profile Fields:** Allow users to define more nuanced preferences (e.g., company size, specific technologies to avoid).
*   **UI/Dashboard:** Develop a web-based or desktop GUI for easier interaction and visualization of job search progress.
*   **Feedback Loop for AI:** Implement a mechanism for users to provide feedback on AI-generated content to further refine future outputs.
*   **Cover Letter/Resume Templates:** Allow users to select from different templates for generated documents.
*   **Interview Preparation:** Add features for generating interview questions and practice responses based on job descriptions and user profiles.
