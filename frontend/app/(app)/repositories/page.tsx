import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HealthRing } from "@/components/shared/health-ring";
import { GithubMark } from "@/components/shared/github-mark";
import { formatRelativeDate } from "@/lib/format";
import { healthScoreLabel } from "@/lib/risk";
import { api } from "@/lib/api";
import type { RepositoryHealth } from "@/lib/types";

export default async function RepositoriesPage() {
  const repositories = await api.getRepositories().catch(() => []);

  // Fetch health metrics for completed repositories in parallel
  const healthMap: Record<string, RepositoryHealth> = {};
  await Promise.all(
    repositories.map(async (repo) => {
      if (repo.analysisStatus === "completed") {
        const h = await api.getRepositoryHealth(repo.id).catch(() => null);
        if (h) healthMap[repo.id] = h;
      }
    })
  );

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Repositories</h1>
          <p className="text-sm text-muted-foreground">
            {repositories.length === 0
              ? "No connected repositories"
              : `${repositories.length} connected via GitHub.`}
          </p>
        </div>
        <Button asChild>
          <Link href="/onboarding">
            <Plus className="size-4" />
            Connect repository
          </Link>
        </Button>
      </div>

      {repositories.length === 0 ? (
        <Card className="flex flex-col items-center justify-center gap-4 p-12 text-center border-dashed">
          <div className="flex size-14 items-center justify-center rounded-full bg-primary/10 text-primary">
            <GithubMark className="size-7" />
          </div>
          <div className="max-w-md">
            <h2 className="text-lg font-semibold">No repositories analyzed yet</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Connect any public GitHub repository to run AST parsing, ML defect prediction, security risk analysis, and dependency graphs.
            </p>
          </div>
          <Button asChild className="gap-2">
            <Link href="/onboarding">
              <Plus className="size-4" />
              Connect your first repository
            </Link>
          </Button>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {repositories.map((repo) => {
            const health = healthMap[repo.id];
            const isReady = repo.analysisStatus === "completed" && health;
            const href = isReady
              ? `/repositories/${repo.id}`
              : `/repositories/${repo.id}/analyzing`;

            return (
              <Link key={repo.id} href={href} className="group">
                <Card className="h-full gap-4 p-5 transition-colors hover:border-primary/40">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex min-w-0 items-start gap-2">
                      <GithubMark className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                      <div className="min-w-0">
                        <p className="truncate font-mono text-sm font-medium">{repo.fullName}</p>
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {repo.description || "No description provided"}
                        </p>
                      </div>
                    </div>
                    {isReady ? (
                      <HealthRing score={health.score} size={56} strokeWidth={5} />
                    ) : (
                      <Badge
                        variant="outline"
                        className="shrink-0 border-risk-medium/30 bg-risk-medium/10 text-risk-medium text-[11px] capitalize"
                      >
                        {repo.analysisStatus.replace("_", " ")}
                      </Badge>
                    )}
                  </div>

                  <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-border pt-3 text-xs text-muted-foreground">
                    <div className="flex items-center gap-1.5">
                      {repo.languages.slice(0, 2).map((l) => (
                        <span key={l} className="rounded bg-muted px-1.5 py-0.5 text-[10px]">
                          {l}
                        </span>
                      ))}
                      <span>·</span>
                      <span>{repo.fileCount} files</span>
                    </div>
                    <span className="flex items-center gap-1 group-hover:text-primary">
                      {isReady ? healthScoreLabel(health.score) : "Analyzing"}
                      <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
                    </span>
                  </div>
                </Card>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
