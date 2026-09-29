---
description: Snapshot webinar build state to progress.txt so a new session can resume exactly where the build stopped
---

# /save-state

Snapshot the current session into `progress.txt` (repo root, gitignored) so `/resume` in a
new conversation continues with zero context loss.

---

## Step 1: Read state sources (one at a time, never batched)

- `plans/DEMOS.md`
- `plans/DECISIONS.md`
- `TODOS.md` (if it exists)

Then:

```bash
ls -la notebooks/ spaces/*/ plans/demo*_plan.md diagrams/ 2>/dev/null
```

Cell count and header map per notebook:

```bash
for f in notebooks/*.ipynb; do .venv/bin/python3 -c "
import json, sys
nb = json.load(open(sys.argv[1]))
print(sys.argv[1], 'cells:', len(nb['cells']))
for i, c in enumerate(nb['cells']):
    first = ''.join(c['source']).strip().splitlines()[:1]
    print('  ', i, c['cell_type'], first[0][:70] if first else '')
" "$f"; done 2>/dev/null
```

## Step 2: Status per demo

| Signal | Status |
|---|---|
| No plan | `not_started` |
| Plan, notebook missing or short of SPEC's cell count | `plan_only` / `building` |
| Notebook complete, validation + self-check pass | `notebook_done` |
| Spaces folder built, parity passes | `done` |
| Any validation failure or open TODO | `needs_fix` |

Run:

```bash
.venv/bin/python3 validate_notebooks.py --all --selfcheck --parity
```

## Step 3: Next action

Walk the build order 3, 1, 2. First demo not `done`:

| Status | Next action |
|---|---|
| `not_started` | `/research-demo N` |
| `plan_only` / `building` | `/build-notebook N` |
| `notebook_done` | `/build-space N` |
| `needs_fix` | the specific fix |

All three done: `/build-diagrams`, then the `golden-path-policy-demo` Actions repo, then the
pre-flight checks in SPEC.

## Step 4: Write progress.txt

```
WEBINAR: Platform Engineering Foundations - 3 Gradio demos
SAVED: <YYYY-MM-DD HH:MM>
REPO: /Users/axelsirota/repos/platform-engineering-webinar

==============================================================================
DEMO STATUS (build order 3, 1, 2)
==============================================================================

[done]          Demo 3 - Rollout simulator
                plan:      plans/demo3_plan.md
                notebook:  notebooks/demo3_rollout.ipynb (11/11 cells)
                spaces:    spaces/demo3_rollout/
                selfcheck: PASS

[building]      Demo 1 - Golden path portal
                plan:      plans/demo1_plan.md
                notebook:  notebooks/demo1_portal.ipynb (7/12 cells)
                next:      /build-notebook 1

[not_started]   Demo 2 - Funding game
                next:      /research-demo 2

[not_started]   Actions repo golden-path-policy-demo

==============================================================================
DIAGRAMS
==============================================================================

<built slugs>  /  <pending slugs>

==============================================================================
KNOWN ISSUES / OPEN TODOS
==============================================================================

<open entries, or "none">

==============================================================================
LOCKED DECISIONS (do not re-litigate without Axel)
==============================================================================

- SPEC is imp_docs/demos.md. It wins over any prompt block or plan.
- Stack: gradio==<pin>, pandas, numpy, plotly. Nothing else. No network.
- GRADIO_ANALYTICS_ENABLED=False before importing gradio.
- Synthetic, fictional data only. No real client or company names.
- Per-visitor gr.State; shared state only for the Demo 1 room and Demo 2 tally, locked.
- header_html and theme come from Demo 3, copied verbatim.
- Notebooks handed over with outputs cleared.
- Spaces app.py generated from the notebook, never hand-edited.
- Always verify cell_id before every NotebookEdit.

==============================================================================
KEY FILES
==============================================================================

CLAUDE.md                 - stack, conventions, build order
imp_docs/demos.md         - SPEC
imp_docs/outline.md       - course scope
plans/DECISIONS.md        - webinar manifest
plans/DEMOS.md            - status tracker
plans/demoN_plan.md       - cell-by-cell plans
notebooks/                - the three Colab notebooks
spaces/                   - Hugging Face Spaces backups
diagrams/                 - Mermaid sources and PNGs
validate_notebooks.py     - validator

==============================================================================
NEXT ACTION
==============================================================================

<one runnable command>
Reason: <one sentence>

==============================================================================
HOW TO RESUME
==============================================================================

1. Open /Users/axelsirota/repos/platform-engineering-webinar
2. Run /resume
3. If /resume is unavailable, read this file and run the NEXT ACTION.
```

## Step 5: gitignore

```bash
grep -q "progress.txt" .gitignore 2>/dev/null || echo "progress.txt" >> .gitignore
```

## Step 6: Confirm

```
progress.txt written.
  demo 3: <status>   demo 1: <status>   demo 2: <status>
Next action: <command>
Run /resume in any future session to reload this context.
```

---

## Non-Negotiables

- Real paths only, no placeholders
- NEXT ACTION is one runnable command
- Every demo listed, even `not_started`
- Cell counts always recorded against SPEC's count
- Plain text, no markdown, no emoji

---

## Notebook Edit Protocol (awareness)

If this command ends up editing notebook cells, follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`.
Blind bulk index-based rewrites are forbidden.
