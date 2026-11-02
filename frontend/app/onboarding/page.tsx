"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Database,
  FileCode,
  Loader2,
  Lock,
  Search,
  ShieldCheck,
  Sparkles,
  Star,
  Zap,
  Activity,
  Layers,
  Bug,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { LogoMark } from "@/components/shared/logo-mark";
import { GithubMark } from "@/components/shared/github-mark";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { Repository } from "@/lib/types";

const EXAMPLE_REPOS = [
  { fullName: "pallets/flask", description: "A lightweight Python web framework", language: "Python", stars: "67k" },
  { fullName: "psf/requests", description: "HTTP for Humans — Python library", language: "Python", stars: "52k" },
  { fullName: "expressjs/express", description: "Fast web framework for Node.js", language: "JavaScript", stars: "64k" },
  { fullName: "vercel/next.js", description: "The React framework for the web", language: "TypeScript", stars: "126k" },
  { fullName: "fastapi/fastapi", description: "FastAPI framework, high performance", language: "Python", stars: "78k" },
  { fullName: "django/django", description: "The web framework for perfectionists", language: "Python", stars: "80k" },
];

function parseRepoSlug(input: string): string | null {
  let s = input.trim().replace(/\/+$/, "");
  if (!s) return null;
  if (s.endsWith(".git")) s = s.slice(0, -4);

  // Full URL: https://github.com/owner/repo or git@github.com:owner/repo
  const urlMatch = s.match(/github\.com[:/]([^/\s]+)\/([^/\s]+)/i);
  if (urlMatch) {
    return `${urlMatch[1]}/${urlMatch[2].replace(/\/.*$/, "")}`;
  }

  // owner/repo format
  const slugMatch = s.match(/^([^/\s]+)\/([^/\s]+)$/);
  if (slugMatch) {
    return `${slugMatch[1]}/${slugMatch[2]}`;
  }

  return null;
}

export default function OnboardingPage() {
  const router = useRouter();
  const [input, setInput] = React.useState("");
  const [loading, setLoading] = React.useState(false);
  const [connectedRepos, setConnectedRepos] = React.useState<Repository[]>([]);
  const [loadingRepos, setLoadingRepos] = React.useState(true);

  // Load already-connected repos
  React.useEffect(() => {
    api.getRepositories()
      .then(setConnectedRepos)
      .catch(() => setConnectedRepos([]))
      .finally(() => setLoadingRepos(false));
  }, []);

  const slug = parseRepoSlug(input);
  const isValid = !!slug;

  async function handleConnect(fullName: string) {
    if (loading) return;
    setLoading(true);

    try {
      toast.loading(`Connecting ${fullName}…`, { id: "connect" });
      const repo = await api.connectRepository({ fullName });
      toast.success(`Connected! Starting analysis of ${repo.fullName}`, { id: "connect" });
      router.push(`/repositories/${repo.id}/analyzing`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      toast.error("Failed to connect repository", {
        id: "connect",
        description: msg.includes("not found")
          ? `Repository "${fullName}" was not found. Check spelling and ensure it's public.`
          : msg.includes("422")
          ? "Invalid repository format. Use 'owner/repo' or a GitHub URL."
          : msg,
      });
      setLoading(false);
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (slug) handleConnect(slug);
  }

  return (
    <div className="min-h-svh bg-background text-foreground">
      {/* Top Bar */}
      <header className="border-b border-border/70 bg-background/80 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-5xl items-center justify-between px-4 md:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <LogoMark />
            <span className="font-mono text-base font-bold tracking-tight">SkyTrace</span>
            <Badge variant="outline" className="hidden sm:inline-flex text-[10px] border-primary/30 text-primary">
              Repository Intelligence
            </Badge>
          </Link>
          <div className="flex items-center gap-3">
            <ThemeToggle />
            <Button variant="outline" size="sm" asChild className="gap-1.5">
              <Link href="/">
                <ArrowLeft className="size-3.5" />
                <span>Back to Home</span>
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-10 md:px-6 md:py-14">
        {/* Title Header */}
        <div className="text-center max-w-2xl mx-auto mb-10">
          <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary font-mono text-xs mb-3">
            Repository Ingestion &amp; Onboarding
          </Badge>
          <h1 className="text-3xl font-extrabold tracking-tight sm:text-4xl">
            Analyze a GitHub Repository
          </h1>
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">
            Enter any public GitHub repository URL or <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">owner/repo</code> slug.
            SkyTrace fetches source files, parses AST syntax, and runs full ML risk analysis.
          </p>
        </div>

        {/* 3-Step Process Flow Visual Header */}
        <div className="mb-10 grid gap-4 sm:grid-cols-3">
          <Card className="p-4 border-primary/40 bg-primary/5 flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground font-mono text-sm font-bold">
              01
            </div>
            <div>
              <p className="text-xs font-bold text-foreground">Step 1 — Connect</p>
              <p className="text-[11px] text-muted-foreground">Provide GitHub URL or owner/repo slug</p>
            </div>
          </Card>

          <Card className="p-4 border-border/80 bg-card flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground font-mono text-sm font-bold">
              02
            </div>
            <div>
              <p className="text-xs font-bold text-foreground">Step 2 — Analyze</p>
              <p className="text-[11px] text-muted-foreground">SkyTrace parses AST, history &amp; ML features</p>
            </div>
          </Card>

          <Card className="p-4 border-border/80 bg-card flex items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground font-mono text-sm font-bold">
              03
            </div>
            <div>
              <p className="text-xs font-bold text-foreground">Step 3 — Investigate</p>
              <p className="text-[11px] text-muted-foreground">Inspect risks, graph, PR reviews &amp; evidence</p>
            </div>
          </Card>
        </div>

        {/* 3 Info Cards: What you provide / What SkyTrace analyzes / What you receive */}
        <div className="mb-10 grid gap-4 sm:grid-cols-3">
          <Card className="p-4 gap-2 border-border/70">
            <div className="flex items-center gap-2 text-primary">
              <GithubMark className="size-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">What You Provide</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Public GitHub repository URL, branch, or <code className="font-mono text-[11px]">owner/repository</code> format.
            </p>
          </Card>

          <Card className="p-4 gap-2 border-border/70">
            <div className="flex items-center gap-2 text-primary">
              <Zap className="size-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">What SkyTrace Analyzes</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Source code ASTs, git commit churn, import/call dependency graphs, and static security patterns.
            </p>
          </Card>

          <Card className="p-4 gap-2 border-border/70">
            <div className="flex items-center gap-2 text-primary">
              <Activity className="size-4" />
              <h3 className="text-xs font-bold uppercase tracking-wider">What You Receive</h3>
            </div>
            <p className="text-xs text-muted-foreground leading-relaxed">
              Overall health score (0-100), component defect risk levels, regression blast radius, and AI PR reviews.
            </p>
          </Card>
        </div>

        {/* Main URL Input Card */}
        <Card className="p-6 md:p-8 gap-6 border-primary/30 shadow-lg">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <label htmlFor="repo-url-input" className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Enter Repository Address
            </label>
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1">
                <GithubMark className="pointer-events-none absolute left-3.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  id="repo-url-input"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="https://github.com/owner/repo  or  owner/repo"
                  className="pl-10 font-mono text-sm h-11"
                  disabled={loading}
                  autoFocus
                  aria-label="GitHub repository URL or slug"
                />
              </div>
              <Button
                id="analyze-btn"
                type="submit"
                size="lg"
                className="h-11 px-6 font-semibold gap-2 shadow-md"
                disabled={!isValid || loading}
              >
                {loading ? (
                  <>
                    <Loader2 className="size-4 animate-spin" />
                    <span>Connecting…</span>
                  </>
                ) : (
                  <>
                    <Zap className="size-4" />
                    <span>Start Analysis</span>
                  </>
                )}
              </Button>
            </div>

            {input && !isValid && (
              <p className="text-xs text-destructive flex items-center gap-1 font-medium">
                <span>Not a valid GitHub URL or <code>owner/repo</code> format.</span>
              </p>
            )}
            {isValid && (
              <p className="text-xs text-muted-foreground flex items-center gap-1.5">
                <CheckCircle2 className="size-3.5 text-risk-low" />
                <span>Ready to analyze target: <strong className="font-mono text-foreground">{slug}</strong></span>
              </p>
            )}
          </form>

          {/* Quick Example Repositories */}
          <div className="border-t border-border/70 pt-6">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-bold text-muted-foreground uppercase tracking-wider">
                Or Select an Example Repository
              </p>
              <span className="text-[11px] text-muted-foreground">Instant single-click connection</span>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {EXAMPLE_REPOS.map((repo) => (
                <button
                  key={repo.fullName}
                  id={`example-${repo.fullName.replace("/", "-")}`}
                  onClick={() => handleConnect(repo.fullName)}
                  disabled={loading}
                  className={cn(
                    "flex flex-col justify-between rounded-lg border border-border/80 p-3.5 text-left transition-all",
                    "hover:border-primary/50 hover:bg-muted/40 hover:shadow-sm disabled:opacity-50 disabled:cursor-not-allowed group"
                  )}
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2 min-w-0">
                        <GithubMark className="size-4 shrink-0 text-muted-foreground group-hover:text-primary transition-colors" />
                        <span className="font-mono text-xs font-bold truncate group-hover:text-primary transition-colors">
                          {repo.fullName}
                        </span>
                      </div>
                      <ArrowRight className="size-3.5 shrink-0 text-muted-foreground group-hover:text-primary transition-transform group-hover:translate-x-0.5" />
                    </div>
                    <p className="text-[11px] text-muted-foreground truncate mt-1.5">{repo.description}</p>
                  </div>
                  <div className="flex items-center gap-2 mt-3 pt-2 border-t border-border/50">
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0 font-medium">{repo.language}</Badge>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-0.5 ml-auto">
                      <Star className="size-2.5" /> {repo.stars}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </Card>

        {/* Already Connected Repositories Section */}
        {!loadingRepos && connectedRepos.length > 0 && (
          <div className="mt-12">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-base font-bold text-foreground">Previously Connected Repositories</h2>
              <Badge variant="outline" className="text-xs">{connectedRepos.length} Repositories</Badge>
            </div>
            <ul className="grid gap-3 sm:grid-cols-2">
              {connectedRepos.map((repo) => {
                const isReady = repo.analysisStatus === "completed";
                const href = isReady
                  ? `/repositories/${repo.id}`
                  : `/repositories/${repo.id}/analyzing`;

                return (
                  <li key={repo.id}>
                    <Card className="p-4 flex flex-col justify-between gap-3 h-full hover:border-primary/40 transition-colors">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
                            <GithubMark className="size-4" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="truncate font-mono text-sm font-bold">
                                {repo.fullName}
                              </span>
                              {repo.private && (
                                <Badge variant="outline" className="gap-1 text-[10px]">
                                  <Lock className="size-2.5" />
                                  Private
                                </Badge>
                              )}
                            </div>
                            <p className="mt-0.5 truncate text-xs text-muted-foreground">
                              {repo.description || repo.fullName}
                            </p>
                          </div>
                        </div>
                        {isReady ? (
                          <Badge className="bg-risk-low/15 text-risk-low border-risk-low/30 text-[10px] shrink-0" variant="outline">
                            Analyzed
                          </Badge>
                        ) : (
                          <Badge className="bg-risk-medium/15 text-risk-medium border-risk-medium/30 text-[10px] shrink-0" variant="outline">
                            {repo.analysisStatus === "failed" ? "Failed" : "Analyzing"}
                          </Badge>
                        )}
                      </div>

                      <div className="pt-2 border-t border-border/60 flex items-center justify-between">
                        <span className="text-[11px] text-muted-foreground font-mono">
                          {repo.fileCount ? `${repo.fileCount} files indexed` : "Repository ready"}
                        </span>
                        <Button size="sm" variant={isReady ? "default" : "secondary"} asChild className="gap-1.5 text-xs">
                          <Link href={href}>
                            <span>{isReady ? "Open Dashboard" : "View Progress"}</span>
                            <ArrowRight className="size-3" />
                          </Link>
                        </Button>
                      </div>
                    </Card>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <div className="mt-12 text-center text-xs text-muted-foreground border-t border-border/70 pt-6">
          <p>
            Public repositories do not require GitHub authentication.{" "}
            <a
              href="https://github.com/settings/tokens"
              target="_blank"
              rel="noopener noreferrer"
              className="underline underline-offset-2 hover:text-foreground font-medium"
            >
              Add a Personal Access Token
            </a>{" "}
            if you wish to analyze private repositories.
          </p>
        </div>
      </main>
    </div>
  );
}
