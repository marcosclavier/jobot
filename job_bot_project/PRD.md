# Product Requirements Document: Job Bot Application System

## 1. Introduction
This document outlines the requirements for the Job Bot application system, a comprehensive tool designed to assist users in their job application process. The system comprises a web portal, a FastAPI backend, and a Chrome extension, integrating AI-powered resume parsing, profile enhancement, job matching, and on-demand document generation. It includes two AI-powered chatbots: a registration chatbot for capturing user profile information during onboarding (starting with CV upload and using multi-agent workflows for refinement), and a dashboard-accessible chatbot for career planning questions and advice.
The target audience includes entry-level to mid-career professionals in industries like tech, finance, and marketing, who apply to 5+ jobs per week and seek to reduce application time. Unique value propositions include privacy-focused AI processing (data not shared with third parties), faster matching via Gemini integration, and seamless browser automation—differentiating from competitors like LinkedIn (network-focused), Indeed (broad search), Teal (resume builder), and Jobscan (ATS optimization). Benefits: Reduce application time by 50% and improve match quality through user-refined AI.

## 2. Goals
The primary goal of the Job Bot system is to provide a sophisticated, user-friendly, and efficient platform for job seekers to manage their applications, optimize their profiles, and generate tailored application materials. Success will be measured by achieving the following SMART objectives:
- Enable 85% of users to complete a job application (from match to submission) in under 10 minutes, as tracked via in-app analytics by the end of Phase 4.
- Achieve a user satisfaction score of at least 4.5/5 based on post-application surveys, focusing on match relevance and document quality.
- Grow to 10,000 active users within 6 months post-launch, with 70% retention rate, by offering differentiated features like AI-enhanced personalization compared to competitors such as LinkedIn or Indeed.
Additional objectives: Ensure 99% uptime for API endpoints and comply with GDPR/CCPA for data privacy, verified through quarterly audits.

## 3. Key Features & Phases
The development of the Job Bot system will proceed in four major phases:
Dependencies: Phase 2 builds on Phase 1's authentication and database; Phase 3 requires Phase 2's API endpoints; Phase 4 integrates all prior phases. User flows and wireframes (e.g., Figma prototypes for dashboard and extension) will be developed in parallel to guide UI/UX.

### Phase 1: Web Portal and Backend Foundation
This phase focuses on establishing the core web application and user management system.

**3.1. Backend API (FastAPI) Expansion:**
*   **User Authentication:** Implement user registration and login with JWT-based authentication.
    *   `POST /api/register`: Endpoint for new user account creation. (Implemented in `main.py`)
    *   `POST /api/login`: Endpoint for user authentication, returning an access token. (Implemented in `main.py`)
    *   `POST /api/password-reset`: Endpoint for initiating password recovery via email verification.
    *   `POST /api/mfa-setup`: Optional endpoint for enabling multi-factor authentication (e.g., via TOTP).
*   **CV Upload Endpoint:**
    *   `POST /api/cv-upload`: Endpoint to accept CV file uploads and update existing user profiles. (Implemented in `main.py`)
    *   Support file formats: PDF, DOCX; max size: 5MB. Include error handling for invalid files, with user-friendly responses (e.g., "Unsupported format—please upload PDF or DOCX").

**3.2. Frontend Web Portal Development:**
*   **User Interface:** Simple HTML pages for:
    *   Registration page (`register.html`)
    *   Login page (`login.html`)
    *   Main dashboard page for CV upload (`index.html`)
*   **Client-Side Logic:** JavaScript to handle form submissions and interact with the backend API.
*   Upgrade to responsive design using Tailwind CSS for modern UX, ensuring mobile compatibility.

**3.3. CV Parsing Integration:**
*   Upon CV upload to `/api/cv-upload`, the backend will trigger `parse_resume` and `enhance_profile_with_gemini` functions.
*   Extracted and enhanced profile data will be saved to the MongoDB database (`profiles_collection`), associated with the user's account.
*   Data storage: Encrypt sensitive fields (e.g., contact info) at rest; retention policy: Delete after 12 months of inactivity.

**3.4. Registration Chatbot:**
*   **Objective:** Integrate a conversational AI chatbot into the registration flow to capture user profile information (e.g., name, contact info, education, work experience, skills) through natural dialogue, starting with CV upload, and using multi-agent workflows for refinement. The chatbot builds the candidate's profile using predefined information clusters, ensuring optional and toggleable elements to avoid discrimination (e.g., ageism).
*   **User Flow:** After submitting email/password in `/api/register`, users are redirected to the chatbot session with a temporary token. The chatbot prompts users to first upload their CV (or LinkedIn profile/raw text) via the `/api/cv-upload` endpoint (adapted for temporary sessions). Once uploaded, the system parses the document to pre-fill 70% of profile clusters, then engages in 3-5 targeted questions to collect the remaining 30%, focusing on high-impact areas like achievements. Users can review and toggle clusters for inclusion/omissions.
*   **Key Components:**
    *   Uses Gemini API for responses, with a system prompt focused on onboarding questions, data extraction, and subtle guidance (e.g., "Tell me about your education—should we omit dates?").
    *   WebSocket-based for real-time interaction during registration.
    *   Extracts data into profile clusters and updates `profiles_collection` incrementally.
    *   UX: Non-overwhelming, positive experience with optional skips; starts automatically post-email/password setup.
    *   Security: Tied to temporary session token during registration.
    *   **Multi-Agent Workflow Integration:** Deploy collaborative AI agents (e.g., via CrewAI or similar) for profile refinement:
        - **Parser Agent:** Uses NLP/computer vision (e.g., PyMuPDF for PDFs) to extract and pre-fill clusters from uploads (e.g., education from text sections).
        - **Feedback Agent:** Scores completeness (aim for 90%), suggests gaps/omissions, and generates adaptive questions based on user level/industry (e.g., metrics for executives, soft skills for entry-level).
        - **Validator Agent:** Cross-verifies data against user inputs, handles toggles for sensitive clusters (e.g., hide graduation_year if >15 years), and flags bias risks per the cluster table.
        - **Writer Agent:** Refines summaries, mimics user writing style, and prioritizes ~15-20 data points (e.g., top 5 skills per industry).
    *   **Adaptive Questionnaire:** Generates dynamic, branched questions (start with 5 core, branch to 10-15 more); incorporates feedback loops (e.g., "Does this summary match your style?").
    *   **Multi-Modal Inputs:** Handles text chats, voice (via speech-to-text, e.g., Google Cloud Speech), or LinkedIn auto-imports; pulls from job ads for aligned prompts (e.g., "This role needs Python—experience?").
    *   **Information Clusters:** Profiles built using modular clusters (optional/toggleable):
        - name: Full name.
        - contact_info: Dictionary with "email", "phone", "linkedin".
        - location: City/state/country.
        - education: List with "institution", "degree", "field", "graduation_year" (optional hide).
        - work_experience: List with "company", "title", "start_date", "end_date", "responsibilities".
        - enhanced_skills: List of skills/technologies.
        - experience_summary: Brief professional summary.
        - suggested_keywords: 10-15 keywords.
        - salary_range: Suggested range.
        - achievements: List with "description", "context", "date".
        - projects: List with "name", "description", "technologies", "role", "outcome".
        - certifications: List with "name", "organization", "issue_date", "expiration".
        - volunteer_experience: Similar to work_experience.
        - languages: List with "language", "proficiency".
        - publications: List with "title", "venue", "date".
        - hobbies: 3-5 items with professional ties.
        - athletic_achievements: Subset of achievements.
        - professional_affiliations: List with "organization", "role", "dates".
        - references: 2-3 contacts (optional).
    *   **Omission and Toggle Handling:** Clusters are optional/toggleable via UI checkboxes (e.g., "Include in CV?", "Hide dates?"). Automated suggestions flag risks (e.g., "Omit graduation_year from 20+ years ago?"). Avoid discriminatory fields like DOB/photos. Prompt thoughtfully: "Omit dates to avoid biases?" with tips. Use cluster table for risks/strategies.
    *   **Benefits and Optimality:** Ensures accuracy via cross-verification; targets 70% pre-fill, 30% via questions; yields 20-30% more ATS-friendly CVs. Scales across levels/industries with prioritization (e.g., 15-20 items).
*   **New API Endpoints:**
    *   `GET /api/onboarding-chat`: WebSocket endpoint for registration chatbot interaction.

**3.5. Career Coach LLM Chatbot:**
*   **Objective:** Create a WebSocket-based chat endpoint accessible from the dashboard for career planning questions, advice, and profile refinements.
*   **Key Components:**
    *   New DB collection: `chat_histories` to store per-user message lists.
    *   System prompt: Defines the coach's behavior (empathetic, subtle CV prompts, data extraction for clusters like education/achievements).
    *   WebSocket endpoint: Authenticates via JWT, handles messages, calls Gemini, extracts data, updates profiles.
    *   Integration: Link to existing `/api/cv-upload` for notifications; update profiles in `profiles_collection` with extracted data.
    *   UX Considerations: Make it non-overwhelming (e.g., start with a welcome message); handle omissions (e.g., ageism) and style matching in the prompt.
    *   Security: Rate limit WebSockets; validate tokens.
*   **New API Endpoints:**
    *   `GET /api/chat`: WebSocket endpoint for real-time chat interaction.

### Phase 2: Job Matching and Portal Dashboard
This phase integrates job matching capabilities and enhances the user dashboard.

**3.6. Job Matching Logic Adaptation:**
*   The existing job matching logic (e.g., `run_job_matching_for_all_users` from `job_matching_service.py`) will be integrated as a backend service.
*   This service will run daily (with on-demand triggers via user dashboard button) for each user, sourcing jobs from integrated APIs (e.g., Indeed, LinkedIn Jobs API where permitted) to avoid scraping risks and ensure fresh data. It will identify job matches based on their profile, and store these matches in the database (`recommended_jobs_collection`), handling duplicates and expired listings by checking timestamps and unique IDs.
*   Matching will incorporate personalization, such as user-defined preferences (e.g., salary range, location filters, ignored industries) stored in the user profile, with match scores calculated and displayed (e.g., 0-100 based on keyword overlap and AI relevance).
*   Scalability: Use async tasks (e.g., Celery) to handle large user bases; limit AI calls per run to control costs.
*   To refine job searches, extract keywords (e.g., skills, job titles, technologies) from saved jobs in the `saved_jobs_collection` using AI (e.g., Gemini API or adapted `resume_parser` logic for job descriptions). These keywords will be aggregated (e.g., top 10 frequent/relevant terms) and incorporated into API query parameters for better-targeted searches (e.g., "python developer remote machine learning" for Indeed API queries).

**3.7. New API Endpoints for Job Management:**
*   `GET /api/matches`: To fetch a list of matched jobs for the logged-in user.
*   `POST /api/matches/{job_id}/apply`: To record a user's intent to apply and return the direct URL to the job application page.
*   `DELETE /api/matches/{job_id}`: To remove a job match from the user's dashboard.
*   `POST /api/matches/{job_id}/save`: To save a job match to the user's saved jobs list, storing it in `saved_jobs_collection` for keyword extraction and future reference.
*   `GET /api/saved-jobs`: To fetch the list of saved jobs for the logged-in user.
*   `DELETE /api/saved-jobs/{job_id}`: To remove a job from the saved jobs list.

**3.8. Enhanced Portal Dashboard:**
*   The dashboard will display matched jobs fetched from `/api/matches`.
*   Each job listing will include an "Apply" button (opening the application page in a new tab) and a "Remove" button.
*   Additional features: Filters/sorts by match score, salary, location; a "Why this match?" tooltip explaining relevance; and user feedback buttons (e.g., thumbs up/down) to refine future recommendations.
*   Add a "Save" button per job listing to trigger `/api/matches/{job_id}/save`, and a separate tab/section for viewing saved jobs fetched from `/api/saved-jobs`, with options to remove or apply from there.
*   Integrate the Career Coach chatbot as an embedded chat window in the dashboard for on-demand career questions.

### Phase 3: Chrome Extension Overhaul
This phase reconfigures the Chrome extension to interact with the new backend.

**3.9. Extension Authentication:**
*   The extension's options page (`options.html`, `options.js`) will be updated to allow users to paste an authentication token obtained from the web portal, securely linking the extension to their account.
*   Improve with Chrome Identity API for OAuth-based login, reducing manual token handling.

**3.10. Profile Data Fetching from API:**
*   The `popup.js` script will be modified to make authenticated requests to a new backend endpoint (e.g., `GET /api/me/profile`) to retrieve user profile data directly from the database, replacing local storage.
*   Add local caching (e.g., Chrome storage) for offline access, with sync on reconnect.

### Phase 4: On-Demand Document Generation
This final phase implements the dynamic generation of application documents.

**3.11. Document Generation API Endpoint:**
*   `POST /api/jobs/{job_id}/generate-documents`: A new endpoint to generate tailored resumes and cover letters.
*   This endpoint will utilize the user's profile and specific job details to call existing functions like `generate_refined_resume` and `generate_application_materials`.
*   Generated documents (as downloadable blobs in PDF/DOCX format) will be returned directly in the API response.
*   Support ATS-friendly formats; allow iterations via optional parameters (e.g., user edits in request body). Extend to non-matched jobs by accepting job_url or details in payload.

**3.12. Updated Extension "Fill Form" Logic:**
*   When "Fill Form" is clicked on a job page, the extension will perform a two-step process:
    1.  Call `/api/jobs/{job_id}/generate-documents` to get tailored CV and cover letter text.
    2.  Proceed to fill the form using the user's profile data and the newly generated text.

**3.13. Handling File Uploads (User Interaction Required):**
*   **Constraint:** Due to browser security, the Chrome extension cannot programmatically select local files for upload fields.
*   **Solution:** The extension will generate and offer direct downloads of the CV/Cover Letter as files (e.g., via blob URLs), or integrate with browser APIs for clipboard/copy-to-new-tab functionality. For uploads, it will highlight the field and prompt the user to select the freshly downloaded file, minimizing steps. Future exploration: Integrate with cloud storage (e.g., Google Drive API) for auto-upload where possible.

## 4. Technical Requirements

*   **Backend Framework:** FastAPI (Python)
*   **Database:** MongoDB (via `motor` for async operations)
    *   Collections: `users`, `profiles`, `seen_jobs`, `recommended_jobs`, `saved_jobs`, `chat_histories`, `temp_sessions` (for registration onboarding)
*   **Authentication:** JWT (JSON Web Tokens) with `python-jose` and `passlib` for password hashing.
    *   **Web Authentication:** Token stored in HTTP-only cookies for secure session management.
    *   **Chrome Extension Authentication:** OAuth2 Implicit Flow for secure token acquisition.
*   **AI Integration:** Google Gemini API (`google-generativeai`); CrewAI for multi-agent workflows; PyMuPDF for PDF parsing; Google Cloud Speech for voice inputs.
*   **Resume Parsing:** `resume_parser` module, enhanced with PyMuPDF for document extraction.
*   **Profile Enhancement:** `gemini_services` module, integrated with agent workflows.
*   **Job Matching:** `job_matching_service` module
*   **Environment Management:** `.env` files for configuration (`python-dotenv`)
*   **Logging:** Standard Python `logging` module
*   **Frontend Technologies:** HTML, CSS, JavaScript
*   **Chrome Extension Technologies:** HTML, CSS, JavaScript, `manifest.json`
*   **Deployment (Inferred):** Docker/Docker Compose for containerization.
*   API Versioning: Use /api/v1/ prefix for all endpoints.
*   Rate Limiting: Implement with FastAPI middleware (e.g., 100 requests/min per user).
*   AI Fallbacks: Include offline modes or alternative models (e.g., local Hugging Face) for outages; monitor costs per API call.
*   Testing: Unit tests with Pytest; integration tests for end-to-end flows; CI/CD via GitHub Actions.
*   Monitoring: Integrate Sentry for error tracking and Prometheus for metrics.
*   Compliance: Ensure GDPR/CCPA adherence with consent prompts and data export endpoints.
*   Non-Functional: API responses <500ms; system scalable to 10k users via horizontal scaling.
*   Keyword Extraction: Adapt `gemini_services` or add a new module (e.g., `job_keyword_extractor`) using Gemini to parse saved job descriptions for relevant terms (e.g., TF-IDF or AI-summarized keywords).
*   Chatbot Implementation: Separate system prompts for registration (profile-focused with agent workflow) and dashboard (advice-focused) chatbots; use WebSockets for both. Support multi-modal inputs (text/voice) and cluster-based data handling with toggles.

## 5. Out of Scope / Future Considerations
*   Automated file uploads for generated documents (due to browser security constraints).
*   Advanced analytics or reporting features for job application success rates.
*   Integration with third-party job boards beyond initial scraping (if any).
*   Real-time job matching notifications.
*   Mobile app development (focus on responsive web first); interview prep tools; monetization details (e.g., freemium with premium tiers for unlimited matches).

## 6. Risks and Mitigations
*   Risk: AI hallucinations in generated documents—Mitigation: Add validation prompts and user edit previews.
*   Risk: Scalability issues with job matching—Mitigation: Optimize with caching and batch processing.
*   Risk: Data privacy breaches—Mitigation: Regular security audits and penetration testing.
*   Risk: Poor UX leading to low adoption—Mitigation: Conduct user testing with 20+ beta testers per phase.
*   Risk: Inaccurate keyword extraction from saved jobs—Mitigation: Use AI prompts focused on job-specific terms and validate with user feedback loops.
*   Risk: Chatbot overload or irrelevant responses—Mitigation: Refine system prompts iteratively and limit session lengths.
*   Risk: Incomplete profile data from uploads—Mitigation: Ensure agent workflows achieve 90% completeness with user verification.

This PRD will serve as the guiding document for the development of the Job Bot application system. For endpoints summary:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| /api/register | POST | User registration | No |
| /api/login | POST | User login | No |
| /api/password-reset | POST | Password recovery | No |
| /api/mfa-setup | POST | MFA setup | Yes |
| /api/cv-upload | POST | Upload CV | Yes |
| /api/matches | GET | Get matched jobs | Yes |
| /api/matches/{job_id}/apply | POST | Record apply intent | Yes |
| /api/matches/{job_id} | DELETE | Remove match | Yes |
| /api/matches/{job_id}/save | POST | Save job | Yes |
| /api/saved-jobs | GET | Get saved jobs | Yes |
| /api/saved-jobs/{job_id} | DELETE | Remove saved job | Yes |
| /api/me/profile | GET | Get user profile | Yes |
| /api/jobs/{job_id}/generate-documents | POST | Generate docs | Yes 
| /api/onboarding-chat | GET | WebSocket for registration chat | No 
| /api/chat | GET | WebSocket for dashboard chat | Yes 

| Cluster | Potential Bias Risk | Omission Strategy |
|---------|---------------------|-------------------|
| Education | Ageism via graduation_year | Make year optional; default to hide if >15 years old. |
| Work Experience | Ageism from long history | Limit to 10-15 recent years; summarize older roles without dates. |
| Achievements/Athletic | Indirect age/gender cues | User toggle; rephrase to focus on skills (e.g., "Team leadership in sports" without specifics). |
| Volunteer Experience | Cultural/ethnic hints | Optional; emphasize transferable skills only. |
| Hobbies | Personal biases (e.g., family-related) | Skippable; tie to professional traits if included. 