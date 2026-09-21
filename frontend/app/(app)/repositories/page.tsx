import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { HealthRing } from "@/components/shared/health-ring";
import { GithubMark } from "@/components/shared/github-mark";
import { repositories as fallbackRepositories, repositoryHealth } from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";
import { healthScoreLabel } from "@/lib/risk";
import { api } from "@/lib/api";

export default async function RepositoriesPage() {
  const liveRepos = await api.getRepositories().catch(() => fallbackRepositories);
  const repositories = liveRepos && liveRepos.length > 0 ? liveRepos : fallbackRepositories;
  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Repositories</h1>
          <p className="text-sm text-muted-foreground">
            {repositories.length} connected via the GitHub App.
          </p>
        </div>
        <Button asChild>
          <Link href="/onboarding">
            <Plus className="size-4" />
            Connect repository
          </Link>
        </Button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {repositories.map((repo) => {
          const health = repositoryHealth[repo.id];
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
                        {repo.description}
                      </p>
                    </div>
                  </div>
                  {isReady ? (
                    <HealthRing score={health.score} size={56} strokeWidth={5} />
                  ) : (
                    <Badge
                      variant="outline"
                      className="shrink-0 border-risk-medium/30 bg-risk-medium/10 text-risk-medium"
                    >
                      Analyzing
                    </Badge>
                  )}
                </div>

                <div className="flex flex-wrap items-center gap-1.5">
                  {repo.languages.map((lang) => (
                    <Badge key={lang} variant="secondary" className="text-[10px]">
                      {lang}
                    </Badge>
                  ))}
                </div>

                <div className="mt-auto flex items-center justify-between border-t border-border pt-3 text-xs text-muted-foreground">
                  <span>
                    {isReady
                      ? healthScoreLabel(health.score)
                      : "Ingestion in progress"}
                  </span>
                  <span className="flex items-center gap-1">
                    {repo.lastAnalyzedAt
                      ? `Analyzed ${formatRelativeDate(repo.lastAnalyzedAt)}`
                      : "Not yet analyzed"}
                    <ArrowRight className="size-3 transition-transform group-hover:translate-x-0.5" />
                  </span>
                </div>
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
