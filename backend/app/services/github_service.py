"""GitHub API integration service for SkyTrace.

Fetches real repository metadata, file contents, commits, and pull requests
from the GitHub API. No git client required — uses the REST API directly.
"""

from __future__ import annotations

import base64
import re
import urllib.request
import urllib.error
import json
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# Supported source code file extensions
SUPPORTED_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".java", ".go",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".cs", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".r", ".m", ".sh", ".bash",
}

# Max file size to fetch content for (100 KB)
MAX_FILE_BYTES = 100_000

# Max files to analyze per repo (to keep analysis time reasonable)
MAX_FILES = 150


@dataclass
class GitHubFile:
    path: str
    name: str
    size: int
    download_url: str
    language: str = "Unknown"
    content: str = ""


@dataclass
class GitHubCommit:
    sha: str
    message: str
    author: str
    date: str
    files: List[str] = field(default_factory=list)


@dataclass
class GitHubPR:
    number: int
    title: str
    author: str
    branch: str
    base_branch: str
    state: str
    created_at: str
    body: str = ""
    changed_files: int = 0


@dataclass
class GitHubRepoData:
    owner: str
    name: str
    full_name: str
    description: str
    default_branch: str
    private: bool
    stars: int
    language: str
    languages: Dict[str, int]
    topics: List[str]
    file_count: int
    files: List[GitHubFile]
    commits: List[GitHubCommit]
    pull_requests: List[GitHubPR]


def _ext_to_language(ext: str) -> str:
    return {
        ".py": "Python", ".ts": "TypeScript", ".tsx": "TypeScript",
        ".js": "JavaScript", ".jsx": "JavaScript",
        ".java": "Java", ".go": "Go",
        ".c": "C", ".cpp": "C++", ".cc": "C++", ".cxx": "C++",
        ".h": "C", ".hpp": "C++",
        ".cs": "C#", ".rs": "Rust", ".rb": "Ruby",
        ".php": "PHP", ".swift": "Swift", ".kt": "Kotlin",
        ".scala": "Scala", ".r": "R", ".m": "Objective-C",
        ".sh": "Shell", ".bash": "Shell",
    }.get(ext.lower(), "Unknown")


class GitHubService:
    """Fetches real repository data from the GitHub REST API."""

    BASE = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        self.token = token
        self._rate_limited_until: float = 0

    def _headers(self) -> Dict[str, str]:
        h: Dict[str, str] = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "SkyTrace-Intelligence/1.0",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _get(self, url: str, retries: int = 3) -> Any:
        """HTTP GET with basic retry + rate-limit handling."""
        now = time.time()
        if now < self._rate_limited_until:
            wait = self._rate_limited_until - now
            time.sleep(min(wait, 10))

        for attempt in range(retries):
            try:
                req = urllib.request.Request(url, headers=self._headers())
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                if e.code == 403:
                    # Rate limited
                    reset_str = e.headers.get("X-RateLimit-Reset", "0")
                    reset = int(reset_str) if reset_str else int(time.time()) + 60
                    self._rate_limited_until = float(reset)
                    wait = max(5, reset - int(time.time()))
                    time.sleep(min(wait, 30))
                    continue
                elif e.code == 404:
                    raise ValueError(f"Repository not found: {url}")
                elif e.code == 401:
                    raise ValueError("GitHub token is invalid or expired.")
                raise
            except Exception:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise
        raise RuntimeError(f"Failed to fetch {url} after {retries} retries")

    def _get_raw(self, url: str) -> str:
        """Fetch raw file content."""
        req = urllib.request.Request(url, headers={
            "User-Agent": "SkyTrace-Intelligence/1.0",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read()
                return raw.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def parse_repo_identifier(self, identifier: str) -> Tuple[str, str]:
        """Parse 'owner/repo' or full GitHub URL into (owner, repo)."""
        identifier = identifier.strip().rstrip("/")
        # Handle full URLs
        patterns = [
            r"github\.com[:/]([^/]+)/([^/\s\.]+?)(?:\.git)?$",
            r"^([^/\s]+)/([^/\s]+)$",
        ]
        for pat in patterns:
            m = re.search(pat, identifier)
            if m:
                return m.group(1), m.group(2)
        raise ValueError(
            f"Cannot parse '{identifier}'. Use 'owner/repo' or a GitHub URL."
        )

    def _walk_tree(
        self,
        owner: str,
        repo: str,
        branch: str,
        progress_cb=None,
    ) -> List[GitHubFile]:
        """Walk repo tree via the Git Trees API (single API call)."""
        url = f"{self.BASE}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
        try:
            data = self._get(url)
        except Exception:
            return []

        files: List[GitHubFile] = []
        tree = data.get("tree", [])

        for item in tree:
            if item.get("type") != "blob":
                continue
            path: str = item.get("path", "")
            size: int = item.get("size", 0)
            ext = "." + path.rsplit(".", 1)[-1] if "." in path else ""

            if ext.lower() not in SUPPORTED_EXTENSIONS:
                continue
            if size > MAX_FILE_BYTES:
                continue

            lang = _ext_to_language(ext)
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
            files.append(GitHubFile(
                path=path,
                name=path.split("/")[-1],
                size=size,
                download_url=raw_url,
                language=lang,
            ))

        # Sort by path for determinism, cap at MAX_FILES
        files.sort(key=lambda f: f.path)
        return files[:MAX_FILES]

    def _fetch_file_contents(
        self,
        files: List[GitHubFile],
        progress_cb=None,
    ) -> None:
        """Fetch source code for each file in-place."""
        for i, f in enumerate(files):
            f.content = self._get_raw(f.download_url)
            if progress_cb:
                progress_cb(i + 1, len(files))

    def _fetch_commits(self, owner: str, repo: str) -> List[GitHubCommit]:
        """Fetch recent commits."""
        url = f"{self.BASE}/repos/{owner}/{repo}/commits?per_page=30"
        try:
            items = self._get(url)
        except Exception:
            return []

        commits = []
        for item in items:
            c = item.get("commit", {})
            author = (
                c.get("author", {}).get("name")
                or item.get("author", {}).get("login", "unknown")
            )
            commits.append(GitHubCommit(
                sha=item.get("sha", "")[:7],
                message=c.get("message", "").split("\n")[0][:120],
                author=author,
                date=c.get("author", {}).get("date", ""),
            ))
        return commits

    def _fetch_pull_requests(self, owner: str, repo: str) -> List[GitHubPR]:
        """Fetch open pull requests."""
        url = f"{self.BASE}/repos/{owner}/{repo}/pulls?state=open&per_page=10"
        try:
            items = self._get(url)
        except Exception:
            return []

        prs = []
        for item in items:
            prs.append(GitHubPR(
                number=item.get("number", 0),
                title=item.get("title", "Untitled PR"),
                author=item.get("user", {}).get("login", "unknown"),
                branch=item.get("head", {}).get("ref", ""),
                base_branch=item.get("base", {}).get("ref", "main"),
                state=item.get("state", "open"),
                created_at=item.get("created_at", ""),
                body=item.get("body") or "",
                changed_files=item.get("changed_files", 0),
            ))
        return prs

    def fetch_pr_diff(self, owner: str, repo: str, pull_number: int) -> str:
        """Fetch unified diff for a pull request using GitHub diff media type."""
        url = f"{self.BASE}/repos/{owner}/{repo}/pulls/{pull_number}"
        req = urllib.request.Request(url, headers={
            "Accept": "application/vnd.github.v3.diff",
            "User-Agent": "SkyTrace-Intelligence/1.0",
            **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
        })
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception:
            return ""

    def fetch_repository(
        self,
        identifier: str,
        progress_cb=None,
    ) -> GitHubRepoData:
        """
        Fully fetch a GitHub repository.
        progress_cb(step: str, current: int, total: int) → called during file fetch.
        """
        owner, repo_name = self.parse_repo_identifier(identifier)

        if progress_cb:
            progress_cb("fetch_meta", 0, 1)

        # Repo metadata
        meta = self._get(f"{self.BASE}/repos/{owner}/{repo_name}")
        default_branch = meta.get("default_branch", "main")

        # Languages
        try:
            langs: Dict[str, int] = self._get(
                f"{self.BASE}/repos/{owner}/{repo_name}/languages"
            )
        except Exception:
            langs = {}

        lang_list = list(langs.keys()) or [meta.get("language", "Unknown")]

        # File tree
        if progress_cb:
            progress_cb("walk_tree", 0, 1)
        files = self._walk_tree(owner, repo_name, default_branch, progress_cb)

        # File contents
        if progress_cb:
            progress_cb("fetch_files", 0, len(files))
        self._fetch_file_contents(
            files,
            progress_cb=lambda i, n: progress_cb("fetch_files", i, n) if progress_cb else None,
        )

        # Commits
        if progress_cb:
            progress_cb("fetch_commits", 0, 1)
        commits = self._fetch_commits(owner, repo_name)

        # PRs
        if progress_cb:
            progress_cb("fetch_prs", 0, 1)
        prs = self._fetch_pull_requests(owner, repo_name)

        return GitHubRepoData(
            owner=owner,
            name=repo_name,
            full_name=f"{owner}/{repo_name}",
            description=meta.get("description") or "",
            default_branch=default_branch,
            private=meta.get("private", False),
            stars=meta.get("stargazers_count", 0),
            language=meta.get("language") or (lang_list[0] if lang_list else "Unknown"),
            languages=langs,
            topics=meta.get("topics") or [],
            file_count=len(files),
            files=files,
            commits=commits,
            pull_requests=prs,
        )


# Singleton
_github_service: Optional[GitHubService] = None


def get_github_service() -> GitHubService:
    global _github_service
    if _github_service is None:
        from backend.app.core.config import settings
        _github_service = GitHubService(token=settings.GITHUB_TOKEN)
    return _github_service
