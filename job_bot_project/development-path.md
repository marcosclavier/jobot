
#### Phase 1: Web Portal and Backend Foundation (Focus: Core setup, user basics, and chatbot onboarding)
- **Sub-stage 1.1: Backend Skeleton and Environment Setup**
  - Deliverables: Set up FastAPI project structure, integrate MongoDB (via `motor`), load `.env` configs, and configure basic logging. Include setup for new collections: `users`, `profiles`, `saved_jobs`, `chat_histories`, `temp_sessions` (for registration chatbot). Install dependencies: `crewai`, `pymupdf`, `google-cloud-speech` (for multi-modal inputs).
  - Dependencies: None.
  - Why small: Pure boilerplate.
  - Test: Verify server runs, MongoDB connects, and `.env` loads.

- **Sub-stage 1.2: User Authentication Endpoints**
  - Deliverables: Implement JWT auth with `POST /api/register`, `POST /api/login`, password hashing, and cookie-based token storage. Add password reset (`POST /api/password-reset`) and MFA setup (`POST /api/mfa-setup`). For registration, generate a temporary session token (stored in `temp_sessions_collection`) to enable pre-login CV upload and chatbot interaction.
  - Dependencies: Sub-stage 1.1.
  - Test: Manual API calls for user creation/login; verify cookie and temp token generation.

- **Sub-stage 1.3: CV Upload and Parsing Integration**
  - Deliverables: Enhance `POST /api/cv-upload` to support pre-login uploads (using temp_token) and authenticated uploads. Handle PDF/DOCX (5MB limit), parse with PyMuPDF (`fitz`) for text extraction, and pre-fill ~70% of profile clusters (e.g., education, work_experience). Store temp profiles in `temp_sessions_collection` or update `profiles_collection` post-login. Convert ObjectIds to strings in responses (e.g., `profile["_id"] = str(profile["_id"])`).
  - Dependencies: Sub-stage 1.2.
  - Test: Upload sample CVs (pre/post-login), verify parsed data in DB, check serialization.

- **Sub-stage 1.4: Basic Frontend Pages**
  - Deliverables: Create responsive HTML/JS pages (`register.html`, `login.html`, `index.html`) with Tailwind CSS. Add file upload input and WebSocket-based chat UI to `register.html` for onboarding chatbot interaction post-email/password submission.
  - Dependencies: Sub-stage 1.3.
  - Test: Local server run; verify form submissions and chat UI rendering.

- **Sub-stage 1.5: Registration Chatbot with Multi-Agent Workflow**
  - Deliverables: Implement WebSocket endpoint (`GET /api/onboarding-chat`) for registration chatbot, authenticating via temp_token. Use Gemini API with a custom prompt to prompt CV upload first, then ask 3-5 targeted questions to fill gaps (30% of profile data). Integrate multi-agent workflow (inspired by CrewAI):
    - **Parser Agent**: Extracts clusters (e.g., name, contact_info, education) from CV using PyMuPDF and Gemini.
    - **Feedback Agent**: Scores profile completeness (aim for 90%), suggests gaps/omissions (e.g., "Omit graduation_year?").
    - **Validator Agent**: Verifies data, adds toggles (e.g., `{"include": true}`) for clusters, flags bias risks per table (e.g., hide dates >15 years).
    - **Writer Agent**: Refines summaries, mimics user style, prioritizes ~15-20 data points.
    - Support multi-modal inputs (text/voice via Google Cloud Speech). Store temp profile in `temp_sessions_collection`, transfer to `profiles_collection` on completion. Add UI for cluster toggles (checkboxes in chat).
  - Dependencies: Sub-stage 1.2, 1.3, 1.4.
  - Test: Simulate registration, upload CV, interact via chat/voice, verify profile data (70% pre-fill, 30% via questions), check toggles and omission prompts.

- **Sub-stage 1.6: Career Coach LLM Chatbot**
  - Deliverables: Implement WebSocket-based chat endpoint (`GET /api/chat`) for dashboard-based career planning. Store history in `chat_histories_collection`. Use Gemini with a prompt for advice, subtle CV prompts, and profile refinements. Authenticate via JWT. Link with `/api/cv-upload` for notifications. Update profiles with extracted data. Convert ObjectIds in responses.
  - Dependencies: Sub-stage 1.2, 1.3, 1.4.
  - Test: Test WebSocket connection, history persistence, Gemini responses, profile updates.

#### Phase 2: Job Matching and Portal Dashboard (Focus: Matching logic, saved jobs, keyword extraction, and UI enhancements)
- **Sub-stage 2.1: Job Matching Service Integration**
  - Deliverables: Adapt `run_job_matching_for_all_users` as a scheduled service (e.g., daily via APScheduler), source jobs from APIs (e.g., Indeed), store in `recommended_jobs_collection` with deduping/expiry logic. Add initial setup for keyword extraction in `job_matching_service.py` or new `job_keyword_extractor.py` using Gemini (top 10 terms via TF-IDF/AI summary).
  - Dependencies: Phase 1 complete.
  - Test: Run manually for a test user; verify matches and keyword output in DB.

- **Sub-stage 2.2: Job Management API Endpoints**
  - Deliverables: Add `GET /api/matches`, `POST /api/matches/{job_id}/apply`, `DELETE /api/matches/{job_id}` with auth and personalization. Extend with saved jobs endpoints: `POST /api/matches/{job_id}/save` (store in `saved_jobs_collection`, trigger keyword extraction), `GET /api/saved-jobs`, `DELETE /api/saved-jobs/{job_id}`. Convert ObjectIds to strings in all responses (e.g., `for match in matches: match["_id"] = str(match["_id"])`).
  - Dependencies: Sub-stage 2.1.
  - Test: API queries for matches/saved jobs; verify no serialization errors.

- **Sub-stage 2.3: Keyword Integration into Matching**
  - Deliverables: Update matching service to aggregate keywords from `saved_jobs_collection` (fetch, extract if not pre-stored, combine into query params like "python developer remote"), refine API searches. Handle updates (e.g., re-extract on save/delete).
  - Dependencies: Sub-stage 2.2.
  - Test: Save sample jobs, run matching, verify refined queries.

- **Sub-stage 2.4: Enhanced Dashboard UI**
  - Deliverables: Update `index.html` to display matches with filters, "Apply"/"Remove" buttons, tooltips, and feedback. Add "Save" button per listing (`/api/matches/{job_id}/save`), and a saved jobs tab/section (`/api/saved-jobs`). Embed Career Coach chatbot UI.
  - Dependencies: Sub-stage 2.3.
  - Test: End-to-end: Upload CV, save jobs, run matching, view dashboard, interact with chatbot.

#### Phase 3: Chrome Extension Overhaul (Focus: Extension-backend integration)
- **Sub-stage 3.1: Extension Authentication Setup**
  - Deliverables: Update `options.html/js` for auth (prefer Chrome Identity API), link to user account.
  - Dependencies: Phase 2 complete.
  - Test: Install extension, authenticate.

- **Sub-stage 3.2: Profile Fetching and Caching**
  - Deliverables: Modify `popup.js` to fetch from `GET /api/me/profile`, add local caching. Ensure frontend handles string-converted ObjectIds.
  - Dependencies: Sub-stage 3.1.
  - Test: Load profile in extension popup.

#### Phase 4: On-Demand Document Generation (Focus: AI generation and form filling)
- **Sub-stage 4.1: Document Generation Endpoint**
  - Deliverables: Add `POST /api/jobs/{job_id}/generate-documents` using Gemini, return blobs (PDF/DOCX), support ATS formats and non-matched jobs. Convert ObjectIds in job/profile data to strings.
  - Dependencies: Phase 3 complete.
  - Test: Call with sample job_id; download files.

- **Sub-stage 4.2: Extension Form Filling Logic**
  - Deliverables: Update "Fill Form" to call generation API, fill fields, handle uploads (downloads + prompts).
  - Dependencies: Sub-stage 4.1.
  - Test: Test on a mock job page.

- **Sub-stage 4.3: Final Integrations and Polish**
  - Deliverables: Add rate limiting, monitoring (Sentry), testing (Pytest), compliance checks. Verify keyword extraction and chatbot (both registration and career coach) performance. Audit ObjectId handling across all endpoints.
  - Dependencies: All prior.
  - Test: Full system end-to-end.

**Integration & Testing Milestones**: After each phase, deploy to local/Docker, run end-to-end tests (including registration chatbot, CV upload, agent workflow, and saved jobs/keywords), and gather feedback.

### Better Instructing Your Coding LLM to Reduce Errors
To ensure accurate implementation, especially for the registration chatbot and multi-agent workflow:

#### 1. **Use Incremental, Focused Prompts**
   - For Sub-stage 1.5, provide: "Here's the PRD section on the registration chatbot: [paste 3.4]. Implement WebSocket endpoint and multi-agent workflow (Parser, Feedback, Validator, Writer) using CrewAI and PyMuPDF."
   - Example Prompt:
     ```
     You are an expert Python/FastAPI developer. Relevant PRD: [Paste Sub-stage 1.5 and 3.4 details].

     Existing code: [Paste main.py snippet, resume_parser.py].

     Task: Add /api/onboarding-chat WebSocket, integrate PyMuPDF for CV parsing, and CrewAI for agent workflow. Output: Updated files, explanation, unit tests.

     Best practices: Use Gemini for extraction; target 70% pre-fill, 30% via 3-5 questions; add toggles for clusters; convert ObjectIds to strings [paste example from note].
     ```

#### 2. **Encourage Chain of Thought**
   - Add: "Step-by-step: 1. Validate temp_token. 2. Parse CV with PyMuPDF. 3. Run agent workflow (parse, score, validate, write). 4. Store temp profile. 5. Transfer to profiles_collection. 6. Handle ObjectId conversion."

#### 3. **Provide Clear Guidelines**
   - Specify: "Use PyMuPDF for PDF text extraction; CrewAI for agents; aim for 15-20 cluster items; implement toggles per cluster table; handle voice inputs with Google Cloud Speech."

#### 4. **Iterate and Verify**
   - Test with: "Run with mock CV: [provide sample]. Verify profile data, toggles, and chat responses."

#### 5. **Handle Pitfalls**
   - For chatbot: "Ensure subtle CV prompts; limit to 5-10 exchanges; handle no-CV case with fallback questions."
   - For ObjectId: "Apply this solution: [paste note] to all DB fetches."

