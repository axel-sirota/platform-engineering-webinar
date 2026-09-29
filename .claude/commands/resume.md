---
description: Reload saved webinar build state from progress.txt and orient the session to continue
---

# /resume

Load the saved state from `progress.txt` and orient the session so work continues
immediately. Ask at most one clarifying question.

---

## Step 1: Check for progress.txt

```bash
ls progress.txt 2>/dev/null
```

If missing:

> `progress.txt` not found. Run `/save-state` first, or `/start-session` to load context
> from scratch.

Stop here if missing.

## Step 2: Read progress.txt

Extract: demo statuses, open issues, locked decisions, NEXT ACTION.

## Step 3: Verify against the filesystem

The snapshot may be old:

```bash
ls -la notebooks/ spaces/*/ plans/demo*_plan.md diagrams/ 2>/dev/null
```

- A file exists that progress.txt says is missing: update your understanding
- progress.txt says done but the file is missing, or a notebook is newer than its Spaces
  app.py: flag it

Do NOT re-run full validation. Trust progress.txt unless the filesystem contradicts it.

## Step 4: Print orientation summary

No preamble:

```
=== RESUMED SESSION ===

Saved: <date>

DEMOS (build order 3, 1, 2)
  Demo 3 Rollout simulator     <status>  notebook <n>/11  spaces <status>
  Demo 1 Golden path portal    <status>  notebook <n>/12  spaces <status>
  Demo 2 Funding game          <status>  notebook <n>/13  spaces <status>
  Actions repo                 <status>

DIAGRAMS
  Built: <list>    Pending: <list>

OPEN ISSUES
  <list or "none">

NEXT ACTION
  <command>
  Reason: <one sentence>

KEY DECISIONS (active)
  - SPEC is imp_docs/demos.md and wins on conflict
  - gradio==<pin>, pandas, numpy, plotly only, no network
  - Synthetic, fictional data only
  - header_html and theme copied from Demo 3
  - Spaces app.py generated from the notebook
  - Verify cell_id before every NotebookEdit

=== READY ===
```

## Step 5: At most one question

- NEXT ACTION obvious: do not ask, confirm ready
- Two demos `building` at once: "Which demo first?"
- progress.txt conflicts with the filesystem: describe it and ask which is right

---

## Non-Negotiables

- progress.txt first, filesystem second
- Summary before any question
- One question max
- Do not build or fix anything until the user says "go" or "continue"

---

## Notebook Edit Protocol (awareness)

If this command ends up editing notebook cells, follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`.
Blind bulk index-based rewrites are forbidden.
