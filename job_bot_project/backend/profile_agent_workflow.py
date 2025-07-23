import os
import json
import asyncio
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process
from pydantic import BaseModel, Field
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables from .env file
load_dotenv()

# Ensure the Google API key is available
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("Missing GOOGLE_API_KEY in .env file")

class Metadata(BaseModel):
    include: bool = Field(default=True, description="Whether to include this cluster.")
    omission_reason: str = Field(default="", description="Reason for omission if include is False.")

class Cluster(BaseModel):
    data: dict = Field(description="The data for this cluster.")
    metadata: Metadata = Field(description="Metadata for the cluster.")

class EnhancedProfile(BaseModel):
    name: str = Field(default="", description="The applicant's full name.")
    contact_info: dict = Field(default_factory=dict, description="A dictionary with 'phone', 'email', 'linkedin', 'location' keys (use '' if not found).")
    enhanced_skills: list[str] = Field(default_factory=list, description="A list of key skills and technologies.")
    experience_summary: str = Field(default="", description="A brief summary of professional experience.")
    suggested_keywords: list[str] = Field(default_factory=list, description="A list of 10-15 suggested keywords for job searching.")
    salary_range: str = Field(default="", description="A suggested salary range (e.g., '$100,000 - $120,000 USD').")
    clusters: dict[str, Cluster] = Field(default_factory=dict, description="Dictionary of clusters like 'education', 'work_experience', etc.")

class FeedbackOutput(BaseModel):
    questions: list[str] = Field(default_factory=list, description="A list of questions to ask the user to enrich their profile.")

async def run_agent_workflow(parsed_data: dict) -> dict:
    """
    Runs the CrewAI agent workflow to process parsed CV data.
    """
    print("--- RUNNING FINAL TEMPLATE-BASED APPROACH ---")
    
    try:
        # Define the shared LLM for the crew
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2) # Lowered temp for consistency

        # Define Agents
        parser_agent = Agent(
            role='Parser',
            goal='Extract and structure information from CV data into predefined JSON clusters.',
            backstory='An expert in parsing structured and unstructured text to extract key information accurately.',
            verbose=True,
            allow_delegation=False
        )
        feedback_agent = Agent(
            role='Feedback Provider',
            goal='Analyze the extracted profile for completeness and identify potential biases or areas for improvement.',
            backstory='A seasoned resume reviewer with an eye for detail and quality, ensuring profiles are fair and professional.',
            verbose=True,
            allow_delegation=False
        )
        validator_agent = Agent(
            role='Validator',
            goal='Cross-verify data consistency, handle data toggles for privacy, and ensure the final output adheres to the required JSON schema.',
            backstory='A meticulous data validator focused on authenticity, user privacy, and ensuring the output is perfectly structured for ATS compatibility.',
            verbose=True,
            allow_delegation=False
        )
        writer_agent = Agent(
            role='Profile Writer',
            goal='Refine summaries and prioritize the top 15-20 data points to create a compelling and concise professional profile.',
            backstory='A skilled writer who tailors professional profiles for different career levels and industries, highlighting the most impactful information.',
            verbose=True,
            allow_delegation=False
        )

        # --- REVISED TASKS WITH EXPLICIT TEMPLATES ---

        parse_task = Task(
            agent=parser_agent,
            expected_output="A single JSON object with all available information extracted from the text.",
            description=(
                "Parse the following resume text and extract the information into a JSON object. "
                "Your output must be only the JSON object. Do your best to fill in all fields, using empty strings or arrays if data is not found.\n\n"
                f"Resume Text:\n\"\"\"\n{json.dumps(parsed_data.get('raw_text', ''))}\n\"\"\""
            )
        )
        
        feedback_task = Task(
            agent=feedback_agent,
            expected_output="A JSON object with a 'questions' key containing a list of strings for the user.",
            output_pydantic=FeedbackOutput,
            description=(
                "Analyze the parsed resume data for completeness. Based on the data, generate 3-5 targeted questions "
                "to ask the user to enrich their profile. Focus on missing achievements, vague descriptions, or missing contact details."
            )
        )

        validate_task = Task(
            agent=validator_agent,
            expected_output="A validated and cleaned JSON object, ready for final compilation.",
            description=(
                "Review the parsed JSON data. Verify that all required fields ('name', 'contact_info', 'clusters', etc.) are present, even if empty. "
                "Ensure 'contact_info' is an object and 'clusters' contains 'work_experience' and 'education'. Correct any structural errors. "
                "Pass on the clean, validated JSON."
            )
        )

        write_task = Task(
            agent=writer_agent,
            expected_output="A single, complete, and valid JSON object that exactly matches the structure of the `EnhancedProfile` model.",
            output_pydantic=EnhancedProfile,
            description=(
                "Synthesize all the processed information from the previous steps into a final JSON profile. "
                "Your output MUST be only the single JSON object from the template below, filled with the provided information. "
                "Do not add any extra text, explanations, or markdown formatting around the JSON.\n\n"
                "**JSON TEMPLATE TO FILL:**\n"
                "```json\n"
                "{\n"
                "  \"name\": \"<The applicant's full name>\",\n"
                "  \"contact_info\": {\n"
                "    \"phone\": \"<phone number or ''>\",\n"
                "    \"email\": \"<email address or ''>\",\n"
                "    \"linkedin\": \"<linkedin URL or ''>\",\n"
                "    \"location\": \"<city, province or ''>\"\n"
                "  },\n"
                "  \"enhanced_skills\": [\"<skill 1>\", \"<skill 2>\"],\n"
                "  \"experience_summary\": \"<A 100-200 word professional summary>\",\n"
                "  \"suggested_keywords\": [\"<keyword 1>\", \"<keyword 2>\"],\n"
                "  \"salary_range\": \"<e.g., '$100,000 - $120,000 USD' or ''>\",\n"
                "  \"clusters\": {\n"
                "    \"work_experience\": {\n"
                "      \"data\": [\n"
                "        {\n"
                "          \"title\": \"<job title>\",\n"
                "          \"company\": \"<company name>\",\n"
                "          \"dates\": \"<dates of employment>\",\n"
                "          \"description\": \"<job description>\",\n"
                "          \"achievements\": [\"<achievement 1>\"]\n"
                "        }\n"
                "      ],\n"
                "      \"metadata\": {\"include\": true, \"omission_reason\": \"\"}\n"
                "    },\n"
                "    \"education\": {\n"
                "      \"data\": [\n"
                "        {\n"
                "          \"institution\": \"<institution name>\",\n"
                "          \"degree\": \"<degree or certificate>\",\n"
                "          \"dates\": \"<dates of attendance>\"\n"
                "        }\n"
                "      ],\n"
                "      \"metadata\": {\"include\": true, \"omission_reason\": \"\"}\n"
                "    }\n"
                "  }\n"
                "}\n"
                "```"
            )
        )

        # Create the crew
        crew = Crew(
            agents=[parser_agent, feedback_agent, validator_agent, writer_agent],
            tasks=[parse_task, feedback_task, validate_task, write_task],
            process=Process.sequential,
            llm=llm,
            verbose=True
        )

        # Execute the workflow
        loop = asyncio.get_event_loop()
        crew_output = await loop.run_in_executor(None, crew.kickoff)

        if not crew_output or not crew_output.tasks_output:
            raise Exception("The agent workflow did not return any task output.")

        # The final profile is the output of the last task
        final_profile_task_output = crew_output.tasks_output[-1]
        if not final_profile_task_output or not final_profile_task_output.pydantic:
            raise Exception("The final writing task did not return a valid profile.")
        final_profile = final_profile_task_output.pydantic

        # Optional: Add a fallback if Pydantic parsing failed (e.g., agent output was malformed JSON)
        if final_profile is None and final_profile_task_output.raw:
            try:
                final_profile_data = json.loads(final_profile_task_output.raw)
                final_profile = EnhancedProfile(**final_profile_data)
            except (json.JSONDecodeError, ValidationError) as e:
                raise Exception(f"Failed to parse final profile output: {e}")

        # The feedback questions are the output of the second task
        questions = []
        if len(crew_output.tasks_output) > 1:
            feedback_task_output = crew_output.tasks_output[1]
            if feedback_task_output and feedback_task_output.pydantic:
                questions = feedback_task_output.pydantic.questions
            # Optional: Fallback for feedback if needed
            elif feedback_task_output.raw:
                try:
                    feedback_data = json.loads(feedback_task_output.raw)
                    questions = FeedbackOutput(**feedback_data).questions
                except (json.JSONDecodeError, ValidationError):
                    pass  # Questions remain empty if parsing fails

        return {
            "profile": final_profile.model_dump() if final_profile else {},
            "questions": questions
        }

    except Exception as e:
        print(f"An error occurred in the agent workflow: {e}")
        raise