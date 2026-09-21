"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  Check,
  Loader2,
  Lock,
  Search,
  Star,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { LogoMark } from "@/components/shared/logo-mark";
import { GithubMark } from "@/components/shared/github-mark";
import { repositories as connectedRepositories } from "@/lib/mock-data";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AvailableRepo {
  id: string;
  fullName: string;
  description: string;
  language: string;
  private: boolean;
  stars: number;
  connected: boolean;
}

const availableRepos: AvailableRepo[] = [
  ...connectedRepositories.map((r) => ({
    id: r.id,
    fullName: r.fullName,
    description: r.description,
    language: r.languages[0],
    private: r.private,
    stars: r.stars,
    connected: true,
  })),
  {
    id: "repo-notification-service",
    fullName: "acme-labs/notification-service",
    description: "Email, SMS and push notification dispatch service.",
    language: "TypeScript",
    private: true,
    stars: 19,
    connected: false,
  },
  {
    id: "repo-internal-tools",
    fullName: "acme-labs/internal-tools",
    description: "Internal admin tooling and scripts.",
    language: "Python",
    private: true,
    stars: 6,
    connected: false,
  },
];

const steps = ["Connect GitHub", "Select repository", "Start analysis"];

export default function OnboardingPage() {
  const router = useRouter();
  const [connecting, setConnecting] = React.useState(false);
  const [connected, setConnected] = React.useState(false);
  const [query, setQuery] = React.useState("");
  const [startingId, setStartingId] = React.useState<string | null>(null);

  const currentStep = connected ? 1 : 0;

  function handleConnect() {
    setConnecting(true);
    window.setTimeout(() => {
      setConnecting(false);
      setConnected(true);
      toast.success("GitHub App authorized", {
        description: "acme-labs granted access to 5 repositories.",
      });
    }, 1100);
  }

  async function handleSelect(repo: AvailableRepo) {
    // Notify backend
    api.connectRepository({ fullName: repo.fullName, description: repo.description }).catch(() => null);
    api.analyzeRepository(repo.id).catch(() => null);

    const existing = connectedRepositories.find((r) => r.id === repo.id);
    if (existing?.analysisStatus === "completed") {
      router.push(`/repositories/${repo.id}`);
      return;
    }
    setStartingId(repo.id);
    toast("Analysis queued", {
      description: `${repo.fullName} · cloning, parsing and building the repository graph.`,
    });
    window.setTimeout(() => {
      router.push(`/repositories/${repo.id}/analyzing`);
    }, 500);
  }

  const filtered = availableRepos.filter((r) =>
    r.fullName.toLowerCase().includes(query.toLowerCase()),
  );

  return (
    <div className="mx-auto flex min-h-svh max-w-3xl flex-col px-4 py-10 md:px-0">
      <div className="mb-8 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <LogoMark />
          <span className="font-mono text-sm font-semibold">Repository Intelligence AI</span>
        </Link>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </Button>
      </div>

      <ol className="mb-10 flex items-center gap-2" aria-label="Onboarding progress">
        {steps.map((label, i) => (
          <li key={label} className="flex flex-1 items-center gap-2">
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "flex size-6 shrink-0 items-center justify-center rounded-full text-xs font-medium",
                  i < currentStep && "bg-risk-low text-risk-low-foreground",
                  i === currentStep && "bg-primary text-primary-foreground",
                  i > currentStep && "bg-muted text-muted-foreground",
                )}
              >
                {i < currentStep ? <Check className="size-3.5" /> : i + 1}
              </span>
              <span
                className={cn(
                  "hidden text-sm sm:inline",
                  i === currentStep ? "font-medium text-foreground" : "text-muted-foreground",
                )}
              >
                {label}
              </span>
            </div>
            {i < steps.length - 1 && (
              <div className={cn("h-px flex-1", i < currentStep ? "bg-risk-low" : "bg-border")} />
            )}
          </li>
        ))}
      </ol>

      {!connected ? (
        <Card className="items-center gap-4 p-10 text-center">
          <div className="flex size-14 items-center justify-center rounded-full bg-foreground text-background">
            <GithubMark className="size-7" />
          </div>
          <h1 className="text-xl font-semibold">Install &amp; authorize the GitHub App</h1>
          <p className="max-w-md text-sm text-muted-foreground">
            Repository Intelligence AI needs read access to clone your repository, plus webhook
            access to analyze pull requests. You choose exactly which repositories to grant
            access to on GitHub.
          </p>
          <Button size="lg" onClick={handleConnect} disabled={connecting} className="mt-2">
            {connecting ? (
              <>
                <Loader2 className="size-4 animate-spin" />
                Connecting to GitHub…
              </>
            ) : (
              <>
                <GithubMark className="size-4" />
                Continue with GitHub
              </>
            )}
          </Button>
          <p className="text-xs text-muted-foreground">
            You can revoke access at any time from GitHub App settings.
          </p>
        </Card>
      ) : (
        <div className="flex flex-col gap-4">
          <div>
            <h1 className="text-xl font-semibold">Select a repository</h1>
            <p className="text-sm text-muted-foreground">
              Choose a repository to analyze. Already-analyzed repositories open straight to
              their dashboard.
            </p>
          </div>

          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search repositories…"
              className="pl-9"
              aria-label="Search repositories"
            />
          </div>

          <ul className="flex flex-col gap-2">
            {filtered.map((repo) => {
              const existing = connectedRepositories.find((r) => r.id === repo.id);
              const isAnalyzed = existing?.analysisStatus === "completed";
              const isRunning =
                existing && existing.analysisStatus !== "completed" && existing.analysisStatus !== "not_started";
              const isBusy = startingId === repo.id;
              return (
                <li key={repo.id}>
                  <Card className="flex-row items-center justify-between gap-4 p-4">
                    <div className="flex min-w-0 flex-1 items-start gap-3">
                      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                        <GithubMark className="size-4" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="truncate font-mono text-sm font-medium">
                            {repo.fullName}
                          </span>
                          {repo.private && (
                            <Badge variant="outline" className="gap-1 text-[10px]">
                              <Lock className="size-2.5" />
                              Private
                            </Badge>
                          )}
                          {isAnalyzed && (
                            <Badge className="bg-risk-low/15 text-risk-low border-risk-low/30 text-[10px]" variant="outline">
                              Analyzed
                            </Badge>
                          )}
                          {isRunning && (
                            <Badge className="bg-risk-medium/15 text-risk-medium border-risk-medium/30 text-[10px]" variant="outline">
                              Analyzing
                            </Badge>
                          )}
                        </div>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {repo.description}
                        </p>
                        <div className="mt-1.5 flex items-center gap-3 text-[11px] text-muted-foreground">
                          <span>{repo.language}</span>
                          <span className="flex items-center gap-1">
                            <Star className="size-3" />
                            {repo.stars}
                          </span>
                        </div>
                      </div>
                    </div>
                    <Button
                      size="sm"
                      variant={isAnalyzed ? "outline" : "default"}
                      onClick={() => handleSelect(repo)}
                      disabled={isBusy}
                      className="shrink-0"
                    >
                      {isBusy ? (
                        <Loader2 className="size-3.5 animate-spin" />
                      ) : isAnalyzed ? (
                        "View dashboard"
                      ) : isRunning ? (
                        "View progress"
                      ) : (
                        "Start analysis"
                      )}
                    </Button>
                  </Card>
                </li>
              );
            })}
            {filtered.length === 0 && (
              <p className="rounded-lg border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
                No repositories match &ldquo;{query}&rdquo;.
              </p>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
