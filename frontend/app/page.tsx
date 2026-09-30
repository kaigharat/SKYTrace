import Link from "next/link";
import {
  ArrowRight,
  Bug,
  Code2,
  Cpu,
  Database,
  FileCode,
  FlaskConical,
  GitBranch,
  GitPullRequest,
  History,
  Layers,
  Network,
  ShieldAlert,
  Sparkles,
  Users,
  Zap,
  Activity,
  CheckCircle2,
  Terminal,
  ExternalLink,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { HealthRing } from "@/components/shared/health-ring";
import { LogoMark } from "@/components/shared/logo-mark";
import { RiskBadge } from "@/components/shared/risk-badge";
import { ThemeToggle } from "@/components/layout/theme-toggle";
import { FaqSection } from "@/components/shared/faq-section";
import { repositories as defaultRepos, repositoryHealth as defaultHealth } from "@/lib/mock-data";
import { formatRelativeDate } from "@/lib/format";
import { api } from "@/lib/api";

const workflowSteps = [
  {
    step: "01",
    title: "Connect Repository",
    detail: "Input any public GitHub repository URL or owner/repo slug.",
    icon: GithubMarkIcon,
  },
  {
    step: "02",
    title: "Collect Repository Data",
    detail: "Extract source files, AST syntax trees, dependencies & git history.",
    icon: FileCode,
  },
  {
    step: "03",
    title: "Extract Features",
    detail: "Compute code churn, complexity, coupling & historical metrics.",
    icon: Database,
  },
  {
    step: "04",
    title: "Run ML Analysis",
    detail: "Evaluate trained ML models (Random Forest/XGBoost) for risk scoring.",
    icon: Cpu,
  },
  {
    step: "05",
    title: "Generate Risk & Evidence",
    detail: "Classify component risk levels and extract explainable evidence.",
    icon: Sparkles,
  },
  {
    step: "06",
    title: "Investigate Dashboard",
    detail: "Explore interactive graphs, component inspection & PR impact.",
    icon: Activity,
  },
];

const targetAudiences = [
  {
    title: "Developers",
    icon: Code2,
    badge: "For Code Authors",
    detail:
      "Identify high-risk files before committing, understand cross-file blast radius, and receive targeted unit test recommendations.",
  },
  {
    title: "Code Reviewers",
    icon: GitPullRequest,
    badge: "For Reviewers",
    detail:
      "Review pull requests faster with automated ML risk scores, regression impact heatmaps, and line-level security evidence.",
  },
  {
    title: "Students & Researchers",
    icon: FlaskConical,
    badge: "For Academic Study",
    detail:
      "Study repository evolution metrics, AST component dependency graphs, FAISS vector embeddings, and machine learning defect models.",
  },
  {
    title: "Software Project Teams",
    icon: Users,
    badge: "For Tech Leads",
    detail:
      "Track repository health trends, regression hotspots, and security vulnerabilities across release sprints.",
  },
];

const architectureNodes = [
  { step: "User", label: "Developer / Faculty", desc: "Initiates analysis or views dashboard" },
  { step: "Next.js Frontend", label: "Web UI Layer", desc: "React 19 + Tailwind + Recharts" },
  { step: "FastAPI Backend", label: "REST Engine", desc: "Python 3.11 asynchronous API" },
  { step: "GitHub Repository", label: "Data Source", desc: "Public repos via PyGithub API" },
  { step: "Code & Repo Analysis", label: "Parser Engine", desc: "AST parsing & git history miner" },
  { step: "Feature Extraction", label: "Metrics Builder", desc: "Churn, complexity & coupling" },
  { step: "ML Analysis", label: "Inference Model", desc: "Defect & Security prediction" },
  { step: "Risk Calculation", label: "Scoring Engine", desc: "Health 0-100 & severity weights" },
  { step: "Explainable Findings", label: "Evidence Engine", desc: "Line trace & FAISS history" },
  { step: "Dashboard", label: "Interactive View", desc: "Real-time decision intelligence" },
];

const existingModules = [
  {
    title: "Repository Dashboard",
    icon: Activity,
    status: "Active Module",
    detail:
      "Centralized repository health score (0-100), 14-analysis trend chart, risk distribution, and metric breakdowns.",
  },
  {
    title: "Component Analysis & Inspector",
    icon: FileCode,
    status: "Active Module",
    detail:
      "Deep component-level inspection with ML defect probability, line-by-line code viewer, and historical commit timeline.",
  },
  {
    title: "Dependency Graph & Blast Radius",
    icon: Network,
    status: "Active Module",
    detail:
      "Interactive graph representation of component dependencies, call relationships, and cross-file regression blast radius.",
  },
  {
    title: "Pull Request Review & Impact",
    icon: GitPullRequest,
    status: "Active Module",
    detail:
      "AI-powered PR risk review analyzing modified files, impact blast radius, and prioritized unit test recommendations.",
  },
  {
    title: "Security & Vulnerability Analysis",
    icon: ShieldAlert,
    status: "Active Module",
    detail:
      "Static analysis combined with ML vulnerability scoring, normalized by severity, location, and actionable evidence.",
  },
  {
    title: "Historical Defect Intelligence",
    icon: History,
    status: "Active Module",
    detail:
      "FAISS-backed vector search matching active components against past defect patterns and git commit fixes.",
  },
];

function GithubMarkIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 24 24" fill="currentColor" className="size-4" {...props}>
      <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
    </svg>
  );
}

export default async function Home() {
  const repos = await api.getRepositories().catch(() => []);
  const completedRepo = repos.find((r) => r.analysisStatus === "completed");
  const demoRepo = completedRepo || repos[0] || defaultRepos[0];

  let demoHealth = completedRepo
    ? await api.getRepositoryHealth(completedRepo.id).catch(() => null)
    : await api.getRepositoryHealth(demoRepo.id).catch(() => defaultHealth[demoRepo.id]);
  if (!demoHealth) demoHealth = defaultHealth[demoRepo.id] || defaultHealth["repo-orbit-payments"];

  return (
    <div className="flex min-h-svh flex-col bg-background text-foreground antialiased selection:bg-primary/20">
      {/* Top Navbar */}
      <header className="sticky top-0 z-30 border-b border-border/70 bg-background/85 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 md:px-8">
          <div className="flex items-center gap-3">
            <LogoMark />
            <div className="flex flex-col">
              <span className="font-mono text-sm font-bold tracking-tight text-foreground">
                SkyTrace
              </span>
              <span className="text-[10px] font-medium text-muted-foreground">
                Repository Intelligence AI
              </span>
            </div>
          </div>
          <nav className="hidden items-center gap-6 md:flex">
            <a href="#about" className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
              What is SkyTrace
            </a>
            <a href="#audience" className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
              Who it's for
            </a>
            <a href="#workflow" className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
              Workflow
            </a>
            <a href="#architecture" className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
              Architecture
            </a>
            <a href="#modules" className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
              Modules
            </a>
            <a href="#faq" className="text-xs font-medium text-muted-foreground transition-colors hover:text-foreground">
              FAQ
            </a>
          </nav>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Button variant="ghost" size="sm" asChild className="hidden sm:inline-flex">
              <Link href={`/repositories/${demoRepo.id}`}>Demo Dashboard</Link>
            </Button>
            <Button size="sm" asChild className="gap-1.5 font-medium shadow-sm">
              <Link href="/onboarding">
                <span>Analyze Repo</span>
                <ArrowRight className="size-3.5" />
              </Link>
            </Button>
          </div>
        </div>
      </header>

      <main className="flex-1">
        {/* Section 1: Hero */}
        <section className="relative overflow-hidden border-b border-border/70 bg-gradient-to-b from-primary/5 via-background to-background py-16 md:py-24">
          <div className="pointer-events-none absolute -top-40 left-1/2 -z-10 size-[600px] -translate-x-1/2 rounded-full bg-primary/10 blur-3xl" />
          
          <div className="mx-auto grid max-w-7xl gap-12 px-4 md:grid-cols-12 md:px-8">
            <div className="flex flex-col justify-center gap-6 md:col-span-7">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary font-mono text-xs">
                  SkyTrace · Repository Intelligence AI
                </Badge>
                <Badge variant="secondary" className="text-[11px] font-medium">
                  BTech Final-Year Software Engineering Project
                </Badge>
              </div>

              <h1 className="text-4xl font-extrabold tracking-tight text-balance sm:text-5xl lg:text-6xl">
                Understand your software repository as a connected ML system.
              </h1>

              <p className="max-w-2xl text-base text-muted-foreground text-pretty sm:text-lg">
                SkyTrace combines source code AST semantics, dependency structures, and Git history into one unified representation to predict defect risks, detect security vulnerabilities, and analyze regression impact.
              </p>

              <div className="flex flex-wrap items-center gap-3 pt-2">
                <Button size="lg" asChild className="gap-2 text-sm font-semibold shadow-md">
                  <Link href="/onboarding">
                    <span>Analyze a Repository</span>
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button size="lg" variant="outline" asChild className="gap-2 text-sm">
                  <a href="#workflow">
                    <span>See How It Works</span>
                    <ArrowRight className="size-4" />
                  </a>
                </Button>
              </div>

              {/* Team attribution */}
              <div className="mt-4 rounded-lg border border-border/60 bg-muted/30 p-3.5 text-xs text-muted-foreground">
                <p className="font-semibold text-foreground mb-1">Project Engineering Team:</p>
                <p>
                  Yashodhan (Product, Frontend &amp; GitHub Intelligence) · Swarali (AI/ML &amp; Research) · Kaivalya (Backend &amp; Infrastructure)
                </p>
              </div>
            </div>

            {/* Hero Live Preview Card */}
            <div className="flex items-center justify-center md:col-span-5">
              <Card className="w-full max-w-md flex-col gap-5 p-6 shadow-xl border-primary/20 bg-card/95 backdrop-blur">
                <div className="flex items-center justify-between border-b border-border/60 pb-3">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-muted-foreground">Live Repository Preview</span>
                    <p className="font-mono text-sm font-bold text-foreground truncate">{demoRepo.fullName}</p>
                  </div>
                  <Badge variant="outline" className="border-risk-low/30 bg-risk-low/10 text-risk-low text-[10px]">
                    Analyzed {formatRelativeDate(demoRepo.lastAnalyzedAt!)}
                  </Badge>
                </div>

                <div className="flex items-center gap-5">
                  <HealthRing score={demoHealth.score} size={96} strokeWidth={8} />
                  <dl className="grid flex-1 grid-cols-2 gap-2 text-xs">
                    <div className="rounded-md bg-muted/40 p-2">
                      <dt className="text-muted-foreground text-[10px]">High Defect Risk</dt>
                      <dd className="font-mono text-base font-bold tabular-nums text-foreground">
                        {demoHealth.highRiskComponentCount}
                      </dd>
                    </div>
                    <div className="rounded-md bg-muted/40 p-2">
                      <dt className="text-muted-foreground text-[10px]">Security Findings</dt>
                      <dd className="font-mono text-base font-bold tabular-nums text-destructive">
                        {demoHealth.securityRiskCount}
                      </dd>
                    </div>
                    <div className="rounded-md bg-muted/40 p-2">
                      <dt className="text-muted-foreground text-[10px]">Regression Areas</dt>
                      <dd className="font-mono text-base font-bold tabular-nums text-foreground">
                        {demoHealth.regressionRiskAreaCount}
                      </dd>
                    </div>
                    <div className="rounded-md bg-muted/40 p-2">
                      <dt className="text-muted-foreground text-[10px]">Files Analyzed</dt>
                      <dd className="font-mono text-base font-bold tabular-nums text-foreground">
                        {demoRepo.fileCount}
                      </dd>
                    </div>
                  </dl>
                </div>

                <div className="rounded-lg border border-border/80 bg-muted/50 p-3">
                  <p className="mb-1 text-[11px] font-medium text-muted-foreground">
                    Highest-Risk Component
                  </p>
                  <div className="flex items-center justify-between gap-2">
                    <span className="truncate font-mono text-xs font-semibold">auth/service.py</span>
                    <RiskBadge level="CRITICAL" />
                  </div>
                </div>

                <Button variant="outline" size="sm" asChild className="w-full gap-1.5 font-medium">
                  <Link href={`/repositories/${demoRepo.id}`}>
                    <span>Explore Demo Dashboard</span>
                    <ExternalLink className="size-3.5" />
                  </Link>
                </Button>
              </Card>
            </div>
          </div>
        </section>

        {/* Section 2: What is SkyTrace? */}
        <section id="about" className="border-b border-border/70 py-16 md:py-24">
          <div className="mx-auto max-w-5xl px-4 text-center md:px-8">
            <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
              Core Purpose &amp; Problem Statement
            </Badge>
            <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
              What is SkyTrace?
            </h2>
            <p className="mt-4 text-lg text-muted-foreground text-pretty max-w-3xl mx-auto leading-relaxed">
              Modern software repositories are complex, inter-connected systems. Standard static linters evaluate code in isolation, missing systemic risks. <strong className="text-foreground">SkyTrace</strong> bridges this gap by unifying source code AST syntax, dependency call graphs, Git commit churn history, and Machine Learning models into a single intelligence layer that predicts software defects, identifies security vulnerabilities, and highlights regression blast radius.
            </p>

            <div className="mt-12 grid gap-6 sm:grid-cols-3 text-left">
              <Card className="p-6 gap-3">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Layers className="size-5" />
                </div>
                <h3 className="font-semibold text-base">Integrated Repository Data</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Extracts AST structural trees, import &amp; call graphs, historical commit logs, and static analyzer output into a single graph representation.
                </p>
              </Card>

              <Card className="p-6 gap-3">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Cpu className="size-5" />
                </div>
                <h3 className="font-semibold text-base">ML Defect Prediction</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Evaluates Machine Learning models trained on historical churn and bug fix patterns to estimate defect probabilities per component.
                </p>
              </Card>

              <Card className="p-6 gap-3">
                <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Sparkles className="size-5" />
                </div>
                <h3 className="font-semibold text-base">Explainable Intelligence</h3>
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Provides line-level evidence, FAISS-based historical defect similarity matches, and prioritized test recommendations for developers.
                </p>
              </Card>
            </div>
          </div>
        </section>

        {/* Section 3: Who is it for? */}
        <section id="audience" className="border-b border-border/70 bg-muted/20 py-16 md:py-24">
          <div className="mx-auto max-w-7xl px-4 md:px-8">
            <div className="text-center">
              <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
                Target Stakeholders
              </Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                Who is SkyTrace built for?
              </h2>
              <p className="mt-2 text-muted-foreground">
                Tailored views and actionable software engineering intelligence for every role.
              </p>
            </div>

            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
              {targetAudiences.map((aud) => (
                <Card key={aud.title} className="flex flex-col justify-between p-6 transition-all hover:border-primary/40 hover:shadow-md">
                  <div>
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <aud.icon className="size-5" />
                      </div>
                      <Badge variant="secondary" className="text-[10px]">
                        {aud.badge}
                      </Badge>
                    </div>
                    <h3 className="text-lg font-bold">{aud.title}</h3>
                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                      {aud.detail}
                    </p>
                  </div>
                  <div className="mt-6 flex items-center gap-1 text-xs font-semibold text-primary">
                    <span>Learn module details</span>
                    <ArrowRight className="size-3" />
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Section 4: User Guide (Workflow) */}
        <section id="workflow" className="border-b border-border/70 py-16 md:py-24">
          <div className="mx-auto max-w-7xl px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
                User Guide &amp; Execution Steps
              </Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                How to use SkyTrace in 6 simple steps
              </h2>
              <p className="mt-2 text-muted-foreground">
                From connecting a GitHub URL to inspecting interactive risk dashboards and PR impact reviews.
              </p>
            </div>

            <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {workflowSteps.map((step) => (
                <Card key={step.step} className="p-6 gap-3 relative overflow-hidden border-border/80 hover:border-primary/30 transition-colors">
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-primary bg-primary/10 px-2.5 py-1 rounded-md">
                      Step {step.step}
                    </span>
                    <step.icon className="size-5 text-muted-foreground" />
                  </div>
                  <h3 className="text-base font-bold text-foreground mt-2">{step.title}</h3>
                  <p className="text-xs text-muted-foreground leading-relaxed">{step.detail}</p>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Section 5: Input → Processing → Output Pipeline */}
        <section className="border-b border-border/70 bg-muted/20 py-16 md:py-24">
          <div className="mx-auto max-w-7xl px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
                Data Transformation Pipeline
              </Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                Input → Processing → Output Pipeline
              </h2>
              <p className="mt-2 text-muted-foreground">
                How repository raw data flows through feature extraction and ML inference into decision outputs.
              </p>
            </div>

            <div className="mt-12 grid gap-6 lg:grid-cols-3 items-stretch">
              {/* Input Card */}
              <Card className="p-6 flex flex-col justify-between border-primary/20 bg-card">
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <span className="flex size-7 items-center justify-center rounded-full bg-primary/10 text-primary font-mono text-xs font-bold">1</span>
                    <h3 className="font-bold text-lg text-foreground">INPUT DATA</h3>
                  </div>
                  <ul className="space-y-3 text-xs text-muted-foreground">
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <GithubMarkIcon className="size-4 shrink-0 text-foreground" />
                      <span><strong>GitHub Repository</strong> (Public repo URL / slug)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <FileCode className="size-4 shrink-0 text-foreground" />
                      <span><strong>Source Code &amp; AST</strong> (Python, JS, TS)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <GitPullRequest className="size-4 shrink-0 text-foreground" />
                      <span><strong>Pull Requests &amp; Diffs</strong> (Modified lines &amp; files)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <History className="size-4 shrink-0 text-foreground" />
                      <span><strong>Git Churn &amp; Commit Logs</strong> (Historical bug fixes)</span>
                    </li>
                  </ul>
                </div>
              </Card>

              {/* Processing Card */}
              <Card className="p-6 flex flex-col justify-between border-primary/40 bg-card relative shadow-md">
                <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                  <Badge className="bg-primary text-primary-foreground font-mono text-[10px]">Core ML Processing Engine</Badge>
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-4 mt-1">
                    <span className="flex size-7 items-center justify-center rounded-full bg-primary text-primary-foreground font-mono text-xs font-bold">2</span>
                    <h3 className="font-bold text-lg text-foreground">PROCESSING PIPELINE</h3>
                  </div>
                  <ul className="space-y-3 text-xs text-muted-foreground">
                    <li className="flex items-center gap-2 rounded-md bg-primary/5 border border-primary/20 p-2.5">
                      <Cpu className="size-4 shrink-0 text-primary" />
                      <span><strong>Repository Analysis</strong> (Ingestion &amp; parsing)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-primary/5 border border-primary/20 p-2.5">
                      <Database className="size-4 shrink-0 text-primary" />
                      <span><strong>Feature Extraction</strong> (Complexity, churn, coupling)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-primary/5 border border-primary/20 p-2.5">
                      <Zap className="size-4 shrink-0 text-primary" />
                      <span><strong>ML Risk Analysis</strong> (Random Forest / XGBoost models)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-primary/5 border border-primary/20 p-2.5">
                      <Network className="size-4 shrink-0 text-primary" />
                      <span><strong>Dependency &amp; Call Graphing</strong> (DAG blast radius)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-primary/5 border border-primary/20 p-2.5">
                      <History className="size-4 shrink-0 text-primary" />
                      <span><strong>Historical Vector Search</strong> (FAISS defect similarity)</span>
                    </li>
                  </ul>
                </div>
              </Card>

              {/* Output Card */}
              <Card className="p-6 flex flex-col justify-between border-primary/20 bg-card">
                <div>
                  <div className="flex items-center gap-2 mb-4">
                    <span className="flex size-7 items-center justify-center rounded-full bg-primary/10 text-primary font-mono text-xs font-bold">3</span>
                    <h3 className="font-bold text-lg text-foreground">DECISION OUTPUTS</h3>
                  </div>
                  <ul className="space-y-3 text-xs text-muted-foreground">
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <CheckCircle2 className="size-4 shrink-0 text-risk-low" />
                      <span><strong>Repository Health Score</strong> (0-100 overall score)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <Bug className="size-4 shrink-0 text-risk-high" />
                      <span><strong>Defect Risk</strong> (LOW / MEDIUM / HIGH / CRITICAL)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <ShieldAlert className="size-4 shrink-0 text-risk-critical" />
                      <span><strong>Security Risk Findings</strong> (Semgrep + ML trace)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <GitBranch className="size-4 shrink-0 text-foreground" />
                      <span><strong>Regression Area &amp; Impact</strong> (Blast radius)</span>
                    </li>
                    <li className="flex items-center gap-2 rounded-md bg-muted/40 p-2.5">
                      <Sparkles className="size-4 shrink-0 text-primary" />
                      <span><strong>Explainable Evidence</strong> (Line triggers &amp; test tips)</span>
                    </li>
                  </ul>
                </div>
              </Card>
            </div>
          </div>
        </section>

        {/* Section 6: Technical Architecture Flow */}
        <section id="architecture" className="border-b border-border/70 py-16 md:py-24">
          <div className="mx-auto max-w-7xl px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
                System Engineering Architecture
              </Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                What is the system doing behind the scenes?
              </h2>
              <p className="mt-2 text-muted-foreground">
                End-to-end multi-tier execution path from client UI interaction to ML inference and explainable findings.
              </p>
            </div>

            <div className="mt-12 grid gap-3 sm:grid-cols-2 md:grid-cols-5">
              {architectureNodes.map((node, index) => (
                <div key={node.step} className="flex flex-col items-center">
                  <Card className="w-full p-4 text-center gap-2 h-full flex flex-col justify-between border-border/80 hover:border-primary/40 transition-colors">
                    <div>
                      <span className="font-mono text-[10px] font-semibold text-primary bg-primary/10 px-2 py-0.5 rounded">
                        0{index + 1}
                      </span>
                      <h4 className="font-bold text-sm text-foreground mt-2">{node.step}</h4>
                      <p className="text-[11px] font-medium text-primary mt-0.5">{node.label}</p>
                    </div>
                    <p className="text-[11px] text-muted-foreground mt-2 pt-2 border-t border-border/60">
                      {node.desc}
                    </p>
                  </Card>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Section 7: Main Modules */}
        <section id="modules" className="border-b border-border/70 bg-muted/20 py-16 md:py-24">
          <div className="mx-auto max-w-7xl px-4 md:px-8">
            <div className="text-center max-w-3xl mx-auto">
              <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
                Available Application Modules
              </Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                Core System Modules &amp; Capabilities
              </h2>
              <p className="mt-2 text-muted-foreground">
                Verified modules active and accessible within the SkyTrace platform.
              </p>
            </div>

            <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
              {existingModules.map((mod) => (
                <Card key={mod.title} className="p-6 gap-3 flex flex-col justify-between hover:border-primary/40 transition-colors">
                  <div>
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                        <mod.icon className="size-5" />
                      </div>
                      <Badge variant="outline" className="border-risk-low/40 bg-risk-low/10 text-risk-low text-[10px]">
                        {mod.status}
                      </Badge>
                    </div>
                    <h3 className="font-bold text-base text-foreground">{mod.title}</h3>
                    <p className="text-xs text-muted-foreground leading-relaxed mt-2">{mod.detail}</p>
                  </div>
                  <div className="pt-4 border-t border-border/60">
                    <Button variant="ghost" size="sm" asChild className="w-full justify-between text-xs font-semibold text-primary">
                      <Link href={`/repositories/${demoRepo.id}`}>
                        <span>Explore Module</span>
                        <ArrowRight className="size-3.5" />
                      </Link>
                    </Button>
                  </div>
                </Card>
              ))}
            </div>
          </div>
        </section>

        {/* Section 8: Live Repository Preview */}
        <section className="border-b border-border/70 py-16 md:py-24">
          <div className="mx-auto max-w-7xl px-4 md:px-8">
            <Card className="p-8 border-primary/30 bg-card shadow-lg">
              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-border/70 pb-6">
                <div>
                  <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary font-mono text-xs">
                    Live Analyzer Status
                  </Badge>
                  <h2 className="text-2xl font-bold text-foreground mt-2">
                    Active Demo Repository Analysis: <span className="font-mono text-primary">{demoRepo.fullName}</span>
                  </h2>
                  <p className="text-xs text-muted-foreground mt-1">
                    Real analysis fetched dynamically from FastAPI Backend logic.
                  </p>
                </div>
                <Button size="lg" asChild className="gap-2 font-semibold shrink-0">
                  <Link href={`/repositories/${demoRepo.id}`}>
                    <span>Launch Full Dashboard</span>
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <div className="flex items-center gap-4 rounded-lg border border-border p-4 bg-muted/30">
                  <HealthRing score={demoHealth.score} size={64} strokeWidth={6} />
                  <div>
                    <p className="text-xs text-muted-foreground">Overall Health</p>
                    <p className="font-mono text-xl font-bold text-foreground">{demoHealth.score} / 100</p>
                  </div>
                </div>

                <div className="rounded-lg border border-border p-4 bg-muted/30 flex flex-col justify-center">
                  <p className="text-xs text-muted-foreground">High-Risk Components</p>
                  <p className="font-mono text-xl font-bold text-risk-high">{demoHealth.highRiskComponentCount}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Component probability &gt; 0.70</p>
                </div>

                <div className="rounded-lg border border-border p-4 bg-muted/30 flex flex-col justify-center">
                  <p className="text-xs text-muted-foreground">Security Vulnerabilities</p>
                  <p className="font-mono text-xl font-bold text-destructive">{demoHealth.securityRiskCount}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Semgrep + ML scan findings</p>
                </div>

                <div className="rounded-lg border border-border p-4 bg-muted/30 flex flex-col justify-center">
                  <p className="text-xs text-muted-foreground">Regression Areas</p>
                  <p className="font-mono text-xl font-bold text-foreground">{demoHealth.regressionRiskAreaCount}</p>
                  <p className="text-[10px] text-muted-foreground mt-0.5">Blast radius impact zones</p>
                </div>
              </div>
            </Card>
          </div>
        </section>

        {/* Section 9: FAQ */}
        <section id="faq" className="border-b border-border/70 bg-muted/20 py-16 md:py-24">
          <div className="mx-auto max-w-4xl px-4 md:px-8">
            <div className="text-center mb-12">
              <Badge variant="outline" className="border-primary/30 bg-primary/5 text-primary">
                Frequently Asked Questions
              </Badge>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                Got Questions? We Have Answers.
              </h2>
              <p className="mt-2 text-muted-foreground">
                Everything you need to know about SkyTrace, its analysis pipeline, and ML scoring.
              </p>
            </div>

            <FaqSection />
          </div>
        </section>

        {/* Section 10: Final CTA */}
        <section className="py-20 md:py-28 relative overflow-hidden bg-gradient-to-t from-primary/10 via-background to-background">
          <div className="mx-auto max-w-4xl px-4 text-center md:px-8">
            <Badge variant="outline" className="border-primary/40 bg-primary/10 text-primary font-mono text-xs">
              Get Started Now
            </Badge>
            <h2 className="mt-4 text-3xl font-extrabold tracking-tight sm:text-4xl md:text-5xl">
              Ready to analyze a repository?
            </h2>
            <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
              Paste any public GitHub repository URL or slug to generate real-time ML risk analysis, component graphs, and explainable defect intelligence.
            </p>
            <div className="mt-8 flex flex-wrap justify-center gap-4">
              <Button size="lg" asChild className="gap-2 font-semibold shadow-lg text-base px-8 py-6">
                <Link href="/onboarding">
                  <span>Analyze a Repository</span>
                  <ArrowRight className="size-5" />
                </Link>
              </Button>
              <Button size="lg" variant="outline" asChild className="text-base px-8 py-6">
                <Link href={`/repositories/${demoRepo.id}`}>
                  <span>View Live Demo</span>
                </Link>
              </Button>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t border-border/70 py-8 bg-card">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 px-4 text-xs text-muted-foreground md:flex-row md:px-8">
          <div className="flex items-center gap-2">
            <LogoMark />
            <span className="font-mono font-bold text-foreground">SkyTrace</span>
            <span>— BTech Final-Year Software Engineering Project</span>
          </div>
          <p className="font-mono text-[11px]">
            Next.js 16 · React 19 · FastAPI · Python ML · Tailwind CSS · shadcn/ui
          </p>
        </div>
      </footer>
    </div>
  );
}
