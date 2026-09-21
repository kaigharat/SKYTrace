"""Pydantic schemas mirroring the frontend domain types and PRD contract."""

from __future__ import annotations

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

AnalysisStatus = Literal[
    "not_started",
    "queued",
    "cloning",
    "parsing",
    "building_graph",
    "analyzing_history",
    "running_models",
    "completed",
    "failed",
]

GraphNodeType = Literal[
    "repository",
    "file",
    "function",
    "class",
    "dependency",
    "commit",
    "pull_request",
]

GraphEdgeType = Literal[
    "IMPORTS",
    "CALLS",
    "DEFINES",
    "INHERITS",
    "DEPENDS_ON",
    "MODIFIED_BY",
    "CO_CHANGED_WITH",
]


class Repository(BaseModel):
    id: str
    owner: str
    name: str
    fullName: str
    defaultBranch: str = "main"
    private: bool = False
    languages: List[str] = Field(default_factory=list)
    description: str = ""
    stars: int = 0
    connectedAt: str
    lastAnalyzedAt: Optional[str] = None
    analysisStatus: AnalysisStatus = "completed"
    fileCount: int = 0
    locCount: int = 0


class HealthTrendPoint(BaseModel):
    date: str
    score: int


class RiskDistributionEntry(BaseModel):
    level: RiskLevel
    count: int


class HealthBreakdown(BaseModel):
    defectRisk: int
    securityRisk: int
    regressionRisk: int
    codeQuality: int
    historicalStability: int


class HealthWeights(BaseModel):
    defectRisk: float = 0.3
    securityRisk: float = 0.3
    regressionRisk: float = 0.2
    codeQuality: float = 0.1
    historicalStability: float = 0.1


class RepositoryHealth(BaseModel):
    repositoryId: str
    score: int
    previousScore: int
    trend: List[HealthTrendPoint] = Field(default_factory=list)
    breakdown: HealthBreakdown
    riskDistribution: List[RiskDistributionEntry] = Field(default_factory=list)
    highRiskComponentCount: int = 0
    mediumRiskComponentCount: int = 0
    securityRiskCount: int = 0
    regressionRiskAreaCount: int = 0
    weights: HealthWeights = Field(default_factory=HealthWeights)


class EvidenceFactor(BaseModel):
    label: str
    detail: str
    weight: float


class SimilarPattern(BaseModel):
    id: str
    title: str
    type: Literal["bug", "vulnerability", "change"]
    similarity: float
    repo: str
    date: str
    summary: str


class CodeQualityMetrics(BaseModel):
    loc: int
    cyclomaticComplexity: int
    functionLength: int
    coupling: int
    centrality: float
    changeFrequency: int
    duplication: int
    historicalDefectFrequency: float


class ComponentRisk(BaseModel):
    id: str
    repositoryId: str
    path: str
    name: str
    type: Literal["file", "function", "class"] = "file"
    language: str = "Python"
    defectRisk: int
    securityRisk: int
    regressionRisk: int
    riskLevel: RiskLevel
    metrics: CodeQualityMetrics
    lastModified: str
    lastModifiedBy: str
    evidence: List[EvidenceFactor] = Field(default_factory=list)
    similarHistorical: List[SimilarPattern] = Field(default_factory=list)
    downstreamDependents: List[str] = Field(default_factory=list)


class SecurityFinding(BaseModel):
    id: str
    repositoryId: str
    componentId: str
    severity: RiskLevel
    category: str
    file: str
    line: int
    confidence: float
    description: str
    evidence: str
    source: Literal["semgrep", "bandit", "ml-risk-model", "custom-rule"] = "ml-risk-model"


class RepoGraphNode(BaseModel):
    id: str
    label: str
    type: GraphNodeType
    riskLevel: Optional[RiskLevel] = None
    path: Optional[str] = None


class RepoGraphEdge(BaseModel):
    id: str
    source: str
    target: str
    type: GraphEdgeType


class RepositoryGraph(BaseModel):
    nodes: List[RepoGraphNode] = Field(default_factory=list)
    edges: List[RepoGraphEdge] = Field(default_factory=list)


class ChangedFile(BaseModel):
    path: str
    additions: int
    deletions: int
    riskLevel: RiskLevel


class AffectedComponent(BaseModel):
    path: str
    reason: str
    riskLevel: RiskLevel
    hops: int


class RecommendedTest(BaseModel):
    name: str
    reason: str
    priority: RiskLevel
    suite: str


class PullRequestReview(BaseModel):
    id: str
    repositoryId: str
    number: int
    title: str
    author: str
    authorAvatar: str
    branch: str
    baseBranch: str
    status: Literal["open", "merged", "closed"] = "open"
    createdAt: str
    reviewStatus: Literal["pending", "in_progress", "completed"] = "completed"
    bugRisk: RiskLevel
    securityRisk: RiskLevel
    regressionRisk: RiskLevel
    aiSummary: str
    changedFiles: List[ChangedFile] = Field(default_factory=list)
    potentiallyAffected: List[AffectedComponent] = Field(default_factory=list)
    recommendedTests: List[RecommendedTest] = Field(default_factory=list)


class AnalysisStep(BaseModel):
    key: str
    label: str
    status: Literal["pending", "active", "done", "failed"] = "pending"
    detail: Optional[str] = None


class AnalysisJob(BaseModel):
    repositoryId: str
    status: AnalysisStatus
    progress: int
    steps: List[AnalysisStep] = Field(default_factory=list)
    startedAt: str


class CommitEntry(BaseModel):
    sha: str
    message: str
    author: str
    date: str
    isBugFix: bool = False


# Prediction API Schemas
class PredictCodeRequest(BaseModel):
    code: str = Field(..., description="Source code string to analyze")
    path: str = Field(default="source.py", description="File or component path")
    language: str = Field(default="Python", description="Programming language")
    repositoryId: str = Field(default="repo-orbit-payments", description="Repository identifier")
    componentId: Optional[str] = Field(default=None, description="Optional existing component id")


class PredictCodeResponse(BaseModel):
    component: ComponentRisk
    inferenceSource: str = "SkyTrace RandomForest ML Baseline + Static Features"
    status: str = "success"
