"use client";

import * as React from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  ArrowLeft,
  ArrowRight,
  Loader2,
  Lock,
  Search,
  Star,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { LogoMark } from "@/components/shared/logo-mark";
import { GithubMark } from "@/components/shared/github-mark";
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
  const s = input.trim();
  if (!s) return null;

  // Full URL: https://github.com/owner/repo[.git][/...]
  const urlMatch = s.match(/github\.com[:/]([^/\s]+\/[^/\s\.]+?)(?:\.git)?(?:\/.*)?$/i);
  if (urlMatch) return urlMatch[1];

  // owner/repo format
  if (/^[^/\s]+\/[^/\s]+$/.test(s)) return s;

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
    <div className="mx-auto flex min-h-svh max-w-3xl flex-col px-4 py-10 md:px-0">
      {/* Header */}
      <div className="mb-8 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2">
          <LogoMark />
          <span className="font-mono text-sm font-semibold">SkyTrace</span>
        </Link>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/">
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </Button>
      </div>

      {/* Title */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">Analyze a GitHub repository</h1>
        <p className="mt-2 text-muted-foreground">
          Paste any public GitHub repository URL or <code className="text-xs bg-muted px-1.5 py-0.5 rounded">owner/repo</code> slug.
          SkyTrace will fetch the real source code and run full ML-powered risk analysis.
        </p>
      </div>

      {/* URL Input */}
      <Card className="p-6 gap-4">
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <GithubMark className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="repo-url-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="https://github.com/owner/repo  or  owner/repo"
                className="pl-9 font-mono text-sm"
                disabled={loading}
                autoFocus
                aria-label="GitHub repository URL or slug"
              />
            </div>
            <Button
              id="analyze-btn"
              type="submit"
              disabled={!isValid || loading}
            >
              {loading ? (
                <>
                  <Loader2 className="size-4 animate-spin" />
                  Connecting…
                </>
              ) : (
                <>
                  <Zap className="size-4" />
                  Analyze
                </>
              )}
            </Button>
          </div>

          {input && !isValid && (
            <p className="text-xs text-destructive">
              Not a valid GitHub URL or <code>owner/repo</code> format.
            </p>
          )}
          {isValid && (
            <p className="text-xs text-muted-foreground">
              Will analyze: <span className="font-mono text-foreground">{slug}</span>
            </p>
          )}
        </form>

        <div className="border-t pt-4">
          <p className="mb-3 text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Try an example
          </p>
          <div className="grid gap-2 sm:grid-cols-2">
            {EXAMPLE_REPOS.map((repo) => (
              <button
                key={repo.fullName}
                id={`example-${repo.fullName.replace("/", "-")}`}
                onClick={() => handleConnect(repo.fullName)}
                disabled={loading}
                className={cn(
                  "flex items-start gap-3 rounded-lg border border-border p-3 text-left transition-colors",
                  "hover:border-primary/40 hover:bg-muted/30 disabled:opacity-50 disabled:cursor-not-allowed"
                )}
              >
                <GithubMark className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="font-mono text-xs font-medium truncate">{repo.fullName}</p>
                  <p className="text-[11px] text-muted-foreground truncate mt-0.5">{repo.description}</p>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge variant="secondary" className="text-[10px] px-1.5 py-0">{repo.language}</Badge>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-0.5">
                      <Star className="size-2.5" /> {repo.stars}
                    </span>
                  </div>
                </div>
                <ArrowRight className="mt-0.5 size-3.5 shrink-0 text-muted-foreground" />
              </button>
            ))}
          </div>
        </div>
      </Card>

      {/* Already connected repos */}
      {!loadingRepos && connectedRepos.length > 0 && (
        <div className="mt-8">
          <h2 className="text-sm font-semibold mb-3">Already connected</h2>
          <ul className="flex flex-col gap-2">
            {connectedRepos.map((repo) => {
              const isReady = repo.analysisStatus === "completed";
              const href = isReady
                ? `/repositories/${repo.id}`
                : `/repositories/${repo.id}/analyzing`;

              return (
                <li key={repo.id}>
                  <Card className="flex-row items-center justify-between gap-4 p-4">
                    <div className="flex min-w-0 flex-1 items-center gap-3">
                      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
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
                          {isReady && (
                            <Badge className="bg-risk-low/15 text-risk-low border-risk-low/30 text-[10px]" variant="outline">
                              Analyzed
                            </Badge>
                          )}
                          {!isReady && (
                            <Badge className="bg-risk-medium/15 text-risk-medium border-risk-medium/30 text-[10px]" variant="outline">
                              {repo.analysisStatus === "failed" ? "Failed" : "Analyzing"}
                            </Badge>
                          )}
                        </div>
                        <p className="mt-0.5 truncate text-xs text-muted-foreground">
                          {repo.description || repo.fullName}
                        </p>
                      </div>
                    </div>
                    <Button size="sm" variant={isReady ? "outline" : "secondary"} asChild>
                      <Link href={href}>
                        {isReady ? "View dashboard" : "View progress"}
                        <ArrowRight className="size-3" />
                      </Link>
                    </Button>
                  </Card>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      <p className="mt-8 text-center text-xs text-muted-foreground">
        Only public repositories are supported without a GitHub token.{" "}
        <a
          href="https://github.com/settings/tokens"
          target="_blank"
          rel="noopener noreferrer"
          className="underline underline-offset-2 hover:text-foreground"
        >
          Add a token
        </a>{" "}
        to analyze private repos.
      </p>
    </div>
  );
}
