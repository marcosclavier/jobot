import pytest
from unittest.mock import patch, MagicMock
import json
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import generate_application_materials, extract_questions_from_description
from google.api_core import exceptions as google_exceptions

@pytest.fixture
def mock_job_data():
    """Fixture for a sample job data structure."""
    return {
        "job_details": {
            "title": "Software Engineer",
            "full_description": "<p>We are looking for a great developer.</p><ul><li>Do you have 5 years of experience?</li></ul>",
            "company": {"display_name": "Test Corp"}
        }
    }

@pytest.fixture
def mock_profile_data():
    """Fixture for a sample user profile."""
    return {
        "skills": ["Python", "JavaScript"],
        "experience_summary": "I am a developer."
    }

@pytest.fixture
def mock_gemini_response():
    """Fixture for a mocked Gemini API response for material generation."""
    return {
        "cover_letter": "Dear Hiring Manager...",
        "resume_suggestions": ["Add 'Teamwork' to your skills."],
        "question_answers": [{
            "question": "Do you have 5 years of experience?",
            "answer": "Yes, I have over 5 years of relevant experience."
        }]
    }

@patch('bot.genai.GenerativeModel')
def test_generate_application_materials_success(mock_generative_model, mock_job_data, mock_profile_data, mock_gemini_response):
    """Test the successful generation of application materials."""
    mock_model_instance = mock_generative_model.return_value
    mock_model_instance.generate_content.return_value.text = json.dumps(mock_gemini_response)

    result = generate_application_materials(mock_job_data, mock_profile_data)

    assert result is not None
    assert 'generated_materials' in result
    assert result['generated_materials'] == mock_gemini_response
    mock_generative_model.assert_called_with('gemini-1.5-pro')

@patch('bot.genai.GenerativeModel')
def test_generate_application_materials_quota_exceeded(mock_generative_model, mock_job_data, mock_profile_data):
    """Test handling of API resource exhausted errors."""
    mock_model_instance = mock_generative_model.return_value
    mock_model_instance.generate_content.side_effect = google_exceptions.ResourceExhausted("Quota exceeded")

    result = generate_application_materials(mock_job_data, mock_profile_data)

    assert result is None

def test_extract_questions_from_description():
    """Test the extraction of questions from HTML content."""
    html = """
    <div>
        <p>This is a job description.</p>
        <ul>
            <li>What is your greatest strength?</li>
            <li>Please describe your experience with Python.</li>
            <li>This is not a question.</li>
        </ul>
        <p>Why do you want to work here?</p>
    </div>
    """
    questions = extract_questions_from_description(html)
    assert len(questions) == 2
    assert "What is your greatest strength?" in questions
    assert "Why do you want to work here?" in questions
