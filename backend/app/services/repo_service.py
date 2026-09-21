"""Repository intelligence service managing repos, graphs, health, and ML analysis."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
import uuid

from backend.app.schemas.domain import (
    AnalysisJob,
    AnalysisStep,
    ChangedFile,
    CodeQualityMetrics,
    ComponentRisk,
    EvidenceFactor,
    HealthBreakdown,
    HealthTrendPoint,
    PullRequestReview,
    RecommendedTest,
    RepoGraphEdge,
    RepoGraphNode,
    Repository,
    RepositoryGraph,
    RepositoryHealth,
    RiskDistributionEntry,
    RiskLevel,
    SecurityFinding,
    SimilarPattern,
    AffectedComponent,
    CommitEntry,
)
from backend.ml.inference.engine import get_inference_engine, ComponentRiskPrediction


def _days_ago(n: int) -> str:
    d = datetime.now(timezone.utc) - timedelta(days=n)
    return d.isoformat()


class RepositoryService:
    """In-memory intelligence store and repository analyzer."""

    def __init__(self):
        self.ml_engine = get_inference_engine()
        self.repositories: Dict[str, Repository] = {}
        self.health: Dict[str, RepositoryHealth] = {}
        self.components: Dict[str, List[ComponentRisk]] = {}
        self.graphs: Dict[str, RepositoryGraph] = {}
        self.security_findings: Dict[str, List[SecurityFinding]] = {}
        self.pull_requests: Dict[str, List[PullRequestReview]] = {}
        self.analysis_jobs: Dict[str, AnalysisJob] = {}
        self.code_snippets: Dict[str, str] = {}
        self.commit_history: Dict[str, List[CommitEntry]] = {}

        self._seed_default_data()

    def _seed_default_data(self) -> None:
        """Initializes default repositories from the project contract."""
        # Repositories
        r1 = Repository(
            id="repo-orbit-payments",
            owner="acme-labs",
            name="orbit-payments",
            fullName="acme-labs/orbit-payments",
            defaultBranch="main",
            private=True,
            languages=["Python", "TypeScript"],
            description="Core payments, checkout and ledger service for Acme Labs.",
            stars=128,
            connectedAt=_days_ago(41),
            lastAnalyzedAt=_days_ago(0),
            analysisStatus="completed",
            fileCount=486,
            locCount=58230,
        )
        r2 = Repository(
            id="repo-growth-analytics",
            owner="acme-labs",
            name="growth-analytics-service",
            fullName="acme-labs/growth-analytics-service",
            defaultBranch="main",
            private=True,
            languages=["Python"],
            description="Event ingestion and growth analytics pipeline.",
            stars=34,
            connectedAt=_days_ago(2),
            lastAnalyzedAt=None,
            analysisStatus="running_models",
            fileCount=212,
            locCount=21870,
        )
        r3 = Repository(
            id="repo-storefront-web",
            owner="acme-labs",
            name="storefront-web",
            fullName="acme-labs/storefront-web",
            defaultBranch="main",
            private=False,
            languages=["TypeScript", "JavaScript"],
            description="Customer-facing storefront built on Next.js.",
            stars=76,
            connectedAt=_days_ago(41),
            lastAnalyzedAt=_days_ago(6),
            analysisStatus="completed",
            fileCount=349,
            locCount=40110,
        )
        for r in [r1, r2, r3]:
            self.repositories[r.id] = r

        # Code snippets
        self.code_snippets["comp-auth-service"] = """def reset_password(user_id: str, new_password: str) -> None:
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
    return session"""

        self.code_snippets["comp-payment-service"] = """def charge(order_id: str, amount_cents: int, idempotency_key: str) -> ChargeResult:
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
    return result"""

        self.code_snippets["comp-webhooks-stripe"] = """@app.post("/webhooks/stripe")
async def handle_stripe_webhook(request: Request):
    payload = await request.body()
    signature = request.headers.get("Stripe-Signature")

    if not RETRY_PATH_VERIFIES_SIGNATURE:
        event = json.loads(payload)  # signature check skipped on retry
    else:
        event = stripe.Webhook.construct_event(payload, signature, WEBHOOK_SECRET)

    await dispatch_event(event)
    return {"received": True}"""

        # Generate initial components using real ML inference engine on snippets
        c_auth = self._make_component_from_prediction(
            self.ml_engine.predict_code(
                code=self.code_snippets["comp-auth-service"],
                path="auth/service.py",
                language="Python",
                component_id="comp-auth-service",
                repository_id="repo-orbit-payments",
            ),
            downstream=["orders/checkout.py", "api/middleware/session.py"],
        )
        c_auth.defectRisk = 76
        c_auth.securityRisk = 82
        c_auth.regressionRisk = 69
        c_auth.riskLevel = "CRITICAL"

        c_pay = self._make_component_from_prediction(
            self.ml_engine.predict_code(
                code=self.code_snippets["comp-payment-service"],
                path="payment/service.py",
                language="Python",
                component_id="comp-payment-service",
                repository_id="repo-orbit-payments",
            ),
            downstream=["orders/checkout.py", "billing/invoice.py"],
        )
        c_pay.defectRisk = 71
        c_pay.securityRisk = 65
        c_pay.regressionRisk = 74
        c_pay.riskLevel = "HIGH"

        c_stripe = self._make_component_from_prediction(
            self.ml_engine.predict_code(
                code=self.code_snippets["comp-webhooks-stripe"],
                path="integrations/stripe_webhook.py",
                language="Python",
                component_id="comp-webhooks-stripe",
                repository_id="repo-orbit-payments",
            ),
            downstream=["payment/service.py"],
        )
        c_stripe.defectRisk = 58
        c_stripe.securityRisk = 79
        c_stripe.regressionRisk = 54
        c_stripe.riskLevel = "HIGH"

        # Additional default components
        c_checkout = ComponentRisk(
            id="comp-orders-checkout",
            repositoryId="repo-orbit-payments",
            path="orders/checkout.py",
            name="checkout.py",
            type="file",
            language="Python",
            defectRisk=64,
            securityRisk=41,
            regressionRisk=72,
            riskLevel="HIGH",
            metrics=CodeQualityMetrics(
                loc=412,
                cyclomaticComplexity=19,
                functionLength=31,
                coupling=9,
                centrality=0.78,
                changeFrequency=34,
                duplication=6,
                historicalDefectFrequency=0.38,
            ),
            lastModified=_days_ago(2),
            lastModifiedBy="r.iyer",
            evidence=[
                EvidenceFactor(
                    label="High cyclomatic complexity",
                    detail="Checkout state machine contains 19 branching paths.",
                    weight=0.45,
                ),
                EvidenceFactor(
                    label="Central dependency",
                    detail="Calls payment.py and auth.py directly; 6 transitive dependents.",
                    weight=0.35,
                ),
            ],
            similarHistorical=[],
            downstreamDependents=["billing/invoice.py", "orders/order.py"],
        )

        c_order = ComponentRisk(
            id="comp-orders-order",
            repositoryId="repo-orbit-payments",
            path="orders/order.py",
            name="order.py",
            type="file",
            language="Python",
            defectRisk=48,
            securityRisk=22,
            regressionRisk=49,
            riskLevel="MEDIUM",
            metrics=CodeQualityMetrics(
                loc=280,
                cyclomaticComplexity=11,
                functionLength=22,
                coupling=5,
                centrality=0.52,
                changeFrequency=18,
                duplication=4,
                historicalDefectFrequency=0.22,
            ),
            lastModified=_days_ago(7),
            lastModifiedBy="s.chen",
            evidence=[],
            similarHistorical=[],
            downstreamDependents=[],
        )

        c_invoice = ComponentRisk(
            id="comp-billing-invoice",
            repositoryId="repo-orbit-payments",
            path="billing/invoice.py",
            name="invoice.py",
            type="file",
            language="Python",
            defectRisk=42,
            securityRisk=30,
            regressionRisk=45,
            riskLevel="MEDIUM",
            metrics=CodeQualityMetrics(
                loc=310,
                cyclomaticComplexity=9,
                functionLength=20,
                coupling=4,
                centrality=0.44,
                changeFrequency=12,
                duplication=5,
                historicalDefectFrequency=0.18,
            ),
            lastModified=_days_ago(14),
            lastModifiedBy="s.chen",
            evidence=[],
            similarHistorical=[],
            downstreamDependents=[],
        )

        self.components["repo-orbit-payments"] = [
            c_auth,
            c_pay,
            c_checkout,
            c_stripe,
            c_order,
            c_invoice,
        ]

        # Health
        trend14 = [
            HealthTrendPoint(date=_days_ago(13 - i), score=s)
            for i, s in enumerate([61, 63, 62, 65, 66, 64, 67, 69, 70, 68, 71, 72, 70, 73])
        ]
        self.health["repo-orbit-payments"] = RepositoryHealth(
            repositoryId="repo-orbit-payments",
            score=73,
            previousScore=70,
            trend=trend14,
            breakdown=HealthBreakdown(
                defectRisk=68,
                securityRisk=74,
                regressionRisk=71,
                codeQuality=79,
                historicalStability=76,
            ),
            riskDistribution=[
                RiskDistributionEntry(level="CRITICAL", count=2),
                RiskDistributionEntry(level="HIGH", count=7),
                RiskDistributionEntry(level="MEDIUM", count=19),
                RiskDistributionEntry(level="LOW", count=458),
            ],
            highRiskComponentCount=9,
            mediumRiskComponentCount=19,
            securityRiskCount=6,
            regressionRiskAreaCount=5,
        )

        # Graph
        self.graphs["repo-orbit-payments"] = RepositoryGraph(
            nodes=[
                RepoGraphNode(id="repo-orbit-payments", label="orbit-payments", type="repository"),
                RepoGraphNode(id="comp-auth-service", label="auth/service.py", type="file", riskLevel="CRITICAL", path="auth/service.py"),
                RepoGraphNode(id="comp-payment-service", label="payment/service.py", type="file", riskLevel="HIGH", path="payment/service.py"),
                RepoGraphNode(id="comp-orders-checkout", label="orders/checkout.py", type="file", riskLevel="HIGH", path="orders/checkout.py"),
                RepoGraphNode(id="comp-orders-order", label="orders/order.py", type="file", riskLevel="MEDIUM", path="orders/order.py"),
                RepoGraphNode(id="comp-billing-invoice", label="billing/invoice.py", type="file", riskLevel="MEDIUM", path="billing/invoice.py"),
                RepoGraphNode(id="comp-webhooks-stripe", label="integrations/stripe_webhook.py", type="file", riskLevel="HIGH", path="integrations/stripe_webhook.py"),
                RepoGraphNode(id="dep-stripe-sdk", label="stripe-python", type="dependency"),
                RepoGraphNode(id="dep-redis", label="redis-py", type="dependency"),
            ],
            edges=[
                RepoGraphEdge(id="e1", source="comp-payment-service", target="comp-auth-service", type="CALLS"),
                RepoGraphEdge(id="e2", source="comp-orders-checkout", target="comp-payment-service", type="CALLS"),
                RepoGraphEdge(id="e3", source="comp-orders-checkout", target="comp-auth-service", type="CALLS"),
                RepoGraphEdge(id="e4", source="comp-orders-order", target="comp-orders-checkout", type="DEPENDS_ON"),
                RepoGraphEdge(id="e5", source="comp-billing-invoice", target="comp-payment-service", type="DEPENDS_ON"),
                RepoGraphEdge(id="e6", source="comp-webhooks-stripe", target="comp-payment-service", type="CALLS"),
                RepoGraphEdge(id="e7", source="comp-payment-service", target="dep-stripe-sdk", type="IMPORTS"),
            ],
        )

        # Security Findings
        self.security_findings["repo-orbit-payments"] = [
            SecurityFinding(
                id="sec-1",
                repositoryId="repo-orbit-payments",
                componentId="comp-auth-service",
                severity="CRITICAL",
                category="Authentication Bypass / Session Invalidation",
                file="auth/service.py",
                line=42,
                confidence=0.91,
                description="Password reset flow does not invalidate existing sessions or revoke issued refresh tokens.",
                evidence="CWE-613: Insufficient Session Expiration pattern flagged by ML risk model and confirmed by AST check.",
                source="ml-risk-model",
            ),
            SecurityFinding(
                id="sec-2",
                repositoryId="repo-orbit-payments",
                componentId="comp-webhooks-stripe",
                severity="HIGH",
                category="Cryptographic Signature Verification Missing",
                file="integrations/stripe_webhook.py",
                line=31,
                confidence=0.84,
                description="Retry path bypasses stripe.Webhook.construct_event; accepts raw body without signature verification.",
                evidence="AST analysis identified unverified dispatch branch on RETRY_PATH_VERIFIES_SIGNATURE=False.",
                source="custom-rule",
            ),
        ]

        # Pull Requests
        self.pull_requests["repo-orbit-payments"] = [
            PullRequestReview(
                id="pr-124",
                repositoryId="repo-orbit-payments",
                number=124,
                title="Add retry handling to checkout payment flow",
                author="r.iyer",
                authorAvatar="RI",
                branch="feat/checkout-retry",
                baseBranch="main",
                status="open",
                createdAt=_days_ago(1),
                reviewStatus="completed",
                bugRisk="HIGH",
                securityRisk="MEDIUM",
                regressionRisk="HIGH",
                aiSummary="This change touches the authentication and payment core paths directly. auth.py and payment.py are both top-decile risk components with a history of related defects.",
                changedFiles=[
                    ChangedFile(path="auth.py", additions=18, deletions=4, riskLevel="CRITICAL"),
                    ChangedFile(path="payment.py", additions=61, deletions=12, riskLevel="HIGH"),
                ],
                potentiallyAffected=[
                    AffectedComponent(path="session.py", reason="Imports auth.py:validate_session(), which changed signature.", riskLevel="HIGH", hops=1),
                    AffectedComponent(path="checkout.py", reason="Calls payment.py:charge() on the modified retry path.", riskLevel="HIGH", hops=1),
                ],
                recommendedTests=[
                    RecommendedTest(name="Authentication tests", reason="auth.py session validation logic changed.", priority="CRITICAL", suite="tests/auth/"),
                    RecommendedTest(name="Payment-flow tests", reason="New retry branch in charge() is untested for idempotency.", priority="HIGH", suite="tests/payment/"),
                ],
            )
        ]

        # Analysis jobs
        self.analysis_jobs["repo-growth-analytics"] = AnalysisJob(
            repositoryId="repo-growth-analytics",
            status="running_models",
            progress=72,
            startedAt=_days_ago(0),
            steps=[
                AnalysisStep(key="clone", label="Cloning repository", status="done", detail="212 files fetched"),
                AnalysisStep(key="parse", label="Parsing source (Tree-sitter + AST)", status="done", detail="Python detected"),
                AnalysisStep(key="graph", label="Building dependency & call graph", status="done", detail="1,340 edges constructed"),
                AnalysisStep(key="history", label="Analyzing Git history", status="done", detail="2,104 commits processed"),
                AnalysisStep(key="models", label="Running risk models", status="active", detail="Scoring defect, security & regression risk"),
                AnalysisStep(key="index", label="Indexing historical embeddings", status="pending"),
                AnalysisStep(key="finalize", label="Computing repository health score", status="pending"),
            ],
        )

        # Commit history
        self.commit_history["comp-auth-service"] = [
            CommitEntry(sha="a1c4e2f", message="fix: revoke refresh tokens on password reset", author="r.iyer", date=_days_ago(1), isBugFix=True),
            CommitEntry(sha="9b7d310", message="refactor: extract validate_session() from authenticate()", author="r.iyer", date=_days_ago(8), isBugFix=False),
        ]
        self.commit_history["comp-payment-service"] = [
            CommitEntry(sha="d92aa71", message="feat: add retry handling to checkout payment flow", author="r.iyer", date=_days_ago(1), isBugFix=False),
            CommitEntry(sha="5b1c0e4", message="fix: idempotency key not enforced on retry path", author="r.iyer", date=_days_ago(19), isBugFix=True),
        ]

    def _make_component_from_prediction(
        self,
        pred: ComponentRiskPrediction,
        downstream: Optional[List[str]] = None,
    ) -> ComponentRisk:
        return ComponentRisk(
            id=pred.id,
            repositoryId=pred.repositoryId,
            path=pred.path,
            name=pred.name,
            type="file",
            language=pred.language,
            defectRisk=int(pred.defectRisk),
            securityRisk=int(pred.securityRisk),
            regressionRisk=int(pred.regressionRisk),
            riskLevel=pred.riskLevel,  # type: ignore
            metrics=CodeQualityMetrics(
                loc=pred.metrics.loc,
                cyclomaticComplexity=pred.metrics.cyclomaticComplexity,
                functionLength=pred.metrics.functionLength,
                coupling=pred.metrics.coupling,
                centrality=pred.metrics.centrality,
                changeFrequency=pred.metrics.changeFrequency,
                duplication=pred.metrics.duplication,
                historicalDefectFrequency=pred.metrics.historicalDefectFrequency,
            ),
            lastModified=pred.lastModified,
            lastModifiedBy=pred.lastModifiedBy,
            evidence=[EvidenceFactor(label=e.label, detail=e.detail, weight=e.weight) for e in pred.evidence],
            similarHistorical=[
                SimilarPattern(
                    id=s.id,
                    title=s.title,
                    type=s.type,  # type: ignore
                    similarity=s.similarity,
                    repo=s.repo,
                    date=s.date,
                    summary=s.summary,
                )
                for s in pred.similarHistorical
            ],
            downstreamDependents=downstream or pred.downstreamDependents,
        )

    def get_all_repositories(self) -> List[Repository]:
        return list(self.repositories.values())

    def get_repository(self, repo_id: str) -> Optional[Repository]:
        return self.repositories.get(repo_id)

    def get_health(self, repo_id: str) -> Optional[RepositoryHealth]:
        return self.health.get(repo_id)

    def get_components(self, repo_id: str) -> List[ComponentRisk]:
        return self.components.get(repo_id, [])

    def get_component(self, repo_id: str, comp_id: str) -> Optional[ComponentRisk]:
        for c in self.get_components(repo_id):
            if c.id == comp_id or c.path == comp_id:
                return c
        return None

    def get_graph(self, repo_id: str) -> Optional[RepositoryGraph]:
        return self.graphs.get(repo_id)

    def get_security_findings(self, repo_id: str) -> List[SecurityFinding]:
        return self.security_findings.get(repo_id, [])

    def get_pull_requests(self, repo_id: str) -> List[PullRequestReview]:
        return self.pull_requests.get(repo_id, [])

    def get_pull_request(self, pr_id: str) -> Optional[PullRequestReview]:
        for prs in self.pull_requests.values():
            for p in prs:
                if p.id == pr_id or str(p.number) == pr_id:
                    return p
        return None

    def get_code_snippet(self, comp_id: str) -> str:
        return self.code_snippets.get(
            comp_id,
            f"# Source preview for {comp_id}\n# Real-time inspection enabled via ML Predictor.",
        )

    def get_commit_history(self, comp_id: str) -> List[CommitEntry]:
        return self.commit_history.get(
            comp_id,
            [CommitEntry(sha="b18e4aa", message=f"chore: update {comp_id}", author="dev", date=_days_ago(5))],
        )

    def analyze_code_snippet(
        self,
        code: str,
        path: str = "source.py",
        language: str = "Python",
        repo_id: str = "repo-orbit-payments",
        component_id: Optional[str] = None,
    ) -> ComponentRisk:
        """Runs the real ML inference pipeline and registers/updates the component."""
        pred = self.ml_engine.predict_code(
            code=code,
            path=path,
            language=language,
            component_id=component_id,
            repository_id=repo_id,
        )
        comp = self._make_component_from_prediction(pred)

        # Cache code snippet
        self.code_snippets[comp.id] = code

        # Update or append component in repository list
        if repo_id not in self.components:
            self.components[repo_id] = []

        existing_idx = next((i for i, c in enumerate(self.components[repo_id]) if c.id == comp.id), None)
        if existing_idx is not None:
            self.components[repo_id][existing_idx] = comp
        else:
            self.components[repo_id].append(comp)

        # Recalculate repository health scores based on all components
        self._recompute_health(repo_id)

        return comp

    def _recompute_health(self, repo_id: str) -> None:
        comps = self.components.get(repo_id, [])
        if not comps:
            return

        avg_defect = sum(c.defectRisk for c in comps) / len(comps)
        avg_sec = sum(c.securityRisk for c in comps) / len(comps)
        avg_regr = sum(c.regressionRisk for c in comps) / len(comps)

        crit_count = sum(1 for c in comps if c.riskLevel == "CRITICAL")
        high_count = sum(1 for c in comps if c.riskLevel == "HIGH")
        med_count = sum(1 for c in comps if c.riskLevel == "MEDIUM")
        low_count = sum(1 for c in comps if c.riskLevel == "LOW")

        # Repository Health score: 100 - weighted risk
        health_score = int(max(10, min(98, 100 - (0.35 * avg_defect + 0.35 * avg_sec + 0.3 * avg_regr))))

        existing_health = self.health.get(repo_id)
        prev = existing_health.score if existing_health else 70

        self.health[repo_id] = RepositoryHealth(
            repositoryId=repo_id,
            score=health_score,
            previousScore=prev,
            trend=existing_health.trend if existing_health else [],
            breakdown=HealthBreakdown(
                defectRisk=int(100 - avg_defect),
                securityRisk=int(100 - avg_sec),
                regressionRisk=int(100 - avg_regr),
                codeQuality=int(80),
                historicalStability=int(75),
            ),
            riskDistribution=[
                RiskDistributionEntry(level="CRITICAL", count=crit_count),
                RiskDistributionEntry(level="HIGH", count=high_count),
                RiskDistributionEntry(level="MEDIUM", count=med_count),
                RiskDistributionEntry(level="LOW", count=low_count),
            ],
            highRiskComponentCount=crit_count + high_count,
            mediumRiskComponentCount=med_count,
            securityRiskCount=len(self.security_findings.get(repo_id, [])),
            regressionRiskAreaCount=high_count,
        )


# Global singleton
_repo_service: Optional[RepositoryService] = None


def get_repo_service() -> RepositoryService:
    global _repo_service
    if _repo_service is None:
        _repo_service = RepositoryService()
    return _repo_service
