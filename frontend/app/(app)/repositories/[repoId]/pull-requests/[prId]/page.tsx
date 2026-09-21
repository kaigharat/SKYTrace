import Link from "next/link";
import { notFound } from "next/navigation";
import { ExternalLink, GitMerge, GitPullRequest, Sparkles } from "lucide-react";
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
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { RiskBadge } from "@/components/shared/risk-badge";
import { ChangedFilesList } from "@/components/pr-review/changed-files-list";
import { AffectedList } from "@/components/pr-review/affected-list";
import { TestRecommendations } from "@/components/pr-review/test-recommendations";
import { getPullRequest, getRepository } from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";
import { api } from "@/lib/api";

export default async function PullRequestReviewPage({
  params,
}: {
  params: Promise<{ repoId: string; prId: string }>;
}) {
  const { repoId, prId } = await params;
  let repo = await api.getRepository(repoId).catch(() => getRepository(repoId));
  if (!repo) repo = getRepository(repoId);

  let pr = await api.getPullRequest(prId).catch(() => getPullRequest(prId));
  if (!pr) pr = getPullRequest(prId);

  if (!repo || !pr || pr.repositoryId !== repoId) notFound();

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={`/repositories/${repoId}`}>{repo.fullName}</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={`/repositories/${repoId}/pull-requests`}>Pull requests</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>#{pr.number}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Avatar className="size-10 shrink-0">
            <AvatarFallback className="bg-primary/15 text-sm font-medium text-primary">
              {pr.authorAvatar}
            </AvatarFallback>
          </Avatar>
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-semibold tracking-tight">
                #{pr.number} {pr.title}
              </h1>
              <Badge variant="outline" className="gap-1 text-[10px] capitalize">
                {pr.status === "merged" ? (
                  <GitMerge className="size-2.5" />
                ) : (
                  <GitPullRequest className="size-2.5" />
                )}
                {pr.status}
              </Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              {pr.author} opened {formatRelativeDate(pr.createdAt)} · {pr.branch} → {pr.baseBranch}
            </p>
          </div>
        </div>
        <Badge asChild variant="outline" className="border-primary/30 bg-primary/10 text-primary">
          <a
            href={`https://github.com/${repo.fullName}/pull/${pr.number}`}
            target="_blank"
            rel="noopener noreferrer"
            className="gap-1"
          >
            View on GitHub
            <ExternalLink className="size-3" />
          </a>
        </Badge>
      </div>

      {/* Risk summary */}
      <Card className="gap-4 p-5">
        <CardHeader className="p-0">
          <CardTitle className="text-sm">Risk summary</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-4 p-0 sm:grid-cols-3">
          <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 p-3 sm:flex-col sm:items-start sm:gap-2">
            <span className="text-xs text-muted-foreground">Bug risk</span>
            <RiskBadge level={pr.bugRisk} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 p-3 sm:flex-col sm:items-start sm:gap-2">
            <span className="text-xs text-muted-foreground">Security risk</span>
            <RiskBadge level={pr.securityRisk} />
          </div>
          <div className="flex items-center justify-between rounded-lg border border-border bg-muted/20 p-3 sm:flex-col sm:items-start sm:gap-2">
            <span className="text-xs text-muted-foreground">Regression risk</span>
            <RiskBadge level={pr.regressionRisk} />
          </div>
        </CardContent>
      </Card>

      {/* AI summary */}
      <Card className="gap-3 border-primary/20 bg-primary/[0.03] p-5">
        <CardHeader className="flex-row items-center gap-2 p-0">
          <Sparkles className="size-4 text-primary" />
          <CardTitle className="text-sm">AI review summary</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <p className="text-sm text-pretty text-foreground/90">{pr.aiSummary}</p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card className="gap-3 p-5">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">Changed · {pr.changedFiles.length}</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <ChangedFilesList files={pr.changedFiles} />
          </CardContent>
        </Card>

        <Card className="gap-3 p-5">
          <CardHeader className="p-0">
            <CardTitle className="text-sm">
              Potentially affected · {pr.potentiallyAffected.length}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <AffectedList items={pr.potentiallyAffected} />
          </CardContent>
        </Card>
      </div>

      <Card className="gap-3 p-5">
        <CardHeader className="p-0">
          <CardTitle className="text-sm">
            Recommended tests · {pr.recommendedTests.length}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <TestRecommendations tests={pr.recommendedTests} />
        </CardContent>
      </Card>
    </div>
  );
}
