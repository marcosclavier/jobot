# Product Requirements Document: Job Bot Application System

## 1. Introduction
This document outlines the requirements for the Job Bot application system, a comprehensive tool designed to assist users in their job application process. The system comprises a web portal, a FastAPI backend, and a Chrome extension, integrating AI-powered resume parsing, profile enhancement, job matching, and on-demand document generation.

## 2. Goals
The primary goal of the Job Bot system is to provide a sophisticated, user-friendly, and efficient platform for job seekers to manage their applications, optimize their profiles, and generate tailored application materials.

## 3. Key Features & Phases
The development of the Job Bot system will proceed in four major phases:

### Phase 1: Web Portal and Backend Foundation
This phase focuses on establishing the core web application and user management system.

**3.1. Backend API (FastAPI) Expansion:**
*   **User Authentication:** Implement user registration and login with JWT-based authentication.
    *   `POST /api/register`: Endpoint for new user account creation. (Implemented in `main.py`)
    *   `POST /api/login`: Endpoint for user authentication, returning an access token. (Implemented in `main.py`)
*   **CV Upload Endpoint:**
    *   `POST /api/cv-upload`: Endpoint to accept CV file uploads. (Implemented in `main.py`)

**3.2. Frontend Web Portal Development:**
*   **User Interface:** Simple HTML pages for:
    *   Registration page (`register.html`)
    *   Login page (`login.html`)
    *   Main dashboard page for CV upload (`index.html`)
*   **Client-Side Logic:** JavaScript to handle form submissions and interact with the backend API.

**3.3. CV Parsing Integration:**
*   Upon CV upload to `/api/cv-upload`, the backend will trigger `parse_resume` and `enhance_profile_with_gemini` functions.
*   Extracted and enhanced profile data will be saved to the MongoDB database (`profiles_collection`), associated with the user's account.

### Phase 2: Job Matching and Portal Dashboard
This phase integrates job matching capabilities and enhances the user dashboard.

**3.4. Job Matching Logic Adaptation:**
*   The existing job matching logic (e.g., `run_job_matching_for_all_users` from `job_matching_service.py`) will be integrated as a backend service.
*   This service will periodically run for each user, identify job matches based on their profile, and store these matches in the database (`recommended_jobs_collection`).

**3.5. New API Endpoints for Job Management:**
*   `GET /api/matches`: To fetch a list of matched jobs for the logged-in user.
*   `POST /api/matches/{job_id}/apply`: To record a user's intent to apply and return the direct URL to the job application page.
*   `DELETE /api/matches/{job_id}`: To remove a job match from the user's dashboard.

**3.6. Enhanced Portal Dashboard:**
*   The dashboard will display matched jobs fetched from `/api/matches`.
*   Each job listing will include an "Apply" button (opening the application page in a new tab) and a "Remove" button.

### Phase 3: Chrome Extension Overhaul
This phase reconfigures the Chrome extension to interact with the new backend.

**3.7. Extension Authentication:**
*   The extension's options page (`options.html`, `options.js`) will be updated to allow users to paste an authentication token obtained from the web portal, securely linking the extension to their account.

**3.8. Profile Data Fetching from API:**
*   The `popup.js` script will be modified to make authenticated requests to a new backend endpoint (e.g., `GET /api/me/profile`) to retrieve user profile data directly from the database, replacing local storage.

### Phase 4: On-Demand Document Generation
This final phase implements the dynamic generation of application documents.

**3.9. Document Generation API Endpoint:**
*   `POST /api/jobs/{job_id}/generate-documents`: A new endpoint to generate tailored resumes and cover letters.
*   This endpoint will utilize the user's profile and specific job details to call existing functions like `generate_refined_resume` and `generate_application_materials`.
*   Generated documents (text content) will be returned directly in the API response.

**3.10. Updated Extension "Fill Form" Logic:**
*   When "Fill Form" is clicked on a job page, the extension will perform a two-step process:
    1.  Call `/api/jobs/{job_id}/generate-documents` to get tailored CV and cover letter text.
    2.  Proceed to fill the form using the user's profile data and the newly generated text.

**3.11. Handling File Uploads (User Interaction Required):**
*   **Constraint:** Due to browser security, the Chrome extension cannot programmatically select local files for upload fields.
*   **Solution:** The extension will present the generated CV/Cover Letter text to the user (e.g., in a new tab or via copy-to-clipboard). The user will then manually save the text as a `.docx` or `.pdf` file and select it in the upload dialog.

## 4. Technical Requirements

*   **Backend Framework:** FastAPI (Python)
*   **Database:** MongoDB (via `motor` for async operations)
    *   Collections: `users`, `profiles`, `seen_jobs`, `recommended_jobs`
*   **Authentication:** JWT (JSON Web Tokens) with `python-jose` and `passlib` for password hashing.
*   **AI Integration:** Google Gemini API (`google-generativeai`)
*   **Resume Parsing:** `resume_parser` module
*   **Profile Enhancement:** `gemini_services` module
*   **Job Matching:** `job_matching_service` module
*   **Environment Management:** `.env` files for configuration (`python-dotenv`)
*   **Logging:** Standard Python `logging` module
*   **Frontend Technologies:** HTML, CSS, JavaScript
*   **Chrome Extension Technologies:** HTML, CSS, JavaScript, `manifest.json`
*   **Deployment (Inferred):** Docker/Docker Compose for containerization.

## 5. Out of Scope / Future Considerations
*   Automated file uploads for generated documents (due to browser security constraints).
*   Advanced analytics or reporting features for job application success rates.
*   Integration with third-party job boards beyond initial scraping (if any).
*   Real-time job matching notifications.

This PRD will serve as the guiding document for the development of the Job Bot application system.