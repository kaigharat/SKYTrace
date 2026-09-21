# Repository Intelligence AI — Frontend

BTech final-year project. This package is **Yashodhan's scope**: Product, Frontend & GitHub
Intelligence — the Next.js web application described in the project PRD
(`Repository_Intelligence_AI_PRD.docx`, §19 "Team Ownership").

It is a standalone, fully working frontend built against a **typed mock data layer**
(`lib/mock-data.ts`) shaped to match the backend Integration Contract in the PRD (§17, §18, §20),
so the real FastAPI backend can be wired in later by replacing the functions in that file with
`fetch` calls — no component changes required.

## What's implemented

Everything listed under "Yashodhan" in PRD §19:

- Next.js 16 (App Router) + TypeScript application architecture
- Repository dashboard: health score, risk distribution, health trend, recently-changed /
  high-impact components, security findings summary
- Risk cards and component-detail interface, including the explainable "Why is this risky?"
  panel, code quality metrics, downstream dependents and similar historical patterns
- Interactive dependency / call / impact graph (React Flow + dagre auto-layout), filterable by
  node type, with a relationship inspector panel
- GitHub App connect flow and repository selection interface (`/onboarding`)
- Pull-request AI review interface: risk summary, changed files, potentially affected
  components, recommended tests
- AI explanation interface (evidence + weighted contribution bars)
- Health trend charts (Recharts)
- Loading, error and not-found states for every route
- Light/dark theme (dark by default), full keyboard/focus accessibility pass

## Stack

Next.js · TypeScript · Tailwind CSS v4 · shadcn/ui (Radix) · React Flow · Recharts · next-themes

## Getting started

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). The app opens on the marketing/connect page;
the fastest way into the product is **View demo dashboard**, which opens the fully analyzed demo
repository `acme-labs/orbit-payments`.

```bash
npm run build   # production build + type check
npm run lint     # eslint
```

## Project structure

```
app/
  page.tsx                          Marketing / connect landing page
  onboarding/                       GitHub App connect + repository selection
  (app)/                            Authenticated shell (sidebar + topbar)
    repositories/
      page.tsx                      All connected repositories
      [repoId]/
        page.tsx                    Repository dashboard
        analyzing/                  Analysis progress (live-poll or animated demo)
        components/[componentId]/   Component risk detail
        graph/                      Dependency & call graph explorer
        pull-requests/              PR list + AI review detail
components/
  dashboard/  component-detail/  graph/  pr-review/  onboarding/  layout/  shared/  ui/
lib/
  types.ts        Domain types mirroring the backend Integration Contract
  mock-data.ts     Mock dataset + accessor functions (swap for real API calls)
  risk.ts          Risk-level → color/label mapping
  graph-layout.ts  dagre-based auto-layout for the dependency graph
design-system/
  repository-intelligence-ai/MASTER.md   Persisted design tokens (ui-ux-pro-max skill)
```

## Connecting the real backend

Replace the accessor functions at the bottom of `lib/mock-data.ts` (`getRepository`,
`getComponentsForRepo`, `getPullRequest`, etc.) with calls to the FastAPI endpoints in PRD §17.
The shapes in `lib/types.ts` already match the Backend → Frontend contract in PRD §20, so no
component or page should need to change.

See `docs/USER_GUIDE.md` for a walkthrough of every screen and `docs/DEMO_SCRIPT.md` for the
end-to-end demo flow.
