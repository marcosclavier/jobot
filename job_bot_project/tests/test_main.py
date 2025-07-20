import pytest
from unittest.mock import patch, mock_open
import json
import os
from click.testing import CliRunner

# Add project root to path to allow imports
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main import (
    cli, save_profile, generate_application_materials, export_docs,
    PROFILE_FILE
)
from file_utils import load_profile, save_json_file, load_json_file

# A valid base64-encoded 32-byte key
TEST_KEY = b'_B_4x7w2b2-n9BHj-s8pWn5-2X-c8c5bL7b8g5fXk_o='

# Mock Fernet to avoid real encryption/decryption in tests
class MockFernet:
    def __init__(self, key):
        pass

    def encrypt(self, data):
        return f"encrypted_{data.decode()}".encode()

    def decrypt(self, data):
        return data.decode().replace("encrypted_", "").encode()

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_env_vars():
    # Patch os.getenv to return the test key
    with patch('os.getenv', return_value=TEST_KEY.decode()) as p:
        yield p

@pytest.fixture
def mock_fernet():
    # Patch Fernet in all modules where it is used
    with patch('main.Fernet', MockFernet), \
         patch('file_utils.Fernet', MockFernet):
        yield

@pytest.fixture
def mock_file_operations():
    with patch('builtins.open', new_callable=mock_open) as mock_file:
        yield mock_file

@pytest.fixture
def mock_json_load():
    with patch('json.load') as mock_load:
        yield mock_load

@pytest.fixture
def mock_json_dumps():
    with patch('json.dumps') as mock_dumps:
        yield mock_dumps

@pytest.fixture
def mock_os_path_exists():
    with patch('os.path.exists', return_value=True) as mock_exists:
        yield mock_exists

# --- Tests for Profile Management ---
def test_load_profile_success(mock_env_vars, mock_fernet, mock_file_operations, mock_os_path_exists):
    mock_file_operations.return_value.read.return_value = b'encrypted_{"skills": ["Python"], "location": "Remote"}'
    profile = load_profile()
    assert profile == {"skills": ["Python"], "location": "Remote"}
    mock_file_operations.assert_called_with(PROFILE_FILE, 'rb')

def test_load_profile_file_not_found(mock_env_vars, mock_fernet, mock_file_operations):
    mock_file_operations.side_effect = FileNotFoundError
    profile = load_profile()
    assert profile == {}

def test_save_profile_success(mock_env_vars, mock_fernet, mock_file_operations, mock_json_dumps, mock_os_path_exists):
    with patch('main.update_profile_hash') as mock_update_hash:
        profile_data = {"skills": ["Java"], "location": "New York"}
        result = save_profile(profile_data)
        assert result is True
        mock_file_operations.assert_called_with(PROFILE_FILE, 'wb')
        mock_json_dumps.assert_called_once_with(profile_data, indent=4)
        mock_update_hash.assert_called_once()

# --- Tests for Export Docs ---
@patch('main.load_profile')
@patch('main.load_json_file')
def test_export_docs_no_placeholders_in_header(mock_load_json, mock_load_profile, mock_env_vars, mock_file_operations, mock_docx_document, mock_os_path_exists):
    mock_load_profile.return_value = {}
    mock_load_json.return_value = [{"job_details": {"title": "Dev", "company": {"display_name": "ABC"}}, "generated_materials": {"cover_letter": "CL", "refined_resume": "RES", "question_answers": []}}]
    
    runner = CliRunner()
    with patch('os.makedirs'), patch('main.add_styled_header') as mock_add_styled_header:
        result = runner.invoke(export_docs)
        assert result.exit_code == 0

        assert mock_add_styled_header.called
        # The second argument to add_styled_header is the text
        header_text_arg = mock_add_styled_header.call_args[0][1]
        assert "Applicant Name" not in header_text_arg
        assert "N/A" not in header_text_arg

@patch('main.load_profile')
@patch('main.load_json_file')
def test_export_docs_with_profile_data(mock_load_json, mock_load_profile, mock_env_vars, mock_file_operations, mock_docx_document, mock_os_path_exists):
    mock_load_profile.return_value = {"name": "Test User", "contact_info": {"email": "test@example.com"}, "location": "Test City"}
    mock_load_json.return_value = [{"job_details": {"title": "Dev", "company": {"display_name": "ABC"}}, "generated_materials": {"cover_letter": "CL", "refined_resume": "RES", "question_answers": []}}]
    
    runner = CliRunner()
    with patch('os.makedirs'), patch('main.add_styled_header') as mock_add_styled_header:
        result = runner.invoke(export_docs)
        assert result.exit_code == 0

        assert mock_add_styled_header.called
        header_text_arg = mock_add_styled_header.call_args[0][1]
        assert "Test User" in header_text_arg
        assert "test@example.com" in header_text_arg
        assert "Test City" in header_text_arg

@patch('main.load_profile')
@patch('main.load_json_file')
def test_export_docs_empty_materials_content(mock_load_json, mock_load_profile, mock_env_vars, mock_file_operations, mock_docx_document, mock_os_path_exists):
    mock_load_profile.return_value = {}
    mock_load_json.return_value = [{"job_details": {"title": "Dev", "company": {"display_name": "ABC"}}, "generated_materials": {}}]

    runner = CliRunner()
    with patch('os.makedirs'), patch('main.add_formatted_content') as mock_add_formatted_content:
        result = runner.invoke(export_docs)
        assert result.exit_code == 0

        assert mock_add_formatted_content.call_count == 2
        # Check that the content passed is empty, not the default "Not generated."
        assert mock_add_formatted_content.call_args_list[0][0][1] == ''
        assert mock_add_formatted_content.call_args_list[1][0][1] == ''

# Dummy fixtures for tests that need them but they are not used
@pytest.fixture
def mock_generative_model():
    pass

@pytest.fixture
def mock_docx_document():
    with patch('docx.Document') as mock_doc:
        yield mock_doc
