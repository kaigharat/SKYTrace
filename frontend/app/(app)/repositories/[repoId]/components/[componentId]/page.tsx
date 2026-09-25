import Link from "next/link";
import { notFound } from "next/navigation";
import { Network, ShieldAlert, Sparkles } from "lucide-react";
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from "@/components/ui/breadcrumb";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/shared/risk-badge";
import { RiskScorePanel } from "@/components/component-detail/risk-score-panel";
import { EvidenceList } from "@/components/component-detail/evidence-list";
import { SimilarPatterns } from "@/components/component-detail/similar-patterns";
import { CodeSheet } from "@/components/component-detail/code-sheet";
import { HistorySheet } from "@/components/component-detail/history-sheet";
import {
  components as mockComponents,
  getCodeSnippet,
  getCommitHistory,
  getComponent,
  getRepository,
  getSecurityFindingsForRepo,
} from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";
import { api } from "@/lib/api";
import { LiveMLInspector } from "@/components/component-detail/live-ml-inspector";

export default async function ComponentDetailPage({
  params,
}: {
  params: Promise<{ repoId: string; componentId: string }>;
}) {
  const { repoId, componentId } = await params;

  // Try fetching from backend API, fall back to mock data
  const repo = (await api.getRepository(repoId).catch(() => null)) ?? getRepository(repoId);
  const component = (await api.getComponent(repoId, componentId).catch(() => null)) ?? getComponent(componentId);
  if (!repo || !component || component.repositoryId !== repoId) notFound();

  let codeSnippet = await api.getComponentCode(repoId, componentId).catch(() => "");
  if (!codeSnippet) codeSnippet = getCodeSnippet(componentId);

  let commits = await api.getComponentHistory(repoId, componentId).catch(() => []);
  if (!commits || commits.length === 0) commits = getCommitHistory(componentId);

  let allFindings = await api.getSecurityFindings(repoId).catch(() => null);
  const findings = (allFindings ?? getSecurityFindingsForRepo(repoId)).filter(
    (f) => f.componentId === componentId,
  );

  let allComponents = await api.getComponents(repoId).catch(() => []);
  const pool = allComponents.length > 0 ? allComponents : mockComponents;
  const dependents = component.downstreamDependents
    .map((path) => pool.find((c) => c.path === path && c.repositoryId === repoId))
    .filter((c): c is (typeof pool)[number] => Boolean(c));

  const metricRows: { label: string; value: string | number }[] = [
    { label: "Lines of code", value: component.metrics.loc },
    { label: "Cyclomatic complexity", value: component.metrics.cyclomaticComplexity },
    { label: "Avg. function length", value: component.metrics.functionLength },
    { label: "Class coupling", value: component.metrics.coupling },
    { label: "Dependency centrality", value: component.metrics.centrality.toFixed(2) },
    { label: "Change frequency (90d)", value: component.metrics.changeFrequency },
    { label: "Duplication", value: `${component.metrics.duplication}%` },
    {
      label: "Historical defect frequency",
      value: `${Math.round(component.metrics.historicalDefectFrequency * 100)}%`,
    },
  ];

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href="/repositories">Repositories</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={`/repositories/${repoId}`}>{repo.fullName}</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage className="font-mono">{component.path}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="font-mono text-xl font-semibold tracking-tight">{component.name}</h1>
            <RiskBadge level={component.riskLevel} />
            <Badge variant="secondary" className="text-xs">
              {component.language}
            </Badge>
          </div>
          <p className="mt-1 font-mono text-xs text-muted-foreground">{component.path}</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Last modified {formatRelativeDate(component.lastModified)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <CodeSheet code={codeSnippet} path={component.path} />
          <HistorySheet commits={commits} path={component.path} />
          <Button variant="outline" size="sm" asChild>
            <Link href={`/repositories/${repoId}/graph?focus=${component.id}`}>
              <Network className="size-4" />
              Graph context
            </Link>
          </Button>
        </div>
      </div>

      {/* Risk scores */}
      <RiskScorePanel
        defectRisk={component.defectRisk}
        securityRisk={component.securityRisk}
        regressionRisk={component.regressionRisk}
      />

      {/* Live ML Inference Interactive Inspector */}
      <LiveMLInspector
        initialCode={codeSnippet}
        componentPath={component.path}
        componentId={component.id}
        repositoryId={repoId}
        initialRisk={component}
      />

      {/* Metrics grid */}
      <Card className="gap-3 p-5">
        <CardHeader className="p-0">
          <CardTitle className="text-sm">Static &amp; historical metrics</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {metricRows.map((m) => (
              <div key={m.label} className="rounded-lg border border-border/60 bg-muted/20 p-3">
                <p className="text-[11px] text-muted-foreground">{m.label}</p>
                <p className="mt-1 font-mono text-sm font-semibold">{m.value}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Downstream dependents */}
      {dependents.length > 0 && (
        <Card className="gap-3 p-5">
          <CardHeader className="flex-row items-center justify-between p-0">
            <CardTitle className="text-sm">Impacted downstream components</CardTitle>
            <span className="text-xs text-muted-foreground">
              {dependents.length} direct dependents
            </span>
          </CardHeader>
          <CardContent className="flex flex-col divide-y divide-border p-0">
            {dependents.map((dep) => (
              <div
                key={dep.id}
                className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0"
              >
                <div className="min-w-0">
                  <Link
                    href={`/repositories/${repoId}/components/${dep.id}`}
                    className="truncate font-mono text-xs hover:text-primary hover:underline"
                  >
                    {dep.path}
                  </Link>
                </div>
                <div className="flex items-center gap-2">
                  <RiskBadge level={dep.riskLevel} />
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Evidence */}
      <EvidenceList evidence={component.evidence} />

      {/* Security findings for this component */}
      {findings.length > 0 && (
        <Card className="gap-3 p-5">
          <CardHeader className="flex-row items-center justify-between p-0">
            <div className="flex items-center gap-2">
              <ShieldAlert className="size-4 text-risk-critical" />
              <CardTitle className="text-sm">Security findings in this component</CardTitle>
            </div>
            <span className="text-xs text-muted-foreground">{findings.length} findings</span>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 p-0">
            {findings.map((f) => (
              <div
                key={f.id}
                className="rounded-lg border border-border/60 bg-muted/20 p-3 text-xs"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-medium text-foreground">{f.category}</span>
                  <div className="flex items-center gap-2">
                    <Badge variant="outline" className="text-[10px] uppercase">{f.source}</Badge>
                    <RiskBadge level={f.severity} />
                  </div>
                </div>
                <p className="mt-1 text-muted-foreground">{f.description}</p>
                <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                  {f.file}:{f.line} · {Math.round(f.confidence * 100)}% confidence
                </p>
                {f.evidence && (
                  <div className="mt-2 rounded border border-border/40 bg-background/50 p-2 text-foreground font-mono text-[11px]">
                    <span className="font-semibold text-primary">Evidence:</span>{" "}
                    {f.evidence}
                  </div>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Similar historical patterns */}
      <SimilarPatterns patterns={component.similarHistorical} />
    </div>
  );
}
