from crewai import Agent, Task, Crew, Process
from google.generativeai import GenerativeModel
import json
import asyncio

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
    parse_task = Task(description=f'Parse {parsed_data} into clusters. Identify sensitive info like old dates and suggest omissions.', agent=parser_agent)
    feedback_task = Task(description='Score profile completeness, generate 3-5 questions for gaps, and flag potential biases.', agent=feedback_agent)
    validate_task = Task(description='Verify data consistency and ensure the output structure for each cluster includes "data" and "metadata" fields.', agent=validator_agent)
    write_task = Task(
        description='Output the final profile as a single JSON object. Each cluster must have a "data" object and a "metadata" object. The metadata must contain an "include" boolean (default true) and an "omission_reason" string.',
        agent=writer_agent
    )

    crew = Crew(agents=[parser_agent, feedback_agent, validator_agent, writer_agent], tasks=[parse_task, feedback_task, validate_task, write_task], process=Process.sequential)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, crew.kickoff)

    # The agent workflow is now responsible for generating the correct JSON structure with toggles.
    return json.loads(result)
