# User Guide

A screen-by-screen walkthrough of the Repository Intelligence AI frontend.

## 1. Landing page (`/`)

Explains the product and offers two entry points: **Connect a GitHub repository** (starts
onboarding) and **Explore the live demo** (jumps straight to the analyzed demo repository).

## 2. Onboarding (`/onboarding`)

Three steps, shown as a progress stepper at the top:

1. **Connect GitHub** — authorize the GitHub App. In this demo, "Continue with GitHub" simulates
   the OAuth round trip and grants access to a set of sample repositories.
2. **Select a repository** — search and pick a repository. Already-analyzed repositories open
   straight to their dashboard; unanalyzed ones start an analysis run.
3. **Start analysis** — handled automatically once a repository is selected.

## 3. Analysis progress (`/repositories/[repoId]/analyzing`)

Shows the ingestion pipeline stage by stage (clone → parse → build graph → analyze history → run
risk models → index embeddings → compute health score), with a live progress bar. Once complete,
it links to the repository dashboard.

## 4. Repository dashboard (`/repositories/[repoId]`)

The main working view:

- **Health score ring** — overall score out of 100, with the five weighted sub-scores
  (defect resilience, security posture, regression resilience, code quality, historical
  stability) as bar meters.
- **Risk distribution** — component counts across Critical / High / Medium / Low.
- **Repository graph preview** — node/edge counts with a link into the full graph explorer.
- **Health trend** — score over the last 14 analyses.
- **Recently changed & high-impact components** — sortable table linking into component detail.
- **Security findings** — top open findings with severity, category and location.
- **Recent pull requests** — quick links into PR reviews.

## 5. Component detail (`/repositories/[repoId]/components/[componentId]`)

For a single file/function/class:

- **Risk scores** — defect / security / regression risk, each 0–100%.
- **Why is this component risky?** — the evidence factors behind the score, each with a
  relative-contribution bar (this is the explainability requirement from PRD §12).
- **Code quality metrics** — LOC, cyclomatic complexity, coupling, centrality, change frequency,
  duplication, historical defect frequency.
- **Action buttons**:
  - *View code* — read-only source preview.
  - *View history* — commit timeline, with bug-fix commits flagged.
  - *View graph* — opens the dependency graph focused on this component.
  - *View similar bugs* — jumps to the similar historical patterns section.
- **Downstream dependents** — what would be affected if this component breaks.
- **Security findings** — findings scoped to this file, if any.
- **Similar historical patterns** — related past bugs/vulnerabilities/changes with a similarity
  score.

## 6. Dependency & call graph (`/repositories/[repoId]/graph`)

An interactive React Flow canvas of the repository graph (Repository / File / Function / Class /
Dependency / Commit / Pull Request nodes; IMPORTS / CALLS / DEFINES / INHERITS / DEPENDS_ON /
MODIFIED_BY / CO_CHANGED_WITH edges — PRD §10).

- Filter which node types are visible.
- Click a node to open the relationship inspector (outgoing/incoming edges, and — for files —
  its risk scores with a link into the full component detail page).
- Pan, zoom, and use the minimap; nodes are colored by risk level.

## 7. Pull requests (`/repositories/[repoId]/pull-requests`)

List of analyzed PRs with bug-risk badges. Selecting one opens the **PR review**:

- Bug / security / regression risk summary.
- AI review summary (plain-language explanation of why the PR is risky).
- Changed files, with additions/deletions and per-file risk.
- Potentially affected components, with the reasoning and hop distance in the call graph.
- Recommended tests, ranked by priority, with the suite path to run.

## Theming

The theme toggle (top right) switches between dark (default) and light mode. Dark mode is the
primary experience — this is a developer-tooling dashboard used for extended sessions.
