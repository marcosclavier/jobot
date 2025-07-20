
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
import os
import sys

# Add project root to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from job_bot_project.backend.main import app, oauth2_scheme


@pytest.fixture
def client():
    return TestClient(app)


async def override_get_current_user():
    return {"_id": "test_user_123", "email": "test@example.com"}


app.dependency_overrides[oauth2_scheme] = override_get_current_user


@pytest.mark.asyncio
async def test_generate_documents_success(client):
    # Arrange
    job_id = "test_job_123"
    user_id = "test_user_123"

    with patch('job_bot_project.backend.main.profiles_collection') as mock_profiles,          patch('job_bot_project.backend.main.recommended_jobs_collection') as mock_recommended_jobs,          patch('job_bot_project.backend.main.generate_application_materials') as mock_generate_materials:

        mock_profiles.find_one = AsyncMock(return_value={"user_id": user_id, "name": "Test User"})
        mock_recommended_jobs.find_one = AsyncMock(return_value={"user_id": user_id, "job_id": job_id, "job_details": {"title": "Software Engineer"}})
        mock_generate_materials.return_value = {
            "cover_letter": "This is a test cover letter.",
            "resume_suggestions": ["Suggestion 1", "Suggestion 2"],
            "question_answers": []
        }

        # Act
        response = client.post(f"/api/jobs/{job_id}/generate-documents", headers={"Authorization": "Bearer dummy-token"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["cover_letter"] == "This is a test cover letter."
        assert data["resume_suggestions"] == ["Suggestion 1", "Suggestion 2"]
