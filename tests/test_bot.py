
import pytest
from unittest.mock import patch, mock_open, PropertyMock
import sys
import os
import json
from cryptography.fernet import Fernet

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot import (
    parse_resume,
    enhance_profile_with_gemini,
    validate_profile,
    encrypt_data,
    decrypt_data,
    has_profile_changed,
    update_profile_hash,
    get_file_hash
)

# --- Fixtures ---

@pytest.fixture
def mock_gemini_response():
    """Fixture to mock the Gemini API response."""
    return {
        "enhanced_skills": ["Python", "Pytest", "Mocking"],
        "experience_summary": "A skilled developer with experience in testing.",
        "suggested_keywords": ["Software Engineer", "Test Automation"],
        "salary_range": "$120,000 - $150,000 USD"
    }

@pytest.fixture
def temp_files(tmp_path):
    """Fixture to create temporary files for testing."""
    profile_path = tmp_path / "profile.json"
    hash_path = tmp_path / ".profile_hash"
    return str(profile_path), str(hash_path)

# --- Test Cases ---

def test_parse_resume_unsupported_format():
    """Test that parse_resume returns None for unsupported file types."""
    with patch('os.path.exists', return_value=True):
        assert parse_resume("test.txt") is None

def test_parse_resume_nonexistent_file():
    """Test that parse_resume returns None for a file that does not exist."""
    with patch('os.path.exists', return_value=False):
        assert parse_resume("nonexistent.pdf") is None

@patch('bot.genai.GenerativeModel')
def test_enhance_profile_with_gemini(mock_generative_model, mock_gemini_response):
    """Test the Gemini profile enhancement function with a mocked API call."""
    # Mock the chain of calls to get to the response object
    mock_model_instance = mock_generative_model.return_value
    # Use PropertyMock for the 'text' attribute
    type(mock_model_instance.generate_content.return_value).text = PropertyMock(return_value=json.dumps(mock_gemini_response))

    resume_text = "Experienced Python developer..."
    result = enhance_profile_with_gemini(resume_text)

    assert result == mock_gemini_response
    mock_generative_model.assert_called_with('gemini-1.5-flash')
    mock_model_instance.generate_content.assert_called_once()

def test_profile_validation():
    """Test the profile validation logic."""
    assert validate_profile({"skills": ["Python"], "location": "remote"}) is True
    assert validate_profile({"skills": ["Python"]}) is False
    assert validate_profile({"location": "remote"}) is False
    assert validate_profile({}) is False

def test_encryption_decryption():
    """Test that data can be encrypted and decrypted successfully."""
    key = Fernet.generate_key()
    original_text = "This is a secret message."
    
    encrypted = encrypt_data(original_text, key)
    assert isinstance(encrypted, bytes)
    
    decrypted = decrypt_data(encrypted, key)
    assert decrypted == original_text

def test_change_detection(temp_files):
    """Test the profile change detection mechanism."""
    profile_path, hash_path = temp_files
    
    # Initially, no hash file exists
    with patch('bot.PROFILE_FILE', profile_path), patch('bot.PROFILE_HASH_FILE', hash_path):
        with open(profile_path, "w") as f:
            f.write("initial content")
        
        assert has_profile_changed() is True
        
        # Update the hash
        update_profile_hash()
        
        # Now, it should not have changed
        assert has_profile_changed() is False
        
        # Modify the profile
        with open(profile_path, "w") as f:
            f.write("modified content")
            
        # It should now be marked as changed
        assert has_profile_changed() is True

def test_get_file_hash_nonexistent():
    """Test that get_file_hash returns None if the file doesn't exist."""
    assert get_file_hash("nonexistent/file.path") is None
