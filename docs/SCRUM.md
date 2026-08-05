# Scrum for this repository

This repo runs on a trimmed but real Scrum process, sized for small, mostly
single-developer work with heavy automation.

## Roles (adapted, lightweight)
- **Product Owner** — the repo owner (you): owns the Product Backlog, orders
  items by value, accepts/rejects increments.
- **Developer** — implements backlog items.
- **Scrum Master** — keeps ceremonies light and removes blockers (automation:
  the agent).

Each person may hold more than one role.

## Artifacts
- **Product Backlog** ([`docs/BACKLOG.md`](BACKLOG.md)) — an ordered list of
  items. Each item is a small **user story** with **acceptance criteria**.
- **Sprint Backlog** — the subset of backlog items committed to the current
  sprint, tracked in `docs/BACKLOG.md` (a "Current Sprint" section).
- **Increment** — working, verified software (ruff + pytest + runnable scripts)
  at the end of each sprint.

## Ceremonies (each sprint)
1. **Sprint Planning** — pick the next backlog item(s); define acceptance
   criteria; estimate effort (S/M/L).
2. **Daily/working check** — one short status line per work session: done
   today / doing / blockers. (For a solo run this is the agent's progress notes.)
3. **Sprint Review** — demonstrate the increment, report the physical ledger /
   results, and confirm acceptance criteria are met.
4. **Sprint Retrospective** — what went well / what to improve next sprint.
   The outputs are recorded at the bottom of the sprint log.

## Definition of Done (DoD)
An item is done only when:
- acceptance criteria pass;
- `ruff check .` is clean;
- `pytest` passes (or tests are deliberately skipped, not failed);
- the relevant docs (chapter README + `docs/ROADMAP.md`) are updated to reflect
  the change;
- the increment is reproducible by re-running the committed scripts.
