### Step-by-Step Development Logic for Implementing the Registration Chatbot and Agent Workflow

Adding the registration chatbot with initial CV upload and an agent-based profile building workflow to your Job Bot backend involves enhancing the registration process in `main.py` with a WebSocket endpoint for conversational onboarding, integrating CV parsing (using PyMuPDF for PDF extraction), and creating a multi-agent system (inspired by CrewAI) for data refinement. This workflow ensures users start by uploading their CV (or LinkedIn/raw text), pre-fills 70% of clusters, then uses adaptive questioning (3-5 targeted prompts) to collect the remaining 30%, with options for omissions to avoid bias. The agents collaborate for validation, personalization, and optimization, targeting ~15-20 data points total.

The logic is modular: Handle uploads via existing `/api/cv-upload` (modified for temporary sessions during registration), parse/extract with PyMuPDF, refine via agents, and store in `profiles_collection`. Assume you'll install required packages: `pip install crewai pymupdf google-cloud-speech` (for speech-to-text; note: Google Cloud credentials needed). For CrewAI with Gemini, use a custom LLM wrapper (as CrewAI defaults to OpenAI but supports integration).<grok:render card_id="3afd5b" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">0</argument>
</grok:render><grok:render card_id="b3c866" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">25</argument>
</grok:render> Multi-modal (voice) uses Google Speech-to-Text for chat inputs.<grok:render card_id="723af5" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">21</argument>
</grok:render> Test for biases by allowing toggles and suggestions.<grok:render card_id="1196df" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">12</argument>
</grok:render>

#### Step 1: Prepare Dependencies and Configurations
- **Logic**: Add libraries for PDF parsing (PyMuPDF), agents (CrewAI), and speech-to-text. Define system prompts for the chatbot and agents. Create a temporary session mechanism for pre-login uploads (e.g., generate a short-lived token).
- **Code Changes in `main.py`**:
  - Add imports:
    ```python
    import fitz  # PyMuPDF for PDF extraction
    from crewai import Agent, Task, Crew, Process  # For multi-agent workflow
    from google.cloud import speech  # For speech-to-text (multi-modal)
    from google.generativeai import GenerativeModel  # For Gemini in agents
    import uuid  # For temporary session IDs
    ```
  - Define onboarding prompt (after SYSTEM_PROMPT if exists):
    ```python
    ONBOARDING_PROMPT = """
    You are the Job Bot Registration Coach. Start by asking the user to upload their CV (PDF/DOCX) or share LinkedIn/raw text. Once uploaded, confirm extraction and ask 3-5 targeted questions to fill gaps (e.g., 'Want to add achievements to your MIT degree? Omit year?'). Use clusters: name, contact_info, location, education, work_experience, enhanced_skills, etc. Suggest omissions for bias (e.g., hide dates if >15 years). Output extractions as [EXTRACT: cluster_key = {json}]. End with profile summary for review.
    """
    ```
  - Add temporary session collection:
    ```python
    temp_sessions_collection = db.temp_sessions  # For pre-login uploads
    ```

#### Step 2: Modify Registration for Chatbot Integration
- **Logic**: After email/password submission in `/api/register`, redirect to a chat session with a temporary token. The chatbot prompts for CV upload first. Use WebSocket for adaptive questionnaire, parsing inputs (text/voice).
- **Code Changes in `main.py`**:
  - Update `/api/register` to generate temp token and return it:
    ```python
    @app.post("/api/register")
    @limiter.limit("5/minute")
    async def register(request: Request, user: UserCreate):
        # Existing code...
        temp_token = str(uuid.uuid4())
        await temp_sessions_collection.insert_one({"token": temp_token, "email": user.email, "expires": datetime.utcnow() + timedelta(minutes=30)})
        return {"message": "User registered. Start onboarding chat with token.", "temp_token": temp_token}
    ```
  - Add onboarding WebSocket (no full auth; validate temp token):
    ```python
    @app.websocket("/api/onboarding-chat")
    async def onboarding_chat(websocket: WebSocket, temp_token: str = Query(...)):
        await websocket.accept()
        # Validate temp session
        session = await temp_sessions_collection.find_one({"token": temp_token})
        if not session or session["expires"] < datetime.utcnow():
            await websocket.close(code=1008, reason="Invalid or expired session")
            return
        # Load temp history if any
        history = []  # Or load from temp collection
        try:
            while True:
                data = await websocket.receive_text()
                # Handle multi-modal: If voice, transcribe (example below)
                if data.startswith("voice:"):  # Assume client prefixes voice data
                    transcribed = await transcribe_voice(data.split(":", 1)[1])  # Define function
                    data = transcribed
                history.append({"role": "user", "parts": [{"text": data}]})
                gemini_content = [{"role": "model", "parts": [{"text": ONBOARDING_PROMPT}]}] + history
                model = GenerativeModel('gemini-1.5-flash')
                response = model.generate_content(gemini_content)
                assistant_msg = response.text
                await websocket.send_text(assistant_msg)
                history.append({"role": "model", "parts": [{"text": assistant_msg}]})
                # Parse extractions and store in temp profile
                extract_match = re.search(r'\[EXTRACT: (\w+) = (.*?)\]', assistant_msg, re.DOTALL)
                if extract_match:
                    key = extract_match.group(1)
                    value = json.loads(extract_match.group(2))
                    await temp_sessions_collection.update_one({"token": temp_token}, {"$set": {f"profile.{key}": value}})
        except WebSocketDisconnect:
            # On completion, move temp profile to real user
            user = await users_collection.find_one({"email": session["email"]})
            temp_profile = await temp_sessions_collection.find_one({"token": temp_token})
            if temp_profile.get("profile"):
                await profiles_collection.insert_one({"user_id": user["_id"], **temp_profile["profile"]})
            await temp_sessions_collection.delete_one({"token": temp_token})
    ```
- **Frontend Note**: In `register.html`, after form submit, connect WebSocket with temp_token and add file upload button linked to a temp upload endpoint (see Step 3).

#### Step 3: Enhance CV Upload for Temporary Sessions and Parsing
- **Logic**: Allow pre-login uploads with temp_token. Use PyMuPDF to extract text/data from PDFs (e.g., identify sections like "Education" via regex/NLP). Pre-fill 70% of clusters, then trigger agent workflow for refinement.<grok:render card_id="b8ccd5" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">10</argument>
</grok:render><grok:render card_id="52c690" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">12</argument>
</grok:render>
- **New Function for Parsing** (add to `resume_parser.py` or inline):
  ```python
  def parse_resume_with_pymupdf(file_path):
      doc = fitz.open(file_path)
      text = ""
      for page in doc:
          text += page.get_text()
      # Simple NLP to extract clusters (improve with regex or Gemini)
      education_match = re.search(r'Education\s*(.*?)\s*Experience', text, re.DOTALL | re.IGNORECASE)
      education = {"institution": "Extracted", "degree": "Extracted"} if education_match else {}
      # Similar for other clusters
      return {"raw_text": text, "education": education, "work_experience": [...]}  # Return dict for agents
  ```
- **Modify `/api/cv-upload` for Temp Sessions**:
  ```python
  @app.post("/api/cv-upload")
  async def cv_upload(request: Request, file: UploadFile = File(...), temp_token: Optional[str] = Query(None), current_user: dict = Depends(get_current_user, use_cache=False)):
      if temp_token:
          session = await temp_sessions_collection.find_one({"token": temp_token})
          if not session:
              raise HTTPException(401, "Invalid session")
          user_id = temp_token  # Use as temp ID
      else:
          user_id = current_user["_id"]
      # Existing file handling...
      parsed_data = parse_resume_with_pymupdf(temp_file_path)
      enhanced_data = await run_agent_workflow(parsed_data)  # Call agents (Step 4)
      if temp_token:
          await temp_sessions_collection.update_one({"token": temp_token}, {"$set": {"profile": enhanced_data}})
      else:
          await profiles_collection.update_one({"user_id": user_id}, {"$set": enhanced_data}, upsert=True)
      return {"message": "CV processed. Continue in chat for refinements."}
  ```

#### Step 4: Implement Multi-Agent Workflow for Profile Refinement
- **Logic**: Use CrewAI-inspired agents: Parser (pre-fill), Feedback (score completeness, suggest questions), Validator (cross-verify, handle omissions), Writer (summarize, mimic style). Integrate Gemini as LLM. Target high-impact areas; allow toggles for clusters (store as {"include": bool, "value": data}).<grok:render card_id="6db289" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">0</argument>
</grok:render><grok:render card_id="ad3492" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">2</argument>
</grok:render> For adaptive questionnaires, agents generate branching prompts based on industry/level.
- **New File: `profile_agent_workflow.py`** (import in `main.py`):
  ```python
  from crewai import Agent, Task, Crew
  class GeminiLLM:
      def __init__(self):
          self.model = GenerativeModel('gemini-1.5-pro')
      def __call__(self, prompt):
          return self.model.generate_content(prompt).text

  async def run_agent_workflow(parsed_data):
      llm = GeminiLLM()
      # Agents
      parser_agent = Agent(role='Parser', goal='Extract and pre-fill clusters from parsed data', backstory='Expert in CV data extraction', llm=llm)
      feedback_agent = Agent(role='Feedback', goal='Score completeness, suggest gaps/omissions', backstory='Resume reviewer for bias and quality', llm=llm)
      validator_agent = Agent(role='Validator', goal='Cross-verify with user style/industry, handle toggles', backstory='Ensures authenticity and ATS-fit', llm=llm)
      writer_agent = Agent(role='Writer', goal='Refine summaries, prioritize 15-20 items', backstory='Tailors to levels/industries', llm=llm)
      
      # Tasks
      parse_task = Task(description=f'Parse {parsed_data} into clusters, suggest omissions (e.g., hide graduation_year if >15 years)', agent=parser_agent)
      feedback_task = Task(description='Score profile (aim 90% complete), generate 3-5 questions for gaps, flag biases per cluster table', agent=feedback_agent)
      validate_task = Task(description='Verify data, add toggles (e.g., "include": true), adapt questionnaire branching', agent=validator_agent)
      write_task = Task(description='Output refined profile with summaries, keywords, mimicking user style', agent=writer_agent)
      
      crew = Crew(agents=[parser_agent, feedback_agent, validator_agent, writer_agent], tasks=[parse_task, feedback_task, validate_task, write_task], process=Process.sequential)
      result = await crew.kickoff()  # Async for FastAPI
      # Post-process: Add toggles, e.g., for education: if graduation_year > datetime.now().year - 15: suggest hide
      refined_profile = json.loads(result)  # Assume JSON output
      for cluster in ['education', 'work_experience', ...]:  # From your table
          if cluster in refined_profile:
              refined_profile[cluster]['include'] = True  # Default; user toggles via chat
      return refined_profile
  ```
- **Integration**: Call in upload/parsing; use feedback_task outputs to generate chat prompts.

#### Step 5: Add Multi-Modal Support (Voice Input)
- **Logic**: For diverse inputs, add speech-to-text in chat. Use Google Cloud Speech for real-time transcription.<grok:render card_id="55ff37" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">20</argument>
</grok:render>
- **New Function in `main.py`**:
  ```python
  async def transcribe_voice(audio_data: str):  # Assume base64 audio from client
      client = speech.SpeechAsyncClient()
      config = speech.RecognitionConfig(encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16, sample_rate_hertz=16000, language_code="en-US")
      audio = speech.RecognitionAudio(content=base64.b64decode(audio_data))
      response = await client.recognize(config=config, audio=audio)
      return response.results[0].alternatives[0].transcript if response.results else ""
  ```

#### Step 6: Handle Cluster Omissions and Toggles
- **Logic**: In agents/chat, flag risks per your table (e.g., auto-suggest hide for old dates). Store clusters with 'include' flag and 'omission_reason'.
- **UI/Frontend**: In registration chat, show preview with checkboxes for toggles; send edits back to update profile.

#### Step 7: Test and Deploy
- **Testing**: Simulate upload/chat; verify 70% pre-fill, refinements. Use code_execution tool internally for snippets.
- **Edge Cases**: No CV (fall back to questionnaire); voice failures; bias flags.
- **Deployment**: Restart server; monitor Gemini costs.

This workflow creates comprehensive, bias-aware profiles, yielding 20-30% better ATS CVs.<grok:render card_id="f8ad6b" card_type="citation_card" type="render_inline_citation">
<argument name="citation_id">26</argument>
</grok:render> Refine based on user testing.