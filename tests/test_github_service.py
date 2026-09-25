"""Tests for GitHubService parsing, URL handling, and tree filtering."""

import pytest
from backend.app.services.github_service import (
    GitHubService,
    SUPPORTED_EXTENSIONS,
    _ext_to_language,
)


def test_parse_repo_identifier_owner_repo():
    svc = GitHubService()
    owner, repo = svc.parse_repo_identifier("pallets/flask")
    assert owner == "pallets"
    assert repo == "flask"


def test_parse_repo_identifier_full_https_url():
    svc = GitHubService()
    owner, repo = svc.parse_repo_identifier("https://github.com/fastapi/fastapi")
    assert owner == "fastapi"
    assert repo == "fastapi"


def test_parse_repo_identifier_url_with_git_and_trailing_slash():
    svc = GitHubService()
    owner, repo = svc.parse_repo_identifier("https://github.com/torvalds/linux.git/")
    assert owner == "torvalds"
    assert repo == "linux"


def test_parse_repo_identifier_invalid():
    svc = GitHubService()
    with pytest.raises(ValueError):
        svc.parse_repo_identifier("invalid_single_string")


def test_ext_to_language():
    assert _ext_to_language(".py") == "Python"
    assert _ext_to_language(".ts") == "TypeScript"
    assert _ext_to_language(".tsx") == "TypeScript"
    assert _ext_to_language(".go") == "Go"
    assert _ext_to_language(".java") == "Java"
    assert _ext_to_language(".unknown") == "Unknown"


def test_supported_extensions_contain_primary_languages():
    for ext in [".py", ".ts", ".tsx", ".js", ".java", ".go", ".c", ".cpp", ".rs"]:
        assert ext in SUPPORTED_EXTENSIONS
