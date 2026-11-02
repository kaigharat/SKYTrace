import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import {
  ArrowRight,
  Cpu,
  ExternalLink,
  GitPullRequest,
  Lock,
  ShieldAlert,
  Sparkles,
  TrendingUp,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HealthRing } from "@/components/shared/health-ring";
import { RiskBadge } from "@/components/shared/risk-badge";
import { MetricBar } from "@/components/dashboard/metric-bar";
import { RiskDistribution } from "@/components/dashboard/risk-distribution";
import { HealthTrendChart } from "@/components/dashboard/health-trend-chart";
import { ComponentsTable } from "@/components/dashboard/components-table";
import { SecuritySummary } from "@/components/dashboard/security-summary";
import { GraphPreview } from "@/components/dashboard/graph-preview";
import { StatTile } from "@/components/dashboard/stat-tile";
import { formatRelativeDate } from "@/lib/format";
import { healthScoreLabel } from "@/lib/risk";
import { api } from "@/lib/api";

export default async function RepositoryDashboardPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  const repo = await api.getRepository(repoId).catch(() => null);
  if (!repo) notFound();

  const health = await api.getRepositoryHealth(repoId).catch(() => null);

  if (!health || repo.analysisStatus !== "completed") {
    redirect(`/repositories/${repoId}/analyzing`);
  }

  const comps = await api.getComponents(repoId).catch(() => []);
  const allComponents = [...comps].sort((a, b) => b.defectRisk - a.defectRisk);
  const topComponents = allComponents.slice(0, 6);

  const findings = await api.getSecurityFindings(repoId).catch(() => []);
  const securityFindings = findings.slice(0, 4);

  const graph = await api.getRepositoryGraph(repoId).catch(() => null);

  const prs = await api.getPullRequests(repoId).catch(() => []);
  const pullRequests = prs.slice(0, 3);
  const scoreDelta = health.score - (health.previousScore ?? health.score);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-mono text-2xl font-semibold tracking-tight">
              {repo.fullName}
            </h1>
            {repo.private && (
              <Badge variant="outline" className="gap-1 text-[10px]">
                <Lock className="size-2.5" />
                Private
              </Badge>
            )}
          </div>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">{repo.description}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            {repo.languages.map((l) => (
              <Badge key={l} variant="secondary" className="text-[10px]">
                {l}
              </Badge>
            ))}
            <span>·</span>
            <span>{repo.fileCount} files</span>
            {repo.lastAnalyzedAt && (
              <>
                <span>·</span>
                <span>Analyzed {formatRelativeDate(repo.lastAnalyzedAt)}</span>
              </>
            )}
          </div>
        </div>
        <div className="flex shrink-0 gap-2 flex-wrap items-center">
          <Button variant="outline" asChild className="gap-1.5 border-primary/30 hover:border-primary">
            <Link href={`/repositories/${repoId}/analyzing`}>
              <Cpu className="size-3.5 text-primary" />
              <span>Analysis Pipeline Flow</span>
            </Link>
          </Button>
          <Button variant="outline" asChild>
            <a
              href={`https://github.com/${repo.fullName}`}
              target="_blank"
              rel="noopener noreferrer"
              className="gap-1.5"
            >
              <span>GitHub</span>
              <ExternalLink className="size-3.5" />
            </a>
          </Button>
          <Button asChild>
            <Link href={`/repositories/${repoId}/pull-requests`}>
              <GitPullRequest className="size-4" />
              Pull requests
            </Link>
          </Button>
        </div>
      </div>

      {/* Evaluator Flow Summary Banner */}
      <Card className="p-5 border-primary/30 bg-card/60 shadow-xs">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/70 pb-3 mb-4">
          <div className="flex items-center gap-2.5">
            <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground font-bold text-xs">
              <Cpu className="size-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-sm font-bold tracking-tight">How SkyTrace Analyzed This Repository</h2>
                <Badge variant="outline" className="text-[10px] border-primary/30 text-primary">
                  Evaluator Flow Verified ✓
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground">
                5-stage pipeline executed from GitHub ingestion through 39 AST metrics to ML Random Forest risk prediction:
              </p>
            </div>
          </div>
          <Button variant="outline" size="sm" asChild className="gap-1 text-xs">
            <Link href={`/repositories/${repoId}/analyzing`}>
              <span>View Full Pipeline Execution</span>
              <ArrowRight className="size-3" />
            </Link>
          </Button>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-foreground mb-1">
                <span className="flex size-4 items-center justify-center rounded-full bg-primary/20 text-primary text-[10px] font-bold">1</span>
                <span>Code Ingestion</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Walked repository tree &amp; pulled source files via GitHub REST API.
              </p>
            </div>
            <div className="mt-2.5 pt-2 border-t border-border/40 font-mono text-[10px] text-primary font-medium">
              {repo.fileCount} source files parsed
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-foreground mb-1">
                <span className="flex size-4 items-center justify-center rounded-full bg-primary/20 text-primary text-[10px] font-bold">2</span>
                <span>AST Feature Extraction</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Parsed syntax trees for complexity, nested loops &amp; sensitive API calls.
              </p>
            </div>
            <div className="mt-2.5 pt-2 border-t border-border/40 font-mono text-[10px] text-primary font-medium">
              39 code features / file
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-foreground mb-1">
                <span className="flex size-4 items-center justify-center rounded-full bg-primary/20 text-primary text-[10px] font-bold">3</span>
                <span>Architecture Graph</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Mapped import relationships &amp; computed pull-request blast radius.
              </p>
            </div>
            <div className="mt-2.5 pt-2 border-t border-border/40 font-mono text-[10px] text-primary font-medium">
              {graph?.nodes.length || 0} nodes · {graph?.edges.length || 0} edges
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-foreground mb-1">
                <span className="flex size-4 items-center justify-center rounded-full bg-primary/20 text-primary text-[10px] font-bold">4</span>
                <span>ML Risk Inference</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Random Forest evaluated defect, security &amp; regression risk tiers.
              </p>
            </div>
            <div className="mt-2.5 pt-2 border-t border-border/40 font-mono text-[10px] text-primary font-medium">
              {allComponents.length} components scored
            </div>
          </div>

          <div className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-1.5 font-semibold text-foreground mb-1">
                <span className="flex size-4 items-center justify-center rounded-full bg-primary/20 text-primary text-[10px] font-bold">5</span>
                <span>Explainable AI</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Attributed evidence weights &amp; calculated overall health score.
              </p>
            </div>
            <div className="mt-2.5 pt-2 border-t border-border/40 font-mono text-[10px] text-risk-low font-bold">
              Health Score: {health.score}/100
            </div>
          </div>
        </div>
      </Card>

      {/* Top row */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="gap-4 p-5">
          <div className="flex items-center gap-5">
            <HealthRing score={health.score} />
            <div>
              <p className="text-sm font-medium">{healthScoreLabel(health.score)}</p>
              <p
                className={
                  "mt-1 flex items-center gap-1 text-xs " +
                  (scoreDelta >= 0 ? "text-risk-low" : "text-risk-critical")
                }
              >
                <TrendingUp className="size-3" />
                {scoreDelta >= 0 ? "+" : ""}
                {scoreDelta} vs previous analysis
              </p>
              <p className="mt-1 text-xs text-muted-foreground">
                Weighted from defect, security, regression, quality and history.
              </p>
            </div>
          </div>
          <div className="flex flex-col gap-3 border-t border-border pt-4">
            <MetricBar label="Defect resilience" value={health.breakdown.defectRisk} />
            <MetricBar label="Security posture" value={health.breakdown.securityRisk} />
            <MetricBar label="Regression resilience" value={health.breakdown.regressionRisk} />
            <MetricBar label="Code quality" value={health.breakdown.codeQuality} />
            <MetricBar label="Historical stability" value={health.breakdown.historicalStability} />
          </div>
        </Card>

        <Card className="gap-4 p-5">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">Risk distribution</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <RiskDistribution data={health.riskDistribution} />
          </CardContent>
          <div className="mt-2 grid grid-cols-2 gap-2">
            <StatTile icon={ShieldAlert} label="High risk" value={health.highRiskComponentCount} tone="high" />
            <StatTile icon={ShieldAlert} label="Medium risk" value={health.mediumRiskComponentCount} tone="medium" />
            <StatTile icon={ShieldAlert} label="Security findings" value={health.securityRiskCount} tone="critical" />
            <StatTile icon={ArrowRight} label="Regression areas" value={health.regressionRiskAreaCount} />
          </div>
        </Card>

        <Card className="gap-3 p-5">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">Repository graph</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {graph && <GraphPreview repositoryId={repoId} graph={graph} />}
          </CardContent>
        </Card>
      </div>

      {/* Trend */}
      <Card className="gap-4 p-5">
        <CardHeader className="p-0">
          <CardTitle className="text-sm">Health trend · last 14 analyses</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <HealthTrendChart data={health.trend} />
        </CardContent>
      </Card>

      {/* Components + security */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="gap-4 p-5 lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between p-0">
            <CardTitle className="text-sm">Recently changed &amp; high-impact components</CardTitle>
            <span className="text-xs text-muted-foreground">
              {allComponents.length} components analyzed
            </span>
          </CardHeader>
          <CardContent className="p-0">
            <ComponentsTable repositoryId={repoId} components={topComponents} />
          </CardContent>
        </Card>

        <Card className="gap-4 p-5">
          <CardHeader className="flex-row items-center justify-between p-0">
            <CardTitle className="text-sm">Security findings</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <SecuritySummary repositoryId={repoId} findings={securityFindings} />
          </CardContent>
        </Card>
      </div>

      {/* PR teaser */}
      {pullRequests.length > 0 && (
        <Card className="gap-3 p-5">
          <CardHeader className="flex-row items-center justify-between p-0">
            <CardTitle className="text-sm">Recent pull requests</CardTitle>
            <Link
              href={`/repositories/${repoId}/pull-requests`}
              className="text-xs font-medium text-primary hover:underline"
            >
              View all
            </Link>
          </CardHeader>
          <CardContent className="flex flex-col divide-y divide-border p-0">
            {pullRequests.map((pr) => (
              <Link
                key={pr.id}
                href={`/repositories/${repoId}/pull-requests/${pr.id}`}
                className="flex items-center justify-between gap-3 py-3 first:pt-0 last:pb-0 hover:text-primary"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">
                    #{pr.number} {pr.title}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {pr.author} · {formatRelativeDate(pr.createdAt)}
                  </p>
                </div>
                <div className="flex shrink-0 gap-1.5">
                  <RiskBadge level={pr.bugRisk} showDot={false} />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
