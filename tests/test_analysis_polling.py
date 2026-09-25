"""Integration tests for repository connect and real-time analysis status polling."""

from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.github_service import (
    GitHubFile,
    GitHubCommit,
    GitHubPR,
    GitHubRepoData,
)

client = TestClient(app)


def test_connect_repository_missing_fullname():
    res = client.post("/api/repositories/connect", json={})
    assert res.status_code == 422


def test_connect_repository_invalid_format():
    res = client.post("/api/repositories/connect", json={"fullName": "not-a-valid-repo"})
    assert res.status_code == 422


def test_get_analysis_status_non_existent():
    res = client.get("/api/repositories/non-existent-repo-xyz/analyze/status")
    assert res.status_code == 404


def test_get_analysis_status_existing_completed():
    res = client.get("/api/repositories/repo-orbit-payments/analyze/status")
    assert res.status_code == 200
    data = res.json()
    assert data["repositoryId"] == "repo-orbit-payments"
    assert data["status"] == "completed"
    assert data["progress"] == 100
    assert "steps" in data


def test_connect_and_poll_workflow_mocked():
    mock_repo_data = GitHubRepoData(
        owner="test-owner",
        name="test-repo",
        full_name="test-owner/test-repo",
        description="A test repository for unit tests",
        default_branch="main",
        private=False,
        stars=42,
        language="Python",
        languages={"Python": 1200},
        topics=["testing"],
        file_count=2,
        files=[
            GitHubFile(
                path="app/main.py",
                name="main.py",
                size=120,
                download_url="https://example.com/raw/main.py",
                language="Python",
                content="def hello():\n    return 'world'\n",
            ),
            GitHubFile(
                path="app/util.py",
                name="util.py",
                size=80,
                download_url="https://example.com/raw/util.py",
                language="Python",
                content="import os\n\ndef run():\n    pass\n",
            ),
        ],
        commits=[
            GitHubCommit(
                sha="abc1234",
                message="Initial commit",
                author="Test User",
                date="2026-09-01T00:00:00Z",
                files=["app/main.py"],
            )
        ],
        pull_requests=[
            GitHubPR(
                number=1,
                title="Add util function",
                author="Contributor",
                branch="feature-util",
                base_branch="main",
                state="open",
                created_at="2026-09-02T00:00:00Z",
                changed_files=1,
            )
        ],
    )

    with patch(
        "backend.app.services.repo_service.get_github_service"
    ) as mock_get_gh:
        mock_gh = MagicMock()
        mock_gh.parse_repo_identifier.return_value = ("test-owner", "test-repo")
        mock_gh.fetch_repository.return_value = mock_repo_data
        mock_get_gh.return_value = mock_gh

        # 1. Connect
        res = client.post("/api/repositories/connect", json={"fullName": "test-owner/test-repo"})
        assert res.status_code == 201
        repo = res.json()
        assert repo["fullName"] == "test-owner/test-repo"
        repo_id = repo["id"]

        # 2. Poll status
        status_res = client.get(f"/api/repositories/{repo_id}/analyze/status")
        assert status_res.status_code == 200
        job = status_res.json()
        assert job["repositoryId"] == repo_id
        assert "steps" in job
