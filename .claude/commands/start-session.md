---
description: Begin a work session - load context, review progress, identify next steps
---

Start a new work session for this project.

## GUARD: Read the Manifest First

```bash
ls plans/DECISIONS.md 2>/dev/null
```

If missing, stop and say:

> `plans/DECISIONS.md` not found. Run `/init-webinar` first. Every command requires it.

## Step 1: Load Context

Read in order:
1. `CLAUDE.md`
2. `plans/DECISIONS.md`
3. `imp_docs/demos.md` (SPEC): shared conventions and the build order section

## Step 2: Load plans/DEMOS.md (status tracker)

If it does NOT exist, create it from this template (Write), then continue:

```markdown
# Demo Status

| Demo | Plan | Notebook | Self-check | Spaces | Click-through |
|---|---|---|---|---|---|
| 3 Rollout simulator | not_started | not_started | - | not_started | - |
| 1 Golden path portal | not_started | not_started | - | not_started | - |
| 2 Funding game | not_started | not_started | - | not_started | - |
| Actions repo golden-path-policy-demo | - | - | - | - | not_started |

## Demo 3 acceptance checks
<copy the checklist from SPEC>

## Demo 1 acceptance checks
<copy the checklist from SPEC>

## Demo 2 acceptance checks
<copy the checklist from SPEC>

## Pre-flight checks
<copy from SPEC>

## Open issues
- none
```

## Step 3: Cross-Check Filesystem

```bash
ls -la notebooks/ spaces/*/ plans/demo*_plan.md diagrams/ 2>/dev/null
```

Cell counts per notebook:

```bash
for f in notebooks/*.ipynb; do .venv/bin/python3 -c "
import json, sys
nb = json.load(open(sys.argv[1]))
print(sys.argv[1], 'cells:', len(nb['cells']))
" "$f"; done 2>/dev/null
```

Flag anything that:
- Exists on disk but is `not_started` in DEMOS.md
- Is `done` in DEMOS.md but missing on disk, or has the wrong cell count
- Has a notebook newer than its Spaces app.py (Spaces folder stale)

## Step 4: Report

The DEMOS.md table, plus mismatches from Step 3.

## Step 5: Recommend Next Step

Walk the build order 3, 1, 2. First demo not fully done decides it:

| State | Next |
|---|---|
| No plan | `/research-demo N` |
| Plan, notebook incomplete | `/build-notebook N` |
| Notebook done, no Spaces | `/build-space N` |
| Spaces stale | `/build-space N` |
| All three done | `/build-diagrams`, then the Actions repo, then pre-flight |

## Step 6: Ask

"Ready to proceed with <next step>? Or is there something else you want to work on?"

---

## Notebook Edit Protocol (awareness)

If this command ends up editing notebook cells, follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`.
Blind bulk index-based rewrites are forbidden.
