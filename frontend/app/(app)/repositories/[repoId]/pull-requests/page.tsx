import Link from "next/link";
import { notFound } from "next/navigation";
import { GitMerge, GitPullRequest } from "lucide-react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { RiskBadge } from "@/components/shared/risk-badge";
import { getPullRequestsForRepo, getRepository } from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";
import { api } from "@/lib/api";

export default async function PullRequestsPage({
  params,
}: {
  params: Promise<{ repoId: string }>;
}) {
  const { repoId } = await params;
  let repo = await api.getRepository(repoId).catch(() => getRepository(repoId));
  if (!repo) repo = getRepository(repoId);
  if (!repo) notFound();

  let prs = await api.getPullRequests(repoId).catch(() => getPullRequestsForRepo(repoId));
  const pullRequests = prs && prs.length > 0 ? prs : getPullRequestsForRepo(repoId);

  return (
    <div className="mx-auto flex max-w-4xl flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Pull requests</h1>
        <p className="text-sm text-muted-foreground">
          {repo.fullName} · AI-reviewed against repository risk context
        </p>
      </div>

      {pullRequests.length === 0 ? (
        <Card className="items-center gap-2 p-10 text-center">
          <GitPullRequest className="size-6 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">No pull requests analyzed yet.</p>
        </Card>
      ) : (
        <ul className="flex flex-col gap-3">
          {pullRequests.map((pr) => (
            <li key={pr.id}>
              <Link href={`/repositories/${repoId}/pull-requests/${pr.id}`}>
                <Card className="flex-row items-center gap-4 p-4 transition-colors hover:border-primary/40">
                  <Avatar className="size-9 shrink-0">
                    <AvatarFallback className="bg-primary/15 text-xs font-medium text-primary">
                      {pr.authorAvatar}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-sm font-medium">
                        #{pr.number} {pr.title}
                      </span>
                      <Badge
                        variant="outline"
                        className="gap-1 text-[10px] capitalize"
                      >
                        {pr.status === "merged" ? (
                          <GitMerge className="size-2.5" />
                        ) : (
                          <GitPullRequest className="size-2.5" />
                        )}
                        {pr.status}
                      </Badge>
                    </div>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {pr.author} opened {formatRelativeDate(pr.createdAt)} ·{" "}
                      {pr.branch} → {pr.baseBranch} · {pr.changedFiles.length} files changed
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1.5">
                    <div className="flex gap-1.5">
                      <RiskBadge level={pr.bugRisk} showDot={false} />
                    </div>
                    <span className="text-[11px] text-muted-foreground">Bug risk</span>
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
