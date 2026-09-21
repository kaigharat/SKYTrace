# Demo script

Maps directly to PRD §25 "Final Demonstration Flow". Run `npm run dev` and follow along.

1. **Land on the homepage** (`/`). Point out the live preview card (health score, high-risk
   count, security findings) — this is real data from the demo repository, not a static image.
2. **Connect a real GitHub repository.**
   Click **Connect a GitHub repository** → **Continue with GitHub** → repository list appears.
   (In this demo, "GitHub" is simulated; a real deployment redirects to GitHub's OAuth flow via
   the GitHub App.)
3. **Run repository analysis.**
   Click **Start analysis** on `acme-labs/notification-service`. Watch the seven-stage pipeline
   run (clone → parse → graph → history → risk models → embeddings → health score).
4. **Show repository size, health score and risk distribution.**
   Navigate to `/repositories/repo-orbit-payments`. Call out the health ring (73/100), the five
   weighted sub-scores, and the risk distribution bar (2 critical, 7 high, 19 medium, 458 low
   across 486 files).
5. **Open a high-risk component.**
   Click `auth/service.py` in the components table (Critical, 91% defect risk).
6. **Show defect/security/regression scores.**
   Point out the three risk meters at the top of the component page.
7. **Open the explainability panel.**
   Scroll to "Why is this component risky?" — four weighted evidence factors summing to the
   score, each with a plain-language justification (historical defect frequency, dependency
   centrality, modification frequency, similarity to past defects).
8. **Open the dependency/call graph.**
   Click **View graph**. The graph opens focused on `auth/service.py`; click the node to show the
   relationship inspector (2 outgoing, 4 incoming relationships, including `PR #124`).
9. **Show downstream change impact.**
   Back on the component page, scroll to "Downstream dependents" — `payment/service.py`,
   `orders/checkout.py`, `api/middleware/session.py`, `billing/invoice.py`.
10. **Retrieve similar historical bug patterns.**
    Scroll to "Similar historical patterns" — three related past incidents with similarity
    scores (up to 91%).
11. **Open a pull request and run AI review.**
    Navigate to **Pull Requests** → **#124 Add retry handling to checkout payment flow**.
    Walk through the risk summary (Bug: High, Security: Medium, Regression: High), the AI
    summary paragraph, changed files, potentially affected components (with hop distance), and
    recommended tests (Authentication / Payment-flow / Order-flow — this is the exact example
    from PRD §7.4).
12. **Show the repository health and risk trends.**
    Return to the dashboard and point out the 14-analysis health trend chart (61 → 73, +12).

Total runtime: ~5 minutes.
