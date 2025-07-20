Phase 1: Web Portal and Backend Foundation
This phase focuses on establishing the core web application and user management system.
3.1. Backend API (FastAPI) Expansion:
User Authentication: Implement user registration and login with JWT-based authentication.
POST /api/register: Endpoint for new user account creation. (Implemented in main.py)
POST /api/login: Endpoint for user authentication, returning an access token. (Implemented in main.py)
POST /api/password-reset: Endpoint for initiating password recovery via email verification.
POST /api/mfa-setup: Optional endpoint for enabling multi-factor authentication (e.g., via TOTP).
CV Upload Endpoint:
POST /api/cv-upload: Endpoint to accept CV file uploads. (Implemented in main.py)
Support file formats: PDF, DOCX; max size: 5MB. Include error handling for invalid files, with user-friendly responses (e.g., "Unsupported format—please upload PDF or DOCX").
3.2. Frontend Web Portal Development:
User Interface: Simple HTML pages for:
Registration page (register.html)
Login page (login.html)
Main dashboard page for CV upload (index.html)
Client-Side Logic: JavaScript to handle form submissions and interact with the backend API.
Upgrade to responsive design using Tailwind CSS for modern UX, ensuring mobile compatibility.
3.3. CV Parsing Integration:
Upon CV upload to /api/cv-upload, the backend will trigger parse_resume and enhance_profile_with_gemini functions.
Extracted and enhanced profile data will be saved to the MongoDB database (profiles_collection), associated with the user's account.
Data storage: Encrypt sensitive fields (e.g., contact info) at rest; retention policy: Delete after 12 months of inactivity.
Phase 2: Job Matching and Portal Dashboard
This phase integrates job matching capabilities and enhances the user dashboard.
3.4. Job Matching Logic Adaptation:
The existing job matching logic (e.g., run_job_matching_for_all_users from job_matching_service.py) will be integrated as a backend service.
This service will run daily (with on-demand triggers via user dashboard button) for each user, sourcing jobs from integrated APIs (e.g., Indeed, LinkedIn Jobs API where permitted) to avoid scraping risks and ensure fresh data. It will identify job matches based on their profile, and store these matches in the database (recommended_jobs_collection), handling duplicates and expired listings by checking timestamps and unique IDs.
Matching will incorporate personalization, such as user-defined preferences (e.g., salary range, location filters, ignored industries) stored in the user profile, with match scores calculated and displayed (e.g., 0-100 based on keyword overlap and AI relevance).
Scalability: Use async tasks (e.g., Celery) to handle large user bases; limit AI calls per run to control costs.
3.5. New API Endpoints for Job Management:
GET /api/matches: To fetch a list of matched jobs for the logged-in user.
POST /api/matches/{job_id}/apply: To record a user's intent to apply and return the direct URL to the job application page.
DELETE /api/matches/{job_id}: To remove a job match from the user's dashboard.
3.6. Enhanced Portal Dashboard:
The dashboard will display matched jobs fetched from /api/matches.
Each job listing will include an "Apply" button (opening the application page in a new tab) and a "Remove" button.
Additional features: Filters/sorts by match score, salary, location; a "Why this match?" tooltip explaining relevance; and user feedback buttons (e.g., thumbs up/down) to refine future recommendations.
Phase 3: Chrome Extension Overhaul
This phase reconfigures the Chrome extension to interact with the new backend.
3.7. Extension Authentication:
The extension's options page (options.html, options.js) will be updated to allow users to paste an authentication token obtained from the web portal, securely linking the extension to their account.
Improve with Chrome Identity API for OAuth-based login, reducing manual token handling.
3.8. Profile Data Fetching from API:
The popup.js script will be modified to make authenticated requests to a new backend endpoint (e.g., GET /api/me/profile) to retrieve user profile data directly from the database, replacing local storage.
Add local caching (e.g., Chrome storage) for offline access, with sync on reconnect.
Phase 4: On-Demand Document Generation
This final phase implements the dynamic generation of application documents.
3.9. Document Generation API Endpoint:
POST /api/jobs/{job_id}/generate-documents: A new endpoint to generate tailored resumes and cover letters.
This endpoint will utilize the user's profile and specific job details to call existing functions like generate_refined_resume and generate_application_materials.
Generated documents (as downloadable blobs in PDF/DOCX format) will be returned directly in the API response.
Support ATS-friendly formats; allow iterations via optional parameters (e.g., user edits in request body). Extend to non-matched jobs by accepting job_url or details in payload.
3.10. Updated Extension "Fill Form" Logic:
When "Fill Form" is clicked on a job page, the extension will perform a two-step process:
Call /api/jobs/{job_id}/generate-documents to get tailored CV and cover letter text.
Proceed to fill the form using the user's profile data and the newly generated text.
3.11. Handling File Uploads (User Interaction Required):
Constraint: Due to browser security, the Chrome extension cannot programmatically select local files for upload fields.
Solution: The extension will generate and offer direct downloads of the CV/Cover Letter as files (e.g., via blob URLs), or integrate with browser APIs for clipboard/copy-to-new-tab functionality. For uploads, it will highlight the field and prompt the user to select the freshly downloaded file, minimizing steps. Future exploration: Integrate with cloud storage (e.g., Google Drive API) for auto-upload where possible.
4. Technical Requirements
Backend Framework: FastAPI (Python)
Database: MongoDB (via motor for async operations)
Collections: users, profiles, seen_jobs, recommended_jobs
Authentication: JWT (JSON Web Tokens) with python-jose and passlib for password hashing.
AI Integration: Google Gemini API (google-generativeai)
Resume Parsing: resume_parser module
Profile Enhancement: gemini_services module
Job Matching: job_matching_service module
Environment Management: .env files for configuration (python-dotenv)
Logging: Standard Python logging module
Frontend Technologies: HTML, CSS, JavaScript
Chrome Extension Technologies: HTML, CSS, JavaScript, manifest.json
Deployment (Inferred): Docker/Docker Compose for containerization.
API Versioning: Use /api/v1/ prefix for all endpoints.
Rate Limiting: Implement with FastAPI middleware (e.g., 100 requests/min per user).
AI Fallbacks: Include offline modes or alternative models (e.g., local Hugging Face) for outages; monitor costs per API call.
Testing: Unit tests with Pytest; integration tests for end-to-end flows; CI/CD via GitHub Actions.
Monitoring: Integrate Sentry for error tracking and Prometheus for metrics.
Compliance: Ensure GDPR/CCPA adherence with consent prompts and data export endpoints.
Non-Functional: API responses <500ms; system scalable to 10k users via horizontal scaling.
