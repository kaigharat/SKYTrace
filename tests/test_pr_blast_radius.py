"""Tests for PR blast-radius calculation, unified diff parsing, and repository persistence."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.schemas.domain import (
    ComponentRisk,
    CodeQualityMetrics,
    RepoGraphNode,
    RepoGraphEdge,
    RepositoryGraph,
)
from backend.app.services.repo_service import (
    _parse_diff_files,
    _make_pr_review,
    RepositoryService,
)
from backend.app.services.github_service import GitHubPR


def test_parse_diff_files_additions_deletions():
    sample_diff = """diff --git a/app/auth.py b/app/auth.py
index abc..def 100644
--- a/app/auth.py
+++ b/app/auth.py
@@ -1,4 +1,6 @@
+import jwt
 def login():
-    return False
+    return True
+    # added line
diff --git a/app/main.py b/app/main.py
--- a/app/main.py
+++ b/app/main.py
@@ -10,2 +10,1 @@
-old_func()
+new_func()
"""
    parsed = _parse_diff_files(sample_diff)
    assert len(parsed) == 2
    assert parsed[0][0] == "app/auth.py"
    assert parsed[0][1] == 3  # additions
    assert parsed[0][2] == 1  # deletions
    assert parsed[1][0] == "app/main.py"
    assert parsed[1][1] == 1
    assert parsed[1][2] == 1


def test_pr_blast_radius_graph_traversal():
    gh_pr = GitHubPR(
        number=42,
        title="Fix authentication flow",
        author="alice",
        branch="fix/auth",
        base_branch="main",
        state="open",
        created_at="2026-09-20T00:00:00Z",
    )

    sample_diff = """diff --git a/app/auth.py b/app/auth.py
--- a/app/auth.py
+++ b/app/auth.py
@@ -1 +1 @@
+import security
"""

    graph = RepositoryGraph(
        nodes=[
            RepoGraphNode(id="node-auth", label="app/auth.py", type="file"),
            RepoGraphNode(id="node-api", label="app/api.py", type="file"),
            RepoGraphNode(id="node-server", label="app/server.py", type="file"),
        ],
        edges=[
            RepoGraphEdge(id="e1", source="node-auth", target="node-api", type="IMPORTS"),
            RepoGraphEdge(id="e2", source="node-api", target="node-server", type="IMPORTS"),
        ],
    )

    metrics = CodeQualityMetrics(
        loc=50,
        cyclomaticComplexity=3,
        functionLength=15,
        coupling=2,
        centrality=0.4,
        changeFrequency=5,
        duplication=0,
        historicalDefectFrequency=0.1,
    )

    auth_comp = ComponentRisk(
        id="comp-auth",
        repositoryId="repo-test",
        path="app/auth.py",
        name="auth.py",
        defectRisk=40,
        securityRisk=75,
        regressionRisk=30,
        riskLevel="HIGH",
        metrics=metrics,
        lastModified="2026-09-20T00:00:00Z",
        lastModifiedBy="alice",
    )

    comp_map = {"app/auth.py": auth_comp}

    review = _make_pr_review(
        repo_id="repo-test",
        gh_pr=gh_pr,
        high_risk_comps=[auth_comp],
        raw_diff=sample_diff,
        graph=graph,
        comp_map=comp_map,
    )

    assert review.number == 42
    assert len(review.changedFiles) == 1
    assert review.changedFiles[0].path == "app/auth.py"
    # Should identify app/api.py (1-hop) and app/server.py (2-hop) as affected
    affected_paths = [a.path for a in review.potentiallyAffected]
    assert "app/api.py" in affected_paths
    assert "app/server.py" in affected_paths
    # Tests recommended
    assert len(review.recommendedTests) > 0


def test_repository_service_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_cache_file = Path(tmpdir) / "test_cache.json"

        with patch("backend.app.services.repo_service.CACHE_FILE", test_cache_file):
            svc1 = RepositoryService()
            # Add a completed repo
            from backend.app.schemas.domain import Repository
            new_repo = Repository(
                id="repo-custom-persist",
                owner="user",
                name="custom-persist",
                fullName="user/custom-persist",
                defaultBranch="main",
                private=False,
                languages=["Python"],
                description="Persistent repo",
                stars=5,
                connectedAt="2026-09-20T00:00:00Z",
                lastAnalyzedAt="2026-09-20T00:00:00Z",
                analysisStatus="completed",
                fileCount=10,
                locCount=500,
            )
            svc1.repositories[new_repo.id] = new_repo
            svc1._save_to_disk()

            assert test_cache_file.exists()

            # Second service instance should load it from disk
            svc2 = RepositoryService()
            assert "repo-custom-persist" in svc2.repositories
            loaded = svc2.get_repository("repo-custom-persist")
            assert loaded is not None
            assert loaded.fullName == "user/custom-persist"
