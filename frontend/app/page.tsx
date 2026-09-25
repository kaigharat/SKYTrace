import Link from "next/link";
import {
  ArrowRight,
  Bug,
  FlaskConical,
  GitPullRequest,
  History,
  Network,
  ShieldAlert,
  Sparkles,
  GitBranch,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { HealthRing } from "@/components/shared/health-ring";
import { LogoMark } from "@/components/shared/logo-mark";
import { RiskBadge } from "@/components/shared/risk-badge";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { repositories as defaultRepos, repositoryHealth as defaultHealth } from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";
import { api } from "@/lib/api";

const onboardingSteps = [
  { title: "Connect GitHub", detail: "Sign in and authorize the Repository Intelligence GitHub App." },
  { title: "Select a repository", detail: "Choose from repositories the GitHub App has access to." },
  { title: "Start analysis", detail: "Ingestion, parsing, graph and history pipelines run automatically." },
  { title: "Track progress", detail: "Watch each analysis stage complete in real time." },
  { title: "Open the dashboard", detail: "Review health, risk, graph and explainable findings." },
];

const features = [
  { icon: Bug, title: "Bug intelligence", detail: "Component-level defect-risk probabilities with LOW/MEDIUM/HIGH/CRITICAL classification." },
  { icon: ShieldAlert, title: "Security intelligence", detail: "Static analysis plus ML risk scoring, normalized with severity, location and evidence." },
  { icon: GitBranch, title: "Regression intelligence", detail: "Trace which components could break when a file or function changes." },
  { icon: History, title: "Historical intelligence", detail: "FAISS-backed retrieval of similar historical defects and vulnerable patterns." },
  { icon: FlaskConical, title: "Smart testing", detail: "Test recommendations ranked by change impact and identified risk." },
  { icon: GitPullRequest, title: "AI code review", detail: "Pull-request analysis using repository context, risk and impact together." },
  { icon: Sparkles, title: "Explainable AI", detail: "Every high-risk finding ships with the evidence behind the classification." },
  { icon: Network, title: "Repository graph", detail: "Interactive dependency, call and impact visualizations across the codebase." },
];

export default async function Home() {
  const repos = await api.getRepositories().catch(() => []);
  const completedRepo = repos.find((r) => r.analysisStatus === "completed");
  const demoRepo = completedRepo || repos[0] || defaultRepos[0];

  let demoHealth = completedRepo
    ? await api.getRepositoryHealth(completedRepo.id).catch(() => null)
    : await api.getRepositoryHealth(demoRepo.id).catch(() => defaultHealth[demoRepo.id]);
  if (!demoHealth) demoHealth = defaultHealth[demoRepo.id] || defaultHealth["repo-orbit-payments"];

  return (
    <div className="flex min-h-svh flex-col">
      <header className="sticky top-0 z-20 border-b border-border/70 bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 md:px-8">
          <div className="flex items-center gap-2">
            <LogoMark />
            <span className="font-mono text-sm font-semibold tracking-tight">
              Repository Intelligence AI
            </span>
          </div>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" asChild className="hidden sm:inline-flex">
              <Link href={`/repositories/${demoRepo.id}`}>View demo dashboard</Link>
            </Button>
            <Button asChild>
              <Link href="/onboarding">
                Connect repository
                <ArrowRight className="size-4" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Hero */}
        <section className="mx-auto grid max-w-6xl gap-10 px-4 py-16 md:grid-cols-[1.1fr_0.9fr] md:px-8 md:py-24">
          <div className="flex flex-col justify-center gap-6">
            <Badge variant="outline" className="w-fit border-primary/30 bg-primary/10 text-primary">
              BTech Final-Year Project · GitHub App
            </Badge>
            <h1 className="text-4xl font-semibold tracking-tight text-balance md:text-5xl">
              Understand your repository as a connected system, not a pile of files.
            </h1>
            <p className="max-w-xl text-lg text-muted-foreground text-pretty">
              Repository Intelligence AI combines source-code semantics, dependency structure
              and Git history into one representation, then uses it to surface defect risk,
              security risk, regression impact and explainable findings — plus AI-reviewed pull
              requests and prioritized test recommendations.
            </p>
            <div className="flex flex-wrap items-center gap-3">
              <Button size="lg" asChild>
                <Link href="/onboarding">
                  Connect a GitHub repository
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild>
                <Link href={`/repositories/${demoRepo.id}`}>Explore the live demo</Link>
              </Button>
            </div>
            <p className="text-xs text-muted-foreground">
              Team: Yashodhan (Product, Frontend &amp; GitHub Intelligence) · Swarali (AI/ML &amp;
              Research) · Kaivalya (Backend &amp; Infrastructure)
            </p>
          </div>

          <Card className="flex flex-col gap-5 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs font-medium text-muted-foreground">Preview · analyzed repository</p>
                <p className="font-mono text-sm font-medium">{demoRepo.fullName}</p>
              </div>
              <Badge variant="outline" className="border-risk-low/30 bg-risk-low/10 text-risk-low">
                Last analyzed {formatRelativeDate(demoRepo.lastAnalyzedAt!)}
              </Badge>
            </div>

            <div className="flex items-center gap-6">
              <HealthRing score={demoHealth.score} size={104} strokeWidth={9} />
              <dl className="grid flex-1 grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-xs text-muted-foreground">High risk</dt>
                  <dd className="font-mono text-lg font-semibold tabular-nums">
                    {demoHealth.highRiskComponentCount}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Security findings</dt>
                  <dd className="font-mono text-lg font-semibold tabular-nums">
                    {demoHealth.securityRiskCount}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Regression areas</dt>
                  <dd className="font-mono text-lg font-semibold tabular-nums">
                    {demoHealth.regressionRiskAreaCount}
                  </dd>
                </div>
                <div>
                  <dt className="text-xs text-muted-foreground">Files indexed</dt>
                  <dd className="font-mono text-lg font-semibold tabular-nums">
                    {demoRepo.fileCount}
                  </dd>
                </div>
              </dl>
            </div>

            <div className="rounded-lg border border-border bg-muted/40 p-3">
              <p className="mb-2 text-xs font-medium text-muted-foreground">
                Highest-risk component right now
              </p>
              <div className="flex items-center justify-between gap-2">
                <span className="truncate font-mono text-sm">auth/service.py</span>
                <RiskBadge level="CRITICAL" />
              </div>
            </div>
          </Card>
        </section>

        {/* How it works */}
        <section className="border-t border-border/70 bg-muted/20 py-16 md:py-20">
          <div className="mx-auto max-w-6xl px-4 md:px-8">
            <h2 className="text-2xl font-semibold tracking-tight">Repository onboarding</h2>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              From authorizing the GitHub App to a full repository dashboard, in five steps.
            </p>
            <ol className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {onboardingSteps.map((step, i) => (
                <li key={step.title}>
                  <Card className="h-full gap-2 p-4">
                    <span className="font-mono text-xs text-primary">
                      Step {String(i + 1).padStart(2, "0")}
                    </span>
                    <p className="text-sm font-semibold">{step.title}</p>
                    <p className="text-xs text-muted-foreground">{step.detail}</p>
                  </Card>
                </li>
              ))}
            </ol>
          </div>
        </section>

        {/* Feature grid */}
        <section className="border-t border-border/70 py-16 md:py-20">
          <div className="mx-auto max-w-6xl px-4 md:px-8">
            <h2 className="text-2xl font-semibold tracking-tight">
              One intelligence layer, eight capabilities
            </h2>
            <p className="mt-2 max-w-2xl text-muted-foreground">
              Every capability reads from the same unified repository representation, so risk,
              impact and explanations stay consistent across the product.
            </p>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {features.map((f) => (
                <Card key={f.title} className="gap-3 p-5">
                  <f.icon className="size-5 text-primary" aria-hidden="true" />
                  <p className="text-sm font-semibold">{f.title}</p>
                  <p className="text-xs text-muted-foreground">{f.detail}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* CTA */}
        <section className="border-t border-border/70 bg-muted/20 py-16 md:py-20">
          <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-6 px-4 md:flex-row md:items-center md:px-8">
            <div>
              <h2 className="text-2xl font-semibold tracking-tight">
                Give it a repository. Get an actionable software-health view.
              </h2>
              <p className="mt-2 max-w-xl text-muted-foreground">
                Connect a GitHub repository to start ingestion, or explore the live demo built on
                acme-labs/orbit-payments.
              </p>
            </div>
            <div className="flex shrink-0 gap-3">
              <Button size="lg" asChild>
                <Link href="/onboarding">
                  Connect a repository
                  <ArrowRight className="size-4" />
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-border/70 py-8">
        <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-3 px-4 text-xs text-muted-foreground md:flex-row md:px-8">
          <p>Repository Intelligence AI — BTech Final-Year Project.</p>
          <p className="font-mono">Next.js · TypeScript · Tailwind CSS · shadcn/ui · React Flow · Recharts</p>
        </div>
      </footer>
    </div>
  );
}
