import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ArrowLeft, ArrowRight, Bug, FileCode, Layers, ShieldAlert, Sparkles } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { RiskBadge } from "@/components/shared/risk-badge";
import { ComponentsTable } from "@/components/dashboard/components-table";
import { api } from "@/lib/api";

export default async function RepositoryComponentsPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  const repo = await api.getRepository(repoId).catch(() => null);
  if (!repo) notFound();

  if (repo.analysisStatus !== "completed") {
    redirect(`/repositories/${repoId}/analyzing`);
  }

  const components = await api.getComponents(repoId).catch(() => []);
  const sortedComponents = [...components].sort((a, b) => b.defectRisk - a.defectRisk);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      {/* Breadcrumb / Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" asChild className="-ml-2 gap-1 text-xs">
              <Link href={`/repositories/${repoId}`}>
                <ArrowLeft className="size-3.5" />
                <span>Overview</span>
              </Link>
            </Button>
            <span className="text-muted-foreground">/</span>
            <span className="text-xs font-semibold text-foreground">Components</span>
          </div>
          <h1 className="mt-1 font-mono text-2xl font-bold tracking-tight">
            Component Risk Intelligence &amp; Inspection
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            {sortedComponents.length} components analyzed across <span className="font-mono font-medium text-foreground">{repo.fullName}</span>. Ranked by ML defect risk probability.
          </p>
        </div>
        <Button variant="outline" size="sm" asChild className="gap-1.5">
          <Link href={`/repositories/${repoId}/graph`}>
            <Layers className="size-4" />
            <span>Dependency Graph</span>
          </Link>
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-4 flex items-center gap-4">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-risk-critical/10 text-risk-critical">
            <Bug className="size-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">High/Critical Defect Risk</p>
            <p className="font-mono text-xl font-bold">
              {sortedComponents.filter((c) => c.riskLevel === "CRITICAL" || c.riskLevel === "HIGH").length}
            </p>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-4">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            <FileCode className="size-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Total Indexed Files</p>
            <p className="font-mono text-xl font-bold">{repo.fileCount}</p>
          </div>
        </Card>

        <Card className="p-4 flex items-center gap-4">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-risk-medium/10 text-risk-medium">
            <Sparkles className="size-5" />
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Explainable Evidence</p>
            <p className="font-mono text-xl font-bold">
              {sortedComponents.reduce((acc, c) => acc + (c.evidence?.length || 0), 0)} Triggers
            </p>
          </div>
        </Card>
      </div>

      {/* Components Table Card */}
      <Card className="gap-4 p-6">
        <CardHeader className="p-0 flex-row items-center justify-between pb-2 border-b border-border/70">
          <div>
            <CardTitle className="text-base font-bold">All Repository Components</CardTitle>
            <p className="text-xs text-muted-foreground">
              Select any component to inspect line-level code, ML defect triggers, and Git history logs.
            </p>
          </div>
          <Badge variant="outline" className="font-mono text-xs">
            {sortedComponents.length} Components
          </Badge>
        </CardHeader>
        <CardContent className="p-0 pt-4">
          <ComponentsTable repositoryId={repoId} components={sortedComponents} />
        </CardContent>
      </Card>
    </div>
  );
}
