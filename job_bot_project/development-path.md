### Updated Breaking Stages for the PRD

I've updated the development sub-stages to incorporate the new feature: using saved jobs to extract keywords for refining job search API queries. This adds a new MongoDB collection (`saved_jobs`), keyword extraction logic (using AI like Gemini), new API endpoints (`POST /api/matches/{job_id}/save`, `GET /api/saved-jobs`, `DELETE /api/saved-jobs/{job_id}`), and UI enhancements (e.g., "Save" button and saved jobs section). These changes are integrated into Phase 2 sub-stages to keep the flow logical and incremental.

The overall structure remains the same (~12-15 sub-stages), but Phase 2 now has an extra sub-stage (2.4) for the saved jobs UI and keyword integration to avoid overloading any single task. This ensures the LLM can handle each sub-stage without complexity issues. As before, aim for testable deliverables per sub-stage.

#### Phase 1: Web Portal and Backend Foundation (Focus: Core setup and user basics)
- **Sub-stage 1.1: Backend Skeleton and Environment Setup**
  - Deliverables: Set up FastAPI project structure, integrate MongoDB (via motor), load .env configs, basic logging. Include setup for new collections like `saved_jobs` (alongside `users`, `profiles`, etc.).
  - Dependencies: None.
  - Why small: Pure boilerplate.
- **Sub-stage 1.2: User Authentication Endpoints**
  - Deliverables: Implement JWT auth with register/login endpoints (`POST /api/register`, `POST /api/login`), password hashing. Implement cookie-based token storage for web application sessions. Add password reset (`POST /api/password-reset`) and MFA setup if opting in.
  - Dependencies: Sub-stage 1.1.
  - Test: Manual API calls for user creation/login, verify cookie presence and validity.
- **Sub-stage 1.3: CV Upload and Profile Update Integration**
  - Deliverables: Add `POST /api/cv-upload` endpoint with file handling (limits: 5MB, PDF/DOCX), trigger `parse_resume` and `enhance_profile_with_gemini`, save to `profiles_collection` (leveraging `upsert=True` for updates). Update frontend (`dashboard.js`) to keep CV upload elements enabled and provide feedback for profile updates.
  - Dependencies: Sub-stage 1.2.
  - Test: Upload sample CVs, verify initial profile creation, then upload a different CV and verify profile update in database and UI feedback.
- **Sub-stage 1.4: Basic Frontend Pages**
  - Deliverables: Create responsive HTML/JS pages (register.html, login.html, index.html) with Tailwind CSS, form submissions to backend APIs.
  - Dependencies: Sub-stage 1.3.
  - Test: Local server run; ensure forms interact with backend.

#### Phase 2: Job Matching and Portal Dashboard (Focus: Matching logic, saved jobs, keyword extraction, and UI enhancements)
- **Sub-stage 2.1: Job Matching Service Integration**
  - Deliverables: Adapt `run_job_matching_for_all_users` as a scheduled service (e.g., daily via Celery or simple cron), source jobs from APIs (e.g., Indeed), store in `recommended_jobs_collection` with deduping/expiry logic. Add initial setup for keyword extraction: Create a function (e.g., in `job_matching_service.py` or new `job_keyword_extractor.py`) using Gemini to parse job descriptions for keywords (e.g., top 10 terms via TF-IDF or AI summary).
  - Dependencies: Phase 1 complete.
  - Test: Run manually for a test user; verify matches and sample keyword output in DB.
- **Sub-stage 2.2: Job Management API Endpoints**
  - Deliverables: Add `GET /api/matches`, `POST /api/matches/{job_id}/apply`, `DELETE /api/matches/{job_id}` with auth and personalization. Extend with saved jobs endpoints: `POST /api/matches/{job_id}/save` (store in `saved_jobs_collection` and trigger keyword extraction/aggregation), `GET /api/saved-jobs`, `DELETE /api/saved-jobs/{job_id}`.
  - Dependencies: Sub-stage 2.1.
  - Test: API queries for matches and saved jobs.
- **Sub-stage 2.3: Keyword Integration into Matching**
  - Deliverables: Update the matching service to aggregate keywords from all saved jobs in `saved_jobs_collection` (e.g., fetch, extract if not pre-stored, combine into query params like "python developer remote"), and use them to refine API searches (e.g., append to Indeed query). Ensure aggregation handles updates (e.g., re-extract on save/delete).
  - Dependencies: Sub-stage 2.2.
  - Test: Save sample jobs, run matching, verify refined queries and improved matches.
- **Sub-stage 2.4: Enhanced Dashboard UI**
  - Deliverables: Update index.html to display matches with filters, "Apply"/"Remove" buttons, tooltips, and feedback. Add "Save" button per listing (triggers `/api/matches/{job_id}/save`), and a separate tab/section for saved jobs (fetched from `/api/saved-jobs`) with apply/remove options.
  - Dependencies: Sub-stage 2.3.
  - Test: End-to-end: Upload CV, save jobs, run matching, view dashboard.

#### Phase 3: Chrome Extension Overhaul (Focus: Extension-backend integration)
- **Sub-stage 3.1: Extension Authentication Setup**
  - Deliverables: Update options.html/js for auth (prefer Chrome Identity API over token paste), link to user account.
  - Dependencies: Phase 2 complete.
  - Test: Install extension, authenticate.
- **Sub-stage 3.2: Profile Fetching and Caching**
  - Deliverables: Modify popup.js to fetch from `GET /api/me/profile`, add local caching for offline use.
  - Dependencies: Sub-stage 3.1.
  - Test: Load profile in extension popup.

#### Phase 4: On-Demand Document Generation (Focus: AI generation and form filling)
- **Sub-stage 4.1: Document Generation Endpoint**
  - Deliverables: Add `POST /api/jobs/{job_id}/generate-documents` using Gemini functions, return blobs (PDF/DOCX), support ATS formats and non-matched jobs via URL/details.
  - Dependencies: Phase 3 complete.
  - Test: Call with sample job_id; download files.
- **Sub-stage 4.2: Extension Form Filling Logic**
  - Deliverables: Update "Fill Form" to call generation API, fill fields, handle uploads (downloads + prompts).
  - Dependencies: Sub-stage 4.1.
  - Test: On a mock job page.
- **Sub-stage 4.3: Final Integrations and Polish**
  - Deliverables: Add rate limiting, monitoring (Sentry), testing (Pytest), and compliance checks. Verify keyword extraction doesn't increase AI costs excessively (e.g., cache extracted keywords per job).
  - Dependencies: All prior.
  - Test: Full system e2e.

After each phase, include an "Integration & Testing" milestone: Deploy to local/Docker, run end-to-end tests (now including save/keyword flows), and gather feedback.

### Better Instructing Your Coding LLM to Reduce Errors

The advice from before remains relevant, but with the added complexity of keyword extraction, emphasize these tweaks:

#### 1. **Use Incremental, Focused Prompts**
   - For new sub-stages like 2.3, provide context like: "Here's the PRD section on keyword extraction: [paste relevant part]. Integrate it into the matching service without altering existing logic."
   - Example Prompt:
     ```
     You are an expert Python/FastAPI developer. Relevant PRD: [Paste Sub-stage 2.3 details].

     Existing code: [Paste job_matching_service.py snippet].

     Task: Add keyword aggregation from saved_jobs_collection and refine API queries. Output: Updated files, explanation, unit tests.

     Best practices: Use Gemini for extraction; cache keywords to avoid repeated AI calls.
     ```

#### 2. **Encourage Chain of Thought**
   - Add: "Step-by-step: 1. Fetch saved jobs. 2. Extract keywords per job. 3. Aggregate uniquely. 4. Append to search query."

#### 3. **Provide Clear Guidelines**
   - Specify: "For keyword extraction, adapt gemini_services; aim for 5-15 terms per job; handle empty saved jobs gracefully."

#### 4. **Iterate and Verify**
   - After outputs involving AI (e.g., extraction), test with sample data: "Run this code with mock saved jobs: [provide mocks]."

#### 5. **Handle Pitfalls**
   - For the new feature: "Ensure extraction is efficient—prompt for batch processing if many saved jobs."

This updated breakdown keeps tasks manageable while fully integrating the saved jobs/keywords feature. If you need a sample prompt for a specific sub-stage, let me know!

### Development Note: Handling MongoDB ObjectId Serialization

**Issue:** When fetching data directly from MongoDB and returning it from a FastAPI endpoint, a `500 Internal Server Error` can occur. The traceback reveals a `TypeError`, stating that an `ObjectId` object is not JSON serializable.

**Root Cause:** MongoDB uses a special BSON `ObjectId` type for its document IDs (e.g., `_id`, `user_id`). FastAPI's default JSON encoder does not know how to convert this special type into a string, causing the serialization to fail.

**Solution:** Before returning any document fetched from MongoDB as a response, you **must** manually convert all fields containing `ObjectId` instances into strings. This ensures the data is in a format that can be correctly serialized to JSON.

**Incorrect (Fails):**
```python
@app.get("/api/some-route/{item_id}")
async def get_item(item_id: str):
    item = await my_collection.find_one({"_id": ObjectId(item_id)})
    return item # This will fail if item contains ObjectIds
```

**Correct (Works):**
```python
@app.get("/api/some-route/{item_id}")
async def get_item(item_id: str):
    item = await my_collection.find_one({"_id": ObjectId(item_id)})
    if item:
        # Convert all relevant ObjectId fields to strings
        if "_id" in item:
            item["_id"] = str(item["_id"])
        if "user_id" in item: # Check for other potential ObjectId fields
            item["user_id"] = str(item["user_id"])
        return item
    raise HTTPException(status_code=404, detail="Item not found")
```

**Rule of Thumb:** Always assume that any data coming from a MongoDB query might contain `ObjectId`s. Explicitly check for and convert them before sending the data to the frontend to prevent this common error.