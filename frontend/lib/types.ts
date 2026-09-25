export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type AnalysisStatus =
  | "not_started"
  | "queued"
  | "cloning"
  | "parsing"
  | "building_graph"
  | "analyzing_history"
  | "running_models"
  | "completed"
  | "failed";

export interface Repository {
  id: string;
  owner: string;
  name: string;
  fullName: string;
  defaultBranch: string;
  private: boolean;
  languages: string[];
  description: string;
  stars: number;
  connectedAt: string;
  lastAnalyzedAt: string | null;
  analysisStatus: AnalysisStatus;
  fileCount: number;
  locCount: number;
}

export interface HealthTrendPoint {
  date: string;
  score: number;
}

export interface RiskDistributionEntry {
  level: RiskLevel;
  count: number;
}

export interface RepositoryHealth {
  repositoryId: string;
  score: number;
  previousScore: number;
  trend: HealthTrendPoint[];
  breakdown: {
    defectRisk: number;
    securityRisk: number;
    regressionRisk: number;
    codeQuality: number;
    historicalStability: number;
  };
  riskDistribution: RiskDistributionEntry[];
  highRiskComponentCount: number;
  mediumRiskComponentCount: number;
  securityRiskCount: number;
  regressionRiskAreaCount: number;
  weights: {
    defectRisk: number;
    securityRisk: number;
    regressionRisk: number;
    codeQuality: number;
    historicalStability: number;
  };
}

export interface EvidenceFactor {
  label: string;
  detail: string;
  weight: number;
}

export interface SimilarPattern {
  id: string;
  title: string;
  type: "bug" | "vulnerability" | "change";
  similarity: number;
  repo: string;
  date: string;
  summary: string;
}

export interface CodeQualityMetrics {
  loc: number;
  cyclomaticComplexity: number;
  functionLength: number;
  coupling: number;
  centrality: number;
  changeFrequency: number;
  duplication: number;
  historicalDefectFrequency: number;
}

export interface ComponentRisk {
  id: string;
  repositoryId: string;
  path: string;
  name: string;
  type: "file" | "function" | "class";
  language: string;
  defectRisk: number;
  securityRisk: number;
  regressionRisk: number;
  riskLevel: RiskLevel;
  metrics: CodeQualityMetrics;
  lastModified: string;
  lastModifiedBy: string;
  evidence: EvidenceFactor[];
  similarHistorical: SimilarPattern[];
  downstreamDependents: string[];
}

export interface SecurityFinding {
  id: string;
  repositoryId: string;
  componentId: string;
  severity: RiskLevel;
  category: string;
  file: string;
  line: number;
  confidence: number;
  description: string;
  evidence: string;
  source: "semgrep" | "bandit" | "ml-risk-model" | "custom-rule";
}

export type GraphNodeType =
  | "repository"
  | "file"
  | "function"
  | "class"
  | "dependency"
  | "commit"
  | "pull_request";

export type GraphEdgeType =
  | "IMPORTS"
  | "CALLS"
  | "DEFINES"
  | "INHERITS"
  | "DEPENDS_ON"
  | "MODIFIED_BY"
  | "CO_CHANGED_WITH";

export interface RepoGraphNode {
  id: string;
  label: string;
  type: GraphNodeType;
  riskLevel?: RiskLevel;
  path?: string;
}

export interface RepoGraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
}

export interface RepositoryGraph {
  nodes: RepoGraphNode[];
  edges: RepoGraphEdge[];
}

export interface ChangedFile {
  path: string;
  additions: number;
  deletions: number;
  riskLevel: RiskLevel;
}

export interface AffectedComponent {
  path: string;
  reason: string;
  riskLevel: RiskLevel;
  hops: number;
}

export interface RecommendedTest {
  name: string;
  reason: string;
  priority: RiskLevel;
  suite: string;
}

export interface PullRequestReview {
  id: string;
  repositoryId: string;
  number: number;
  title: string;
  author: string;
  authorAvatar: string;
  branch: string;
  baseBranch: string;
  status: "open" | "merged" | "closed";
  createdAt: string;
  reviewStatus: "pending" | "in_progress" | "completed";
  bugRisk: RiskLevel;
  securityRisk: RiskLevel;
  regressionRisk: RiskLevel;
  aiSummary: string;
  changedFiles: ChangedFile[];
  potentiallyAffected: AffectedComponent[];
  recommendedTests: RecommendedTest[];
}

export interface AnalysisStep {
  key: string;
  label: string;
  status: "pending" | "active" | "done" | "failed";
  detail?: string;
}

export interface AnalysisJob {
  repositoryId: string;
  status: AnalysisStatus;
  progress: number;
  steps: AnalysisStep[];
  startedAt: string;
  errorMessage?: string;
}

export interface CommitEntry {
  sha: string;
  message: string;
  author: string;
  date: string;
  isBugFix: boolean;
}
