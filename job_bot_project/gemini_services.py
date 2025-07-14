import json
import logging
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions
from bs4 import BeautifulSoup

def enhance_profile_with_gemini(resume_text):
    """
    Uses Gemini to enhance the user profile based on resume text.

    Args:
        resume_text (str): The extracted text content from the user's resume.

    Inputs:
        - resume_text (str): Text content of the resume.
        - Gemini API (gemini-1.5-flash model).

    Returns:
        dict or None: A dictionary containing enhanced profile data (enhanced_skills, experience_summary,
                      suggested_keywords, salary_range) if successful, None otherwise.
    """
    if not resume_text:
        logging.error("Cannot enhance profile, resume text is empty.")
        return None
    
    logging.info("Calling Gemini to enhance profile...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analyze the following resume text and extract key information to create a professional profile.
        Based on the skills and experience, suggest a realistic salary range.
        Also, suggest a list of additional job search keywords (synonyms or related technologies).

        Resume Text:
        ---
        {resume_text}
        ---

        Return the output as a JSON object with the following keys:
        - "name": The full name of the applicant.
        - "contact_info": A dictionary with "email", "phone", and "linkedin" (URL).
        - "education": A list of educational entries, each with "institution", "degree", "field_of_study", and "graduation_year".
        - "work_experience": A list of work experiences, each with "company", "title", "start_date", "end_date", and "responsibilities" (a list of strings).
        - "enhanced_skills": A list of key skills and technologies found.
        - "experience_summary": A brief summary of the professional experience.
        - "suggested_keywords": A list of 10-15 suggested keywords for job searching.
        - "salary_range": A suggested salary range (e.g., "$100,000 - $120,000 USD").

        Example JSON output:
        {{
          "name": "John Doe",
          "contact_info": {{"email": "john.doe@example.com", "phone": "123-456-7890", "linkedin": "https://linkedin.com/in/johndoe"}},
          "education": [
            {{"institution": "University of Example", "degree": "M.Sc.", "field_of_study": "Computer Science", "graduation_year": "2020"}}
          ],
          "work_experience": [
            {{"company": "Tech Solutions Inc.", "title": "Software Engineer", "start_date": "Jan 2021", "end_date": "Present", "responsibilities": ["Developed scalable web applications", "Collaborated with cross-functional teams"]}}
          ],
          "enhanced_skills": ["Python", "Data Analysis", "Machine Learning", "SQL"],
          "experience_summary": "A data scientist with 5 years of experience...",
          "suggested_keywords": ["Data Scientist", "Python Developer", "AI Engineer"],
          "salary_range": "$110,000 - $135,000 USD"
        }}
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        logging.info("Successfully enhanced profile with Gemini.")
        return json.loads(cleaned_response)
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Error enhancing profile with Gemini: {e}", exc_info=True)
        return None

def expand_keywords_with_gemini(base_keywords):
    """
    Expands a list of keywords using Gemini for better search results.

    Args:
        base_keywords (list): A list of initial keywords (e.g., skills from the user's profile).

    Inputs:
        - base_keywords (list): List of keywords to expand.
        - Gemini API (gemini-1.5-flash model).

    Returns:
        list: A combined list of original and expanded keywords, with duplicates removed.
    """
    logging.info("Calling Gemini to expand keywords...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Given the following list of skills, generate a list of 20-30 related and synonymous keywords to improve job search results.
        Return only a comma-separated list of keywords.

        Skills: {', '.join(base_keywords)}
        """
        response = model.generate_content(prompt)
        expanded_keywords = [k.strip() for k in response.text.split(',')]
        logging.info("Successfully expanded keywords with Gemini.")
        return list(set(base_keywords + expanded_keywords)) # Combine and remove duplicates
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded: {e}", exc_info=True)
        return base_keywords
    except Exception as e:
        logging.error(f"Error expanding keywords with Gemini: {e}", exc_info=True)
        return base_keywords # Fallback to original keywords

def extract_questions_from_description(html_content):
    """
    Extracts potential application questions from a job description's HTML content.
    Looks for sentences ending with a question mark within list items or paragraphs.

    Args:
        html_content (str): The HTML content of the job description.

    Inputs:
        - html_content (str): HTML string of the job description.

    Returns:
        list: A list of strings, where each string is a potential question.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    questions = []
    for tag in soup.find_all(['li', 'p']):
        if tag.get_text(strip=True).endswith('?'):
            questions.append(tag.get_text(strip=True))
    return questions

def generate_application_materials(job_data, profile, custom_prompt=""):
    """
    Generates cover letter, resume suggestions, and answers to questions for a job
    using the Gemini API, tailored to the user's profile and job details.

    Args:
        job_data (dict): A dictionary containing job details, including 'job_details' and 'full_description'.
        profile (dict): The user's profile data.
        custom_prompt (str, optional): Additional instructions for Gemini. Defaults to "".

    Inputs:
        - job_data (dict): Job details (title, full_description, etc.).
        - profile (dict): User's professional profile.
        - custom_prompt (str): Optional custom instructions for generation.
        - Gemini API (gemini-1.5-pro model).

    Returns:
        dict or None: The updated job_data dictionary including 'generated_materials' if successful, None otherwise.
    """
    job_title = job_data.get('job_details', {}).get('title', 'N/A')
    logging.info(f"Generating materials for: {job_title}")

    job_description = job_data.get('job_details', {}).get('full_description', '')
    questions = extract_questions_from_description(job_description)

    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        prompt = (
            "**Objective:** Generate tailored application materials for a job applicant.\n\n"
            "**Applicant Profile:**\n"
            f"{json.dumps(profile, indent=2)}\n\n"
            "**Job Details:**\n"
            f"{json.dumps(job_data['job_details'], indent=2)}\n\n"
            "**Custom Instructions:**\n"
            f"{custom_prompt if custom_prompt else 'No custom instructions provided.'}\n\n"
            "**Tasks:**\n"
            "1.  **Cover Letter:** Write a professional, enthusiastic, and tailored cover letter. It should highlight the applicant\'s most relevant skills and experiences from their profile that match the job description. Incorporate any custom instructions provided.\n"
            "2.  **Resume Adjustments:** Provide a list of specific, actionable suggestions for optimizing the applicant\'s resume for this job. Focus on incorporating keywords from the job description and aligning the experience summary with the role\'s requirements. Incorporate any custom instructions.\n"
            "3.  **Answer Questions:** If there are questions below, provide thoughtful and detailed answers based on the applicant\'s profile.\n\n"
            "**Application Questions:**\n"
            f"{json.dumps(questions) if questions else 'No specific questions found.'}\n\n"
            "**Output Format:**\n"
            'Return a single JSON object with three keys: "cover_letter", "resume_suggestions", and "question_answers".\n'
            '- `cover_letter`: A string containing the full text of the cover letter.\n'
            '- `resume_suggestions`: A list of strings, where each string is a specific suggestion.\n'
            '- `question_answers`: A list of objects, each with "question" and "answer" keys.'
        )

        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')

        generated_materials = json.loads(cleaned_response)
        job_data['generated_materials'] = generated_materials

        logging.info(f"Successfully generated materials for: {job_title}")
        return job_data
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded while generating materials for {job_title}: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Error generating materials for {job_title}: {e}", exc_info=True)
        return None

# --- Material Refinement ---
def simulate_ats_score(job_details, materials):
    """
    Simulates an ATS (Applicant Tracking System) score by matching keywords
    from the job description with the generated application materials.

    Args:
        job_details (dict): A dictionary containing the job's details, including 'full_description'.
        materials (dict): A dictionary containing the generated application materials (cover_letter, refined_resume, resume_suggestions).

    Inputs:
        - job_details (dict): Job description to extract keywords from.
        - materials (dict): Application materials to check for keywords.
        - Gemini API (gemini-1.5-flash model).

    Returns:
        dict: A dictionary with 'score' (percentage match), 'matched_keywords', and 'missing_keywords'.
    """
    logging.info("Simulating ATS score...")
    job_description = job_details.get('full_description', '')
    cover_letter = materials.get('cover_letter', '')
    resume_text = materials.get('refined_resume', ' '.join(materials.get('resume_suggestions', [])))
    full_text = cover_letter + ' ' + resume_text

    if not job_description or not full_text:
        return {"score": 0, "matched_keywords": [], "missing_keywords": []}

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        From the following job description, extract the 20 most important keywords and skills.
        Return them as a JSON list of strings.

        Job Description:
        ---
        {job_description[:4000]}
        ---
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        keywords = json.loads(cleaned_response)

        matched_keywords = {kw for kw in keywords if kw.lower() in full_text.lower()}
        missing_keywords = set(keywords) - matched_keywords
        score = (len(matched_keywords) / len(keywords) * 100) if keywords else 0

        logging.info(f"ATS simulation complete. Score: {score:.2f}%")
        return {
            "score": round(score, 2),
            "matched_keywords": list(matched_keywords),
            "missing_keywords": list(missing_keywords)
        }
    except Exception as e:
        logging.error(f"Error during ATS simulation: {e}", exc_info=True)
        return {"score": 0, "matched_keywords": [], "missing_keywords": []}

def validate_materials_with_gemini(materials):
    """
    Uses Gemini to validate the completeness and quality of application materials.
    Provides actionable suggestions for improvement.

    Args:
        materials (dict): A dictionary containing the generated application materials.

    Inputs:
        - materials (dict): Application materials to validate.
        - Gemini API (gemini-1.5-flash model).

    Returns:
        list: A list of strings, where each string is a validation feedback/suggestion.
    """
    logging.info("Calling Gemini to validate materials...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Please act as a career coach and review the following application materials.
        Provide a list of actionable suggestions for improvement.
        Focus on clarity, impact, and professionalism. Check for any incomplete sentences or sections.
        If "refined_resume" is present, review that full resume text; otherwise, review "resume_suggestions".

        Materials:
        ---
        {json.dumps(materials, indent=2)}
        ---

        Return a JSON object with a single key "validation_feedback", which is a list of strings.
        Example: {{"validation_feedback": ["The cover letter could be more specific about project X.", "Consider rephrasing the second resume suggestion for more impact."]}}
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        validation = json.loads(cleaned_response)
        logging.info("Successfully validated materials with Gemini.")
        return validation.get('validation_feedback', [])
    except Exception as e:
        logging.error(f"Error validating materials with Gemini: {e}", exc_info=True)
        return ["Failed to get validation from Gemini."]

def get_gemini_suggestions(text_to_improve, instruction):
    """
    Uses Gemini to improve a specific piece of text based on provided instructions.

    Args:
        text_to_improve (str): The original text to be improved.
        instruction (str): The instruction for Gemini on how to revise the text.

    Inputs:
        - text_to_improve (str): Original text.
        - instruction (str): Instructions for revision.
        - Gemini API (gemini-1.5-pro model).

    Returns:
        str: The revised text from Gemini, or an error message if the call fails.
    """
    logging.info("Calling Gemini for text improvement suggestions...")
    try:
        model = genai.GenerativeModel('gemini-1.5-pro') # Using pro for better writing
        prompt = f"""
        Please revise the following text based on the user's instruction.
        Return only the revised text, without any extra formatting or explanation.

        Original Text:
        ---
        {text_to_improve}
        ---

        Instruction: "{instruction}"
        """
        response = model.generate_content(prompt)
        logging.info("Successfully received suggestion from Gemini.")
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error getting suggestions from Gemini: {e}", exc_info=True)
        return "Failed to get suggestion from Gemini."

def apply_validation_feedback(materials, validation_feedback):
    """
    Uses Gemini to apply validation feedback to the application materials (cover letter and refined resume).

    Args:
        materials (dict): A dictionary containing the generated application materials.
        validation_feedback (list): A list of strings, where each string is a validation feedback/suggestion.

    Inputs:
        - materials (dict): Current application materials.
        - validation_feedback (list): Feedback from validation.
        - Gemini API (gemini-1.5-flash model).

    Returns:
        dict: The updated materials dictionary with revised cover_letter and refined_resume.
    """
    if not validation_feedback:
        logging.info("No validation feedback to apply.")
        return materials

    logging.info("Applying validation feedback with Gemini...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Current Materials:
        ---
        {json.dumps(materials, indent=2)}
        ---

        Validation Feedback:
        ---
        {json.dumps(validation_feedback, indent=2)}
        ---

        Revise the "cover_letter" and "refined_resume" to address all the feedback points. Make sure the revisions improve clarity, impact, professionalism, and incorporate any suggestions.

        Return a JSON object with keys "cover_letter" and "refined_resume", containing the revised texts.
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        try:
            revised = json.loads(cleaned_response)
            materials['cover_letter'] = revised.get('cover_letter', materials['cover_letter'])
            materials['refined_resume'] = revised.get('refined_resume', materials['refined_resume'])
            logging.info("Successfully applied feedback.")
            return materials
        except json.JSONDecodeError as json_e:
            logging.error(f"JSONDecodeError when applying validation feedback: {json_e}")
            logging.error(f"Problematic response: {cleaned_response}")
            return materials
    except Exception as e:
        logging.error(f"Error applying validation feedback: {e}", exc_info=True)
        return materials

# --- New Function for Refined Resume ---
def generate_refined_resume(profile, materials, job_data):
    """
    Uses Gemini to generate a refined resume based on the user's profile and resume suggestions.
    The generated resume is tailored to the specific job description.

    Args:
        profile (dict): The user's profile data.
        materials (dict): A dictionary containing generated application materials, including 'resume_suggestions'.
        job_data (dict): A dictionary containing job details, including 'job_details' and 'full_description'.

    Inputs:
        - profile (dict): User's professional profile.
        - materials (dict): Generated application materials with resume suggestions.
        - job_data (dict): Job details (full_description, title).
        - Gemini API (gemini-1.5-pro model).

    Returns:
        str: The full text of the refined resume, or an error message if generation fails.
    """
    suggestions = materials.get('resume_suggestions', [])
    job_description = job_data.get('job_details', {}).get('full_description', '')
    job_title = job_data.get('job_details', {}).get('title', 'N/A')
    
    logging.info(f"Generating refined resume for: {job_title}")
    
    try:
        model = genai.GenerativeModel('gemini-1.5-pro')
        prompt = f"""
        Applicant Profile:
        ---
        {json.dumps(profile, indent=2)}
        ---

        Job Description:
        ---
        {job_description[:4000]}
        ---

        Resume Suggestions:
        ---
        {json.dumps(suggestions, indent=2)}
        ---

        Task: Create a professional resume based on the applicant profile. Incorporate all the provided suggestions. Tailor it specifically to the job description, highlighting relevant skills and experiences. Ensure the resume is professional, concise, and optimized for ATS systems by including keywords from the job description.
        
        Return only the full text of the resume, without any additional explanations or formatting.
        """
        response = model.generate_content(prompt)
        refined_resume = response.text.strip()
        logging.info(f"Successfully generated refined resume for: {job_title}")
        return refined_resume
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded while generating refined resume for {job_title}: {e}", exc_info=True)
        return "Failed to generate refined resume due to API quota."
    except Exception as e:
        logging.error(f"Error generating refined resume for {job_title}: {e}", exc_info=True)
        return "Failed to generate refined resume."

def evaluate_job_fit(job, user_profile):
    """
    Evaluates job fit using Gemini and calculates a skill match percentage.

    Args:
        job (dict): A dictionary containing job details, including 'full_description' or 'description'.
        user_profile (dict): The user's profile data, including 'skills'.

    Inputs:
        - job (dict): Job details (full_description, description).
        - user_profile (dict): User's skills and other profile data.
        - Gemini API (gemini-1.5-flash model).

    Returns:
        dict or None: A dictionary with 'fit_score', 'explanation', 'summary',
                      'skill_match_percentage', and 'matched_skills' if successful, None otherwise.
    """
    job_description = job.get('full_description', job.get('description', ''))
    user_skills = set(skill.lower() for skill in user_profile.get('skills', []))
    
    found_skills = {skill for skill in user_skills if skill in job_description.lower()}
    skill_match_percentage = (len(found_skills) / len(user_skills) * 100) if user_skills else 0

    logging.info(f"Calling Gemini to evaluate job fit for: {job.get('title')}")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        User Profile: {json.dumps(user_profile, indent=2)}
        Job Description: {job_description}

        Based on the user profile and job description, perform the following tasks:
        1. Rate the job fit on a scale of 1-10.
        2. Provide a brief explanation for the rating.
        3. Write a concise one-paragraph summary of the job role and its key responsibilities.

        Return a JSON object with the keys: "fit_score", "explanation", and "summary".
        Example: {{"fit_score": 8, "explanation": "The role aligns well...", "summary": "This is a software engineering role..."}}
        """
        response = model.generate_content(prompt)
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        evaluation = json.loads(cleaned_response)
        
        evaluation['skill_match_percentage'] = round(skill_match_percentage, 2)
        evaluation['matched_skills'] = list(found_skills)
        
        logging.info(f"Successfully evaluated job fit for: {job.get('title')}")
        return evaluation
    except google_exceptions.ResourceExhausted as e:
        logging.error(f"Gemini API quota exceeded while evaluating job fit: {e}", exc_info=True)
        return None
    except Exception as e:
        logging.error(f"Error evaluating job fit with Gemini: {e}", exc_info=True)
        return None