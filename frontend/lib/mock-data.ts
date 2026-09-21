import type {
  AnalysisJob,
  ComponentRisk,
  PullRequestReview,
  Repository,
  RepositoryGraph,
  RepositoryHealth,
  SecurityFinding,
} from "@/lib/types";

// Mock data shaped to match the backend Integration Contract (PRD §17, §18, §20)
// so this frontend can be re-pointed at the real FastAPI service by swapping
// the functions in lib/api.ts for real fetch calls without touching the UI.

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString();
}

export const repositories: Repository[] = [
  {
    id: "repo-orbit-payments",
    owner: "acme-labs",
    name: "orbit-payments",
    fullName: "acme-labs/orbit-payments",
    defaultBranch: "main",
    private: true,
    languages: ["Python", "TypeScript"],
    description: "Core payments, checkout and ledger service for Acme Labs.",
    stars: 128,
    connectedAt: daysAgo(41),
    lastAnalyzedAt: daysAgo(0),
    analysisStatus: "completed",
    fileCount: 486,
    locCount: 58230,
  },
  {
    id: "repo-growth-analytics",
    owner: "acme-labs",
    name: "growth-analytics-service",
    fullName: "acme-labs/growth-analytics-service",
    defaultBranch: "main",
    private: true,
    languages: ["Python"],
    description: "Event ingestion and growth analytics pipeline.",
    stars: 34,
    connectedAt: daysAgo(2),
    lastAnalyzedAt: null,
    analysisStatus: "running_models",
    fileCount: 212,
    locCount: 21870,
  },
  {
    id: "repo-storefront-web",
    owner: "acme-labs",
    name: "storefront-web",
    fullName: "acme-labs/storefront-web",
    defaultBranch: "main",
    private: false,
    languages: ["TypeScript", "JavaScript"],
    description: "Customer-facing storefront built on Next.js.",
    stars: 76,
    connectedAt: daysAgo(41),
    lastAnalyzedAt: daysAgo(6),
    analysisStatus: "completed",
    fileCount: 349,
    locCount: 40110,
  },
];

const trend14 = [61, 63, 62, 65, 66, 64, 67, 69, 70, 68, 71, 72, 70, 73].map(
  (score, i) => ({ date: daysAgo(13 - i), score }),
);

export const repositoryHealth: Record<string, RepositoryHealth> = {
  "repo-orbit-payments": {
    repositoryId: "repo-orbit-payments",
    score: 73,
    previousScore: 70,
    trend: trend14,
    breakdown: {
      defectRisk: 68,
      securityRisk: 74,
      regressionRisk: 71,
      codeQuality: 79,
      historicalStability: 76,
    },
    riskDistribution: [
      { level: "CRITICAL", count: 2 },
      { level: "HIGH", count: 7 },
      { level: "MEDIUM", count: 19 },
      { level: "LOW", count: 458 },
    ],
    highRiskComponentCount: 9,
    mediumRiskComponentCount: 19,
    securityRiskCount: 6,
    regressionRiskAreaCount: 5,
    weights: {
      defectRisk: 0.3,
      securityRisk: 0.3,
      regressionRisk: 0.2,
      codeQuality: 0.1,
      historicalStability: 0.1,
    },
  },
  "repo-storefront-web": {
    repositoryId: "repo-storefront-web",
    score: 84,
    previousScore: 81,
    trend: trend14.map((p) => ({ date: p.date, score: p.score + 12 })),
    breakdown: {
      defectRisk: 82,
      securityRisk: 88,
      regressionRisk: 80,
      codeQuality: 85,
      historicalStability: 83,
    },
    riskDistribution: [
      { level: "CRITICAL", count: 0 },
      { level: "HIGH", count: 3 },
      { level: "MEDIUM", count: 12 },
      { level: "LOW", count: 334 },
    ],
    highRiskComponentCount: 3,
    mediumRiskComponentCount: 12,
    securityRiskCount: 1,
    regressionRiskAreaCount: 2,
    weights: {
      defectRisk: 0.3,
      securityRisk: 0.3,
      regressionRisk: 0.2,
      codeQuality: 0.1,
      historicalStability: 0.1,
    },
  },
};

export const components: ComponentRisk[] = [
  {
    id: "comp-auth-service",
    repositoryId: "repo-orbit-payments",
    path: "auth/service.py",
    name: "service.py",
    type: "file",
    language: "Python",
    defectRisk: 91,
    securityRisk: 84,
    regressionRisk: 88,
    riskLevel: "CRITICAL",
    metrics: {
      loc: 612,
      cyclomaticComplexity: 34,
      functionLength: 48,
      coupling: 21,
      centrality: 0.92,
      changeFrequency: 27,
      duplication: 6,
      historicalDefectFrequency: 0.71,
    },
    lastModified: daysAgo(1),
    lastModifiedBy: "r.iyer",
    evidence: [
      {
        label: "High historical defect frequency",
        detail: "11 of the last 27 changes to this file were bug-fix commits.",
        weight: 0.32,
      },
      {
        label: "High dependency centrality",
        detail: "Imported by 18 modules; ranks in the top 2% of the call graph by betweenness centrality.",
        weight: 0.28,
      },
      {
        label: "High modification frequency",
        detail: "Changed 27 times in the last 90 days, 3.4x the repository median.",
        weight: 0.22,
      },
      {
        label: "Similar to historical defective patterns",
        detail: "Embedding matches 4 previously confirmed auth-bypass defects at 0.86+ similarity.",
        weight: 0.18,
      },
    ],
    similarHistorical: [
      {
        id: "sim-1",
        title: "Session token not invalidated on password reset",
        type: "bug",
        similarity: 0.91,
        repo: "acme-labs/orbit-payments",
        date: daysAgo(210),
        summary: "Fixed by revoking all refresh tokens on password_reset(), same call pattern as validate_session().",
      },
      {
        id: "sim-2",
        title: "JWT signature check skipped on legacy fallback path",
        type: "vulnerability",
        similarity: 0.88,
        repo: "acme-labs/legacy-auth",
        date: daysAgo(430),
        summary: "CVE-class finding in a structurally similar fallback branch guarding token verification.",
      },
      {
        id: "sim-3",
        title: "Refactor of authenticate() introduced race condition",
        type: "change",
        similarity: 0.79,
        repo: "acme-labs/orbit-payments",
        date: daysAgo(95),
        summary: "A prior refactor of this exact function reintroduced a TOCTOU bug under concurrent login.",
      },
    ],
    downstreamDependents: [
      "payment/service.py",
      "orders/checkout.py",
      "api/middleware/session.py",
      "billing/invoice.py",
    ],
  },
  {
    id: "comp-payment-service",
    repositoryId: "repo-orbit-payments",
    path: "payment/service.py",
    name: "service.py",
    type: "file",
    language: "Python",
    defectRisk: 78,
    securityRisk: 66,
    regressionRisk: 82,
    riskLevel: "HIGH",
    metrics: {
      loc: 540,
      cyclomaticComplexity: 29,
      functionLength: 41,
      coupling: 17,
      centrality: 0.81,
      changeFrequency: 19,
      duplication: 4,
      historicalDefectFrequency: 0.52,
    },
    lastModified: daysAgo(1),
    lastModifiedBy: "r.iyer",
    evidence: [
      { label: "High dependency centrality", detail: "Depended on by checkout, invoice and refund flows.", weight: 0.3 },
      { label: "Elevated modification frequency", detail: "19 changes in 90 days.", weight: 0.24 },
      { label: "Downstream of high-risk auth module", detail: "Directly calls auth/service.py:validate_session().", weight: 0.26 },
      { label: "Moderate historical defect frequency", detail: "6 of 19 recent changes were labeled bug-fix commits.", weight: 0.2 },
    ],
    similarHistorical: [
      {
        id: "sim-4",
        title: "Double-charge on retried payment intent",
        type: "bug",
        similarity: 0.84,
        repo: "acme-labs/orbit-payments",
        date: daysAgo(150),
        summary: "Idempotency key not enforced on retry path, same structure as current charge().",
      },
    ],
    downstreamDependents: ["orders/checkout.py", "billing/invoice.py"],
  },
  {
    id: "comp-orders-checkout",
    repositoryId: "repo-orbit-payments",
    path: "orders/checkout.py",
    name: "checkout.py",
    type: "file",
    language: "Python",
    defectRisk: 64,
    securityRisk: 41,
    regressionRisk: 73,
    riskLevel: "HIGH",
    metrics: {
      loc: 388,
      cyclomaticComplexity: 22,
      functionLength: 33,
      coupling: 12,
      centrality: 0.62,
      changeFrequency: 14,
      duplication: 3,
      historicalDefectFrequency: 0.31,
    },
    lastModified: daysAgo(1),
    lastModifiedBy: "s.chen",
    evidence: [
      { label: "Downstream of two high-risk modules", detail: "Calls both auth/service.py and payment/service.py.", weight: 0.35 },
      { label: "Frequently co-changed with payment/service.py", detail: "Modified together in 11 of the last 14 commits touching either file.", weight: 0.3 },
      { label: "Moderate cyclomatic complexity", detail: "22 branches across 4 public functions.", weight: 0.2 },
      { label: "Low direct defect history", detail: "Only 2 confirmed bug-fix commits historically.", weight: 0.15 },
    ],
    similarHistorical: [],
    downstreamDependents: ["billing/invoice.py"],
  },
  {
    id: "comp-orders-order",
    repositoryId: "repo-orbit-payments",
    path: "orders/order.py",
    name: "order.py",
    type: "file",
    language: "Python",
    defectRisk: 58,
    securityRisk: 22,
    regressionRisk: 61,
    riskLevel: "MEDIUM",
    metrics: {
      loc: 301,
      cyclomaticComplexity: 17,
      functionLength: 26,
      coupling: 9,
      centrality: 0.48,
      changeFrequency: 11,
      duplication: 2,
      historicalDefectFrequency: 0.22,
    },
    lastModified: daysAgo(1),
    lastModifiedBy: "s.chen",
    evidence: [
      { label: "Co-changed with checkout.py", detail: "Shared change history with orders/checkout.py in 8 recent commits.", weight: 0.4 },
      { label: "Moderate centrality", detail: "Depended on by invoice and fulfillment modules.", weight: 0.35 },
      { label: "Stable historical defect rate", detail: "1 bug-fix commit in the last 90 days.", weight: 0.25 },
    ],
    similarHistorical: [],
    downstreamDependents: ["billing/invoice.py", "fulfillment/dispatch.py"],
  },
  {
    id: "comp-billing-invoice",
    repositoryId: "repo-orbit-payments",
    path: "billing/invoice.py",
    name: "invoice.py",
    type: "file",
    language: "Python",
    defectRisk: 46,
    securityRisk: 29,
    regressionRisk: 66,
    riskLevel: "MEDIUM",
    metrics: {
      loc: 274,
      cyclomaticComplexity: 15,
      functionLength: 24,
      coupling: 8,
      centrality: 0.44,
      changeFrequency: 6,
      duplication: 1,
      historicalDefectFrequency: 0.14,
    },
    lastModified: daysAgo(4),
    lastModifiedBy: "r.iyer",
    evidence: [
      { label: "Three-hop downstream of auth/service.py", detail: "Reachable via payment/service.py and orders/checkout.py in the call graph.", weight: 0.5 },
      { label: "Low direct defect history", detail: "No confirmed bug-fix commits in the last 6 months.", weight: 0.3 },
      { label: "Low complexity", detail: "15 cyclomatic complexity, well under repository median.", weight: 0.2 },
    ],
    similarHistorical: [],
    downstreamDependents: [],
  },
  {
    id: "comp-api-session",
    repositoryId: "repo-orbit-payments",
    path: "api/middleware/session.py",
    name: "session.py",
    type: "file",
    language: "Python",
    defectRisk: 55,
    securityRisk: 61,
    regressionRisk: 69,
    riskLevel: "MEDIUM",
    metrics: {
      loc: 198,
      cyclomaticComplexity: 12,
      functionLength: 19,
      coupling: 14,
      centrality: 0.7,
      changeFrequency: 9,
      duplication: 1,
      historicalDefectFrequency: 0.28,
    },
    lastModified: daysAgo(2),
    lastModifiedBy: "r.iyer",
    evidence: [
      { label: "Direct dependent of auth/service.py", detail: "Imports validate_session() and refresh_token().", weight: 0.45 },
      { label: "Security-sensitive surface", detail: "Handles session cookies on every authenticated request.", weight: 0.35 },
      { label: "Moderate change frequency", detail: "9 changes in 90 days.", weight: 0.2 },
    ],
    similarHistorical: [],
    downstreamDependents: ["orders/checkout.py"],
  },
  {
    id: "comp-webhooks-stripe",
    repositoryId: "repo-orbit-payments",
    path: "integrations/stripe_webhook.py",
    name: "stripe_webhook.py",
    type: "file",
    language: "Python",
    defectRisk: 39,
    securityRisk: 72,
    regressionRisk: 34,
    riskLevel: "HIGH",
    metrics: {
      loc: 165,
      cyclomaticComplexity: 11,
      functionLength: 22,
      coupling: 6,
      centrality: 0.31,
      changeFrequency: 5,
      duplication: 0,
      historicalDefectFrequency: 0.1,
    },
    lastModified: daysAgo(9),
    lastModifiedBy: "s.chen",
    evidence: [
      { label: "Static-analysis finding: missing signature verification branch", detail: "Semgrep rule webhook-signature-check flagged an unguarded code path.", weight: 0.55 },
      { label: "External trust boundary", detail: "Directly processes unauthenticated inbound webhook payloads.", weight: 0.3 },
      { label: "Low change frequency", detail: "Only 5 changes in 90 days, reducing confidence in recent hardening.", weight: 0.15 },
    ],
    similarHistorical: [
      {
        id: "sim-5",
        title: "Webhook replay accepted due to missing timestamp check",
        type: "vulnerability",
        similarity: 0.82,
        repo: "acme-labs/legacy-auth",
        date: daysAgo(300),
        summary: "Same integration pattern; fixed by enforcing a 5-minute timestamp tolerance window.",
      },
    ],
    downstreamDependents: ["payment/service.py"],
  },
  {
    id: "comp-cart-utils",
    repositoryId: "repo-orbit-payments",
    path: "orders/cart_utils.ts",
    name: "cart_utils.ts",
    type: "file",
    language: "TypeScript",
    defectRisk: 24,
    securityRisk: 12,
    regressionRisk: 28,
    riskLevel: "LOW",
    metrics: {
      loc: 140,
      cyclomaticComplexity: 8,
      functionLength: 14,
      coupling: 4,
      centrality: 0.18,
      changeFrequency: 4,
      duplication: 0,
      historicalDefectFrequency: 0.05,
    },
    lastModified: daysAgo(12),
    lastModifiedBy: "s.chen",
    evidence: [
      { label: "Low centrality", detail: "Only used by the cart summary widget.", weight: 0.6 },
      { label: "No historical defects", detail: "No bug-fix commits recorded for this file.", weight: 0.4 },
    ],
    similarHistorical: [],
    downstreamDependents: [],
  },
];

export const securityFindings: SecurityFinding[] = [
  {
    id: "sec-1",
    repositoryId: "repo-orbit-payments",
    componentId: "comp-webhooks-stripe",
    severity: "HIGH",
    category: "Broken Authentication",
    file: "integrations/stripe_webhook.py",
    line: 47,
    confidence: 0.88,
    description: "Webhook handler accepts requests without verifying the Stripe-Signature header on the retry path.",
    evidence: "Semgrep rule `python.stripe.webhook-signature-check` matched at line 47; ML risk model corroborates with 0.79 probability.",
    source: "semgrep",
  },
  {
    id: "sec-2",
    repositoryId: "repo-orbit-payments",
    componentId: "comp-auth-service",
    severity: "CRITICAL",
    category: "Session Management",
    file: "auth/service.py",
    line: 212,
    confidence: 0.81,
    description: "Refresh tokens are not revoked when a user's password is reset, allowing continued access with a stolen token.",
    evidence: "AST rule flags missing call to revoke_all_sessions() inside reset_password(); matches 3 historical fix commits.",
    source: "custom-rule",
  },
  {
    id: "sec-3",
    repositoryId: "repo-orbit-payments",
    componentId: "comp-api-session",
    severity: "MEDIUM",
    category: "Sensitive Data Exposure",
    file: "api/middleware/session.py",
    line: 88,
    confidence: 0.64,
    description: "Session cookie is set without the Secure attribute on non-production config fallback.",
    evidence: "Bandit B614-style pattern match; confirmed only reachable when ENV=local, low production exploitability.",
    source: "bandit",
  },
  {
    id: "sec-4",
    repositoryId: "repo-orbit-payments",
    componentId: "comp-payment-service",
    severity: "MEDIUM",
    category: "Improper Idempotency Handling",
    file: "payment/service.py",
    line: 134,
    confidence: 0.58,
    description: "Retried payment intents can be double-submitted if the idempotency key store is unavailable.",
    evidence: "ML risk model flags based on similarity to 1 historical double-charge incident.",
    source: "ml-risk-model",
  },
];

export const repositoryGraphs: Record<string, RepositoryGraph> = {
  "repo-orbit-payments": {
    nodes: [
      { id: "repo-orbit-payments", label: "orbit-payments", type: "repository" },
      { id: "comp-auth-service", label: "auth/service.py", type: "file", riskLevel: "CRITICAL", path: "auth/service.py" },
      { id: "comp-payment-service", label: "payment/service.py", type: "file", riskLevel: "HIGH", path: "payment/service.py" },
      { id: "comp-orders-checkout", label: "orders/checkout.py", type: "file", riskLevel: "HIGH", path: "orders/checkout.py" },
      { id: "comp-orders-order", label: "orders/order.py", type: "file", riskLevel: "MEDIUM", path: "orders/order.py" },
      { id: "comp-billing-invoice", label: "billing/invoice.py", type: "file", riskLevel: "MEDIUM", path: "billing/invoice.py" },
      { id: "comp-api-session", label: "api/middleware/session.py", type: "file", riskLevel: "MEDIUM", path: "api/middleware/session.py" },
      { id: "comp-webhooks-stripe", label: "integrations/stripe_webhook.py", type: "file", riskLevel: "HIGH", path: "integrations/stripe_webhook.py" },
      { id: "comp-cart-utils", label: "orders/cart_utils.ts", type: "file", riskLevel: "LOW", path: "orders/cart_utils.ts" },
      { id: "fn-validate-session", label: "validate_session()", type: "function", riskLevel: "CRITICAL" },
      { id: "fn-charge", label: "charge()", type: "function", riskLevel: "HIGH" },
      { id: "cls-order-repo", label: "OrderRepository", type: "class", riskLevel: "MEDIUM" },
      { id: "dep-stripe-sdk", label: "stripe-python", type: "dependency" },
      { id: "dep-redis", label: "redis-py", type: "dependency" },
      { id: "commit-a1", label: "fix: revoke tokens on reset", type: "commit" },
      { id: "pr-124", label: "PR #124", type: "pull_request" },
    ],
    edges: [
      { id: "e1", source: "comp-payment-service", target: "comp-auth-service", type: "CALLS" },
      { id: "e2", source: "comp-orders-checkout", target: "comp-payment-service", type: "CALLS" },
      { id: "e3", source: "comp-orders-checkout", target: "comp-auth-service", type: "CALLS" },
      { id: "e4", source: "comp-orders-order", target: "comp-orders-checkout", type: "DEPENDS_ON" },
      { id: "e5", source: "comp-billing-invoice", target: "comp-payment-service", type: "DEPENDS_ON" },
      { id: "e6", source: "comp-billing-invoice", target: "comp-orders-order", type: "DEPENDS_ON" },
      { id: "e7", source: "comp-api-session", target: "comp-auth-service", type: "IMPORTS" },
      { id: "e8", source: "comp-orders-checkout", target: "comp-api-session", type: "CALLS" },
      { id: "e9", source: "comp-webhooks-stripe", target: "comp-payment-service", type: "CALLS" },
      { id: "e10", source: "comp-payment-service", target: "dep-stripe-sdk", type: "IMPORTS" },
      { id: "e11", source: "comp-webhooks-stripe", target: "dep-stripe-sdk", type: "IMPORTS" },
      { id: "e12", source: "comp-api-session", target: "dep-redis", type: "IMPORTS" },
      { id: "e13", source: "comp-auth-service", target: "fn-validate-session", type: "DEFINES" },
      { id: "e14", source: "comp-payment-service", target: "fn-charge", type: "DEFINES" },
      { id: "e15", source: "comp-orders-order", target: "cls-order-repo", type: "DEFINES" },
      { id: "e16", source: "comp-orders-checkout", target: "cls-order-repo", type: "CALLS" },
      { id: "e17", source: "comp-orders-checkout", target: "comp-orders-order", type: "CO_CHANGED_WITH" },
      { id: "e18", source: "comp-auth-service", target: "commit-a1", type: "MODIFIED_BY" },
      { id: "e19", source: "pr-124", target: "comp-auth-service", type: "MODIFIED_BY" },
      { id: "e20", source: "pr-124", target: "comp-payment-service", type: "MODIFIED_BY" },
      { id: "e21", source: "pr-124", target: "comp-orders-order", type: "MODIFIED_BY" },
    ],
  },
};

export const pullRequests: PullRequestReview[] = [
  {
    id: "pr-124",
    repositoryId: "repo-orbit-payments",
    number: 124,
    title: "Add retry handling to checkout payment flow",
    author: "r.iyer",
    authorAvatar: "RI",
    branch: "feat/checkout-retry",
    baseBranch: "main",
    status: "open",
    createdAt: daysAgo(1),
    reviewStatus: "completed",
    bugRisk: "HIGH",
    securityRisk: "MEDIUM",
    regressionRisk: "HIGH",
    aiSummary:
      "This change touches the authentication and payment core paths directly. auth.py and payment.py are both top-decile risk components with a history of related defects, and the retry logic in payment.py closely resembles a prior double-charge incident. Recommend a focused review of idempotency handling and session revocation before merge.",
    changedFiles: [
      { path: "auth.py", additions: 18, deletions: 4, riskLevel: "CRITICAL" },
      { path: "payment.py", additions: 61, deletions: 12, riskLevel: "HIGH" },
      { path: "order.py", additions: 9, deletions: 2, riskLevel: "MEDIUM" },
    ],
    potentiallyAffected: [
      { path: "session.py", reason: "Imports auth.py:validate_session(), which changed signature.", riskLevel: "HIGH", hops: 1 },
      { path: "checkout.py", reason: "Calls payment.py:charge() on the modified retry path.", riskLevel: "HIGH", hops: 1 },
      { path: "invoice.py", reason: "Depends on payment.py transitively via checkout.py.", riskLevel: "MEDIUM", hops: 2 },
    ],
    recommendedTests: [
      { name: "Authentication tests", reason: "auth.py session validation logic changed.", priority: "CRITICAL", suite: "tests/auth/" },
      { name: "Payment-flow tests", reason: "New retry branch in charge() is untested for idempotency.", priority: "HIGH", suite: "tests/payment/" },
      { name: "Order-flow tests", reason: "order.py consumes the modified payment response shape.", priority: "MEDIUM", suite: "tests/orders/" },
    ],
  },
  {
    id: "pr-118",
    repositoryId: "repo-orbit-payments",
    number: 118,
    title: "Harden Stripe webhook signature verification",
    author: "s.chen",
    authorAvatar: "SC",
    branch: "fix/webhook-signature",
    baseBranch: "main",
    status: "merged",
    createdAt: daysAgo(9),
    reviewStatus: "completed",
    bugRisk: "LOW",
    securityRisk: "HIGH",
    regressionRisk: "LOW",
    aiSummary:
      "Security-focused fix closing the missing signature verification branch flagged by static analysis. Limited blast radius: only the webhook entrypoint changed, no downstream call-graph impact detected.",
    changedFiles: [
      { path: "integrations/stripe_webhook.py", additions: 22, deletions: 3, riskLevel: "HIGH" },
    ],
    potentiallyAffected: [
      { path: "payment/service.py", reason: "Receives events forwarded from the webhook handler.", riskLevel: "LOW", hops: 1 },
    ],
    recommendedTests: [
      { name: "Webhook security tests", reason: "Signature verification branch is new.", priority: "HIGH", suite: "tests/integrations/" },
    ],
  },
];

export const analysisJobs: Record<string, AnalysisJob> = {
  "repo-growth-analytics": {
    repositoryId: "repo-growth-analytics",
    status: "running_models",
    progress: 72,
    startedAt: daysAgo(0),
    steps: [
      { key: "clone", label: "Cloning repository", status: "done", detail: "212 files fetched" },
      { key: "parse", label: "Parsing source (Tree-sitter + AST)", status: "done", detail: "Python detected across 212 files" },
      { key: "graph", label: "Building dependency & call graph", status: "done", detail: "1,340 edges constructed" },
      { key: "history", label: "Analyzing Git history", status: "done", detail: "2,104 commits processed" },
      { key: "models", label: "Running risk models", status: "active", detail: "Scoring defect, security & regression risk" },
      { key: "index", label: "Indexing historical embeddings", status: "pending" },
      { key: "finalize", label: "Computing repository health score", status: "pending" },
    ],
  },
};

export interface CommitEntry {
  sha: string;
  message: string;
  author: string;
  date: string;
  isBugFix: boolean;
}

const commitHistory: Record<string, CommitEntry[]> = {
  "comp-auth-service": [
    { sha: "a1c4e2f", message: "fix: revoke refresh tokens on password reset", author: "r.iyer", date: daysAgo(1), isBugFix: true },
    { sha: "9b7d310", message: "refactor: extract validate_session() from authenticate()", author: "r.iyer", date: daysAgo(8), isBugFix: false },
    { sha: "4e08a91", message: "fix: race condition in concurrent login attempts", author: "r.iyer", date: daysAgo(21), isBugFix: true },
    { sha: "7fbcaa2", message: "feat: add device-fingerprint claim to session token", author: "s.chen", date: daysAgo(34), isBugFix: false },
    { sha: "12e9d4c", message: "fix: JWT clock-skew tolerance too strict", author: "r.iyer", date: daysAgo(52), isBugFix: true },
    { sha: "c03f7b1", message: "chore: type hints for session helpers", author: "s.chen", date: daysAgo(66), isBugFix: false },
  ],
  "comp-payment-service": [
    { sha: "d92aa71", message: "feat: add retry handling to checkout payment flow", author: "r.iyer", date: daysAgo(1), isBugFix: false },
    { sha: "5b1c0e4", message: "fix: idempotency key not enforced on retry path", author: "r.iyer", date: daysAgo(19), isBugFix: true },
    { sha: "e77aa10", message: "feat: partial refund support", author: "s.chen", date: daysAgo(40), isBugFix: false },
    { sha: "8a4f221", message: "fix: currency rounding error on split payments", author: "r.iyer", date: daysAgo(58), isBugFix: true },
  ],
  "comp-webhooks-stripe": [
    { sha: "22cfe6b", message: "fix: verify Stripe-Signature header on retry path", author: "s.chen", date: daysAgo(9), isBugFix: true },
    { sha: "6dd9f02", message: "feat: handle payment_intent.requires_action event", author: "s.chen", date: daysAgo(70), isBugFix: false },
  ],
};

export function getCommitHistory(componentId: string): CommitEntry[] {
  if (commitHistory[componentId]) return commitHistory[componentId];
  const component = getComponent(componentId);
  return [
    {
      sha: "b18e4aa",
      message: `chore: update ${component?.name ?? "module"}`,
      author: component?.lastModifiedBy ?? "unknown",
      date: component?.lastModified ?? daysAgo(10),
      isBugFix: false,
    },
  ];
}

const codeSnippets: Record<string, string> = {
  "comp-auth-service": `def reset_password(user_id: str, new_password: str) -> None:
    user = user_repository.get(user_id)
    user.password_hash = hash_password(new_password)
    user_repository.save(user)
    # NOTE: refresh tokens issued before this point remain valid.
    # revoke_all_sessions(user_id) is not called on this path.
    audit_log.record("password_reset", user_id=user_id)


def validate_session(token: str) -> Session:
    payload = jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
    session = session_store.get(payload["sid"])
    if session is None or session.revoked:
        raise InvalidSessionError()
    return session`,
  "comp-payment-service": `def charge(order_id: str, amount_cents: int, idempotency_key: str) -> ChargeResult:
    existing = idempotency_store.get(idempotency_key)
    if existing:
        return existing.result

    intent = stripe.PaymentIntent.create(
        amount=amount_cents,
        currency="usd",
        metadata={"order_id": order_id},
    )
    result = ChargeResult(intent_id=intent.id, status=intent.status)
    idempotency_store.set(idempotency_key, result, ttl_seconds=86400)
    return result`,
  "comp-webhooks-stripe": `@app.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    if not RETRY_PATH_VERIFIES_SIGNATURE:
        event = json.loads(payload)  # signature check skipped on retry
    else:
        event = stripe.Webhook.construct_event(payload, signature, WEBHOOK_SECRET)

    await dispatch_event(event)
    return {"received": True}`,
};

export function getCodeSnippet(componentId: string): string {
  if (codeSnippets[componentId]) return codeSnippets[componentId];
  const component = getComponent(componentId);
  return `// ${component?.path ?? "unknown file"}\n// Source preview is not available in this demo dataset.`;
}

export function getRepository(id: string): Repository | undefined {
  return repositories.find((r) => r.id === id);
}

export function getComponentsForRepo(repositoryId: string): ComponentRisk[] {
  return components.filter((c) => c.repositoryId === repositoryId);
}

export function getComponent(id: string): ComponentRisk | undefined {
  return components.find((c) => c.id === id);
}

export function getSecurityFindingsForRepo(repositoryId: string): SecurityFinding[] {
  return securityFindings.filter((s) => s.repositoryId === repositoryId);
}

export function getPullRequestsForRepo(repositoryId: string): PullRequestReview[] {
  return pullRequests.filter((p) => p.repositoryId === repositoryId);
}

export function getPullRequest(id: string): PullRequestReview | undefined {
  return pullRequests.find((p) => p.id === id);
}
