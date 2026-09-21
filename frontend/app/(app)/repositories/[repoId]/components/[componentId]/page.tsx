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
  components,
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
  let repo = await api.getRepository(repoId).catch(() => getRepository(repoId));
  if (!repo) repo = getRepository(repoId);

  let component = await api.getComponent(repoId, componentId).catch(() => getComponent(componentId));
  if (!component) component = getComponent(componentId);
  if (!repo || !component || component.repositoryId !== repoId) notFound();

  let codeSnippet = await api.getComponentCode(repoId, componentId).catch(() => getCodeSnippet(componentId));
  if (!codeSnippet) codeSnippet = getCodeSnippet(componentId);

  let commits = await api.getComponentHistory(repoId, componentId).catch(() => getCommitHistory(componentId));
  if (!commits || commits.length === 0) commits = getCommitHistory(componentId);

  let allFindings = await api.getSecurityFindings(repoId).catch(() => getSecurityFindingsForRepo(repoId));
  const findings = (allFindings || getSecurityFindingsForRepo(repoId)).filter(
    (f) => f.componentId === componentId,
  );
  const dependents = component.downstreamDependents
    .map((path) => components.find((c) => c.path === path && c.repositoryId === repoId))
    .filter((c): c is (typeof components)[number] => Boolean(c));

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
            <h1 className="font-mono text-xl font-semibold tracking-tight">{component.path}</h1>
            <RiskBadge level={component.riskLevel} />
          </div>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="secondary" className="text-[10px]">{component.language}</Badge>
            <Badge variant="outline" className="text-[10px] capitalize">{component.type}</Badge>
            <span>Modified {formatRelativeDate(component.lastModified)} by {component.lastModifiedBy}</span>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <CodeSheet path={component.path} code={codeSnippet} />
          <HistorySheet path={component.path} commits={commits} />
          <Button variant="outline" size="sm" asChild>
            <Link href={`/repositories/${repoId}/graph?focus=${component.id}`}>
              <Network className="size-3.5" />
              View graph
            </Link>
          </Button>
          <Button variant="outline" size="sm" asChild>
            <a href="#similar-historical">
              <Sparkles className="size-3.5" />
              View similar bugs
            </a>
          </Button>
        </div>
      </div>

      <Card className="gap-4 p-5">
        <CardHeader className="p-0">
          <CardTitle className="text-sm">Risk scores</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <RiskScorePanel
            defectRisk={component.defectRisk}
            securityRisk={component.securityRisk}
            regressionRisk={component.regressionRisk}
          />
        </CardContent>
      </Card>

      {/* Real-time ML Predictor & Inspector */}
      <LiveMLInspector
        initialCode={codeSnippet}
        componentPath={component.path}
        componentId={component.id}
        repositoryId={repoId}
        initialRisk={component}
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="gap-4 p-5 lg:col-span-2">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">Why is this component risky?</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <EvidenceList evidence={component.evidence} />
          </CardContent>
        </Card>

        <Card className="gap-4 p-5">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">Code quality metrics</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <dl className="flex flex-col gap-2.5">
              {metricRows.map((m) => (
                <div key={m.label} className="flex items-center justify-between text-xs">
                  <dt className="text-muted-foreground">{m.label}</dt>
                  <dd className="font-mono font-medium tabular-nums">{m.value}</dd>
                </div>
              ))}
            </dl>
          </CardContent>
        </Card>
      </div>

      {dependents.length > 0 && (
        <Card className="gap-3 p-5">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">
              Downstream dependents · {dependents.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col divide-y divide-border p-0">
            {dependents.map((d) => (
              <Link
                key={d.id}
                href={`/repositories/${repoId}/components/${d.id}`}
                className="flex items-center justify-between gap-3 py-2.5 first:pt-0 last:pb-0 hover:text-primary"
              >
                <span className="font-mono text-xs">{d.path}</span>
                <RiskBadge level={d.riskLevel} />
              </Link>
            ))}
          </CardContent>
        </Card>
      )}

      {findings.length > 0 && (
        <Card className="gap-3 p-5">
          <CardHeader className="flex-row items-center gap-2 p-0">
            <ShieldAlert className="size-4 text-muted-foreground" />
            <CardTitle className="text-sm">Security findings</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col divide-y divide-border p-0">
            {findings.map((f) => (
              <div key={f.id} className="py-3 first:pt-0 last:pb-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{f.category}</span>
                  <RiskBadge level={f.severity} />
                  <Badge variant="outline" className="text-[10px] uppercase">{f.source}</Badge>
                </div>
                <p className="mt-1 text-xs text-muted-foreground">{f.description}</p>
                <p className="mt-1 font-mono text-[11px] text-muted-foreground">
                  {f.file}:{f.line} · {Math.round(f.confidence * 100)}% confidence
                </p>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      <Card id="similar-historical" className="scroll-mt-20 gap-3 p-5">
        <CardHeader className="p-0">
          <CardTitle className="text-sm">Similar historical patterns</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <SimilarPatterns patterns={component.similarHistorical} />
        </CardContent>
      </Card>
    </div>
  );
}
