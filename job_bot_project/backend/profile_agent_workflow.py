import os
import json
import re
import asyncio
from dotenv import load_dotenv
from crewai import Agent, Task, Crew, Process, LLM
from pydantic import BaseModel, Field

# Load environment variables from .env file
load_dotenv()

# LiteLLM, which CrewAI uses, expects GEMINI_API_KEY.
# We set it from the existing GOOGLE_API_KEY.
gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
if gemini_api_key:
    os.environ["GEMINI_API_KEY"] = gemini_api_key
else:
    raise ValueError("Missing GOOGLE_API_KEY or GEMINI_API_KEY in .env file")

class Metadata(BaseModel):
    include: bool = Field(default=True, description="Whether to include this cluster.")
    omission_reason: str = Field(default="", description="Reason for omission if include is False.")

class Cluster(BaseModel):
    data: dict = Field(description="The data for this cluster.")
    metadata: Metadata = Field(description="Metadata for the cluster.")

class EnhancedProfile(BaseModel):
    name: str = Field(description="The applicant's full name.")
    contact_info: dict = Field(description="A dictionary with 'phone', 'email', 'linkedin' keys (use '' if not found).")
    enhanced_skills: list[str] = Field(description="A list of key skills and technologies.")
    experience_summary: str = Field(description="A brief summary of professional experience.")
    suggested_keywords: list[str] = Field(description="A list of 10-15 suggested keywords for job searching.")
    salary_range: str = Field(description="A suggested salary range (e.g., '$100,000 - $120,000 USD').")
    clusters: dict[str, Cluster] = Field(description="Dictionary of clusters like 'education', 'work_experience', etc.")

class FeedbackOutput(BaseModel):
    questions: list[str] = Field(description="A list of questions to ask the user to enrich their profile.")

async def run_agent_workflow(parsed_data: dict) -> dict:
    """
    Runs the CrewAI agent workflow to process parsed CV data.
    """
    try:
        # Use CrewAI's built-in LLM with LiteLLM support for Gemini
        llm = LLM(model="gemini/gemini-1.5-flash", temperature=0.7)

        # Define Agents with the configured LLM
        parser_agent = Agent(
            role='Parser',
            goal='Extract and structure information from CV data into predefined JSON clusters.',
            backstory='An expert in parsing structured and unstructured text to extract key information accurately.',
            llm=llm,
            verbose=True
        )
        feedback_agent = Agent(
            role='Feedback Provider',
            goal='Analyze the extracted profile for completeness and identify potential biases or areas for improvement.',
            backstory='A seasoned resume reviewer with an eye for detail and quality, ensuring profiles are fair and professional.',
            llm=llm,
            verbose=True
        )
        validator_agent = Agent(
            role='Validator',
            goal='Cross-verify data consistency, handle data toggles for privacy, and ensure the final output adheres to the required JSON schema.',
            backstory='A meticulous data validator focused on authenticity, user privacy, and ensuring the output is perfectly structured for ATS compatibility.',
            llm=llm,
            verbose=True
        )
        writer_agent = Agent(
            role='Profile Writer',
            goal='Refine summaries and prioritize the top 15-20 data points to create a compelling and concise professional profile.',
            backstory='A skilled writer who tailors professional profiles for different career levels and industries, highlighting the most impactful information.',
            llm=llm,
            verbose=True
        )

        # Define Tasks for the agents
        parse_task = Task(
            description=f"Parse the following data into a structured JSON format with clusters. Identify sensitive information like old dates and suggest omissions for privacy and bias reduction. Parsed data: {json.dumps(parsed_data)}",
            agent=parser_agent,
            expected_output='A JSON object containing the extracted information from the CV, organized into clusters like "education", "work_experience", etc.'
        )
        feedback_task = Task(
            description='Analyze the structured profile for completeness. Generate 3-5 targeted questions to fill any identified gaps and flag potential biases (e.g., ageism from graduation dates).',
            agent=feedback_agent,
            expected_output='A JSON object containing a completeness score (0-100), a list of questions for the user, and a list of any flagged potential biases. Ensure output is strictly valid JSON conforming to the schema without any additional text.',
            output_json=FeedbackOutput
        )
        validate_task = Task(
            description='Verify the consistency of the data and ensure the output structure for each cluster includes "data" and "metadata" fields. The metadata must handle privacy toggles.',
            agent=validator_agent,
            expected_output='A validated JSON object that is consistent and correctly structured, ready for final writing.'
        )
        write_task = Task(
            description='Compile the final profile into a single, clean JSON object. Each cluster must have a "data" object and a "metadata" object with an "include" boolean (defaulting to true) and an "omission_reason" string (if applicable). Output strictly as JSON matching the EnhancedProfile schema. Ensure output is strictly valid JSON conforming to the schema without any additional text.',
            agent=writer_agent,
            expected_output='A final, single JSON object representing the complete, refined, and validated user profile.',
            output_json=EnhancedProfile
        )

        # Create and run the crew
        crew = Crew(
            agents=[parser_agent, feedback_agent, validator_agent, writer_agent],
            tasks=[parse_task, feedback_task, validate_task, write_task],
            process=Process.sequential,
            verbose=True
        )

        # Execute the workflow
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, crew.kickoff)

        # The result object contains the output of all tasks.
        # Access the .json_dict attribute for tasks with Pydantic models.
        final_profile = result.tasks_output[-1].json_dict
        feedback_output = result.tasks_output[1].json_dict

        questions = feedback_output.get('questions', [])

        return {
            "profile": final_profile,
            "questions": questions
        }

    except Exception as e:
        print(f"An error occurred in the agent workflow: {e}")
        raise