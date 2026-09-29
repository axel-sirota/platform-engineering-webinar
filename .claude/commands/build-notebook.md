---
description: Build one demo notebook from its plan, 5 cells at a time with approval checkpoints
---

Build demo notebook: $ARGUMENTS

(Argument is a demo number, 1 to 3. Required.)

## GUARD: Read the Manifest First

```bash
ls plans/DECISIONS.md plans/demo$ARGUMENTS_plan.md 2>/dev/null
```

- No `plans/DECISIONS.md`: stop and say "Run `/init-webinar` first."
- No `plans/demo<N>_plan.md`: stop and say "Run `/research-demo <N>` first."

---

## Demo Map

| N | Notebook | SPEC cells | Final cells (with deploy cell) |
|---|---|---|---|
| 1 | notebooks/demo1_portal.ipynb | 12 | 13 |
| 2 | notebooks/demo2_funding_game.ipynb | 13 | 14 |
| 3 | notebooks/demo3_rollout.ipynb | 11 | 12 |

This command builds SPEC's cells. `/build-space <N>` then inserts the optional "deploy to
Spaces" cell between the launch cell and the instructor notes (see `plans/DECISIONS.md`).
Until then the validator reports a cell-count failure; that one is expected.

The environment is always **Colab** (Runtime > Run all), with the Spaces folder as backup.
Spaces files are built separately by `/build-space <N>`.

---

## Pre-Work: MANDATORY Reading

1. `CLAUDE.md`
2. `plans/DECISIONS.md`
3. `imp_docs/demos.md` (SPEC): shared conventions + this demo's section + its prompt block
4. `plans/demo<N>_plan.md`: the cell-by-cell source
5. For Demo 1 or 2: the built `notebooks/demo3_rollout.ipynb`, to copy `header_html` and the
   theme verbatim

### Show Plan Summary Before Building

In chat, show:
1. Demo title, what it teaches, its minutes in the webinar
2. The cell list (number, type, one line each), matching SPEC's count
3. Acceptance checks and which cell proves each
4. Any SPEC DEVIATIONS from the plan
5. Shared code copied from Demo 3 (for Demo 1 and 2)

**DO NOT PROCEED until the user approves this summary.**

---

## Core Rules

### 1. SPEC's cell list is the structure
Build exactly the cells SPEC lists, in that order. No extra cells, no merged cells. The
shape is: markdown intro, install, imports and config, pure logic, self-check, UI helpers,
Blocks layout, launch, instructor notes.

### 2. Projector code
The code is shown on a projector to engineers:
- Short functions, docstrings, type hints, no clever one-liners
- A comment on the first line of every code cell saying what the cell does
- Comments say WHY, not what. The instructor narrates from them

### 3. Pure logic stays pure
Cells for rules, generators, models and KPIs do not use gradio. They are testable in the
self-check cell and reusable by the GitHub Actions extra (Demo 1).

### 4. Nothing blocks
Every cell runs top to bottom as written on a fresh free Colab CPU runtime in under 60 s.
The only prompt is `getpass` for ADMIN_KEY in Demo 1 when neither Colab userdata nor the
environment has it.

### 5. Stack and safety (from SPEC)
- `%pip install -q gradio==<pin>` from `plans/DECISIONS.md`. pandas, numpy, plotly only
- `os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"` before `import gradio`
- No network calls, no uploads, no free text shown to other visitors
- Per-visitor state in `gr.State` or handler arguments; shared state only where SPEC allows,
  behind `threading.Lock`
- Every status colour paired with a word
- Synthetic, fictional names only. No real client, company or person names
- User-visible text in English with the spelling from `plans/DECISIONS.md`

### 6. Self-check cell
Plain asserts, no pytest. Ends with `print("All Demo <N> checks passed")`. Uses separate
instances for shared objects so the real ones start empty.

### 7. Launch cell
```python
# Gradio 6: theme goes to launch(), not gr.Blocks(). See plans/DECISIONS.md
demo.queue(default_concurrency_limit=64).launch(share=True, theme=THEME, show_error=True, debug=False)
print("Paste the public link in the Teams chat. It lasts 72 hours, and only while this tab stays open.")
```

---

## CRITICAL: 5-Cell Approval Checkpoints - MANDATORY

**NEVER ADD MORE THAN 5 CELLS WITHOUT EXPLICIT APPROVAL.**

1. Add up to 5 cells
2. STOP
3. Validate: `.venv/bin/python3 validate_notebooks.py notebooks/demo<N>_*.ipynb`
4. Once the self-check cell exists, also run
   `.venv/bin/python3 validate_notebooks.py notebooks/demo<N>_*.ipynb --selfcheck`
   and show the output
5. **Unconditional /save-state rule**: after the batch that completes the notebook, and at
   every 10-cell boundary, invoke `/save-state`. Not skipped under "go until the end"
6. Ask: "I have added cells X-Y. How does it look? Should I continue?"
   Under blanket "go until end" approval skip the question, never the validation or save-state

Forbidden: 6+ cells in one batch without approval, skipping validation, skipping save-state.

Write any cell over ~30 lines in its own tool call so the JSON never truncates.

---

## Cell Order: ALWAYS Verify cell_id

Before EVERY NotebookEdit (replace, insert, delete), print the cell map:

```bash
.venv/bin/python3 -c "
import json, sys
nb = json.load(open(sys.argv[1]))
for i, c in enumerate(nb['cells']):
    print(i, c.get('id','?'), c['cell_type'], repr(''.join(c['source'])[:60]))
" notebooks/demo<N>_<name>.ipynb
```

Confirm the target cell_id is where you expect, THEN edit.

Workflow:
1. `mkdir -p notebooks`, create the empty notebook with Write (skeleton below)
2. Insert Cell 0 with `edit_mode="insert"`, no `cell_id`
3. Print the map, insert the next cell after the last id
4. Chain `cell_id` for every following cell. Never assume append order

### Empty Notebook Skeleton
```json
{
 "nbformat": 4,
 "nbformat_minor": 5,
 "metadata": {
  "colab": {"provenance": []},
  "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
  "language_info": {"name": "python", "version": "3.11.0"}
 },
 "cells": []
}
```

---

## Markdown Rendering

Markdown cells are raw strings. Never escape markdown characters, never double-backslash
headers. Mermaid blocks in markdown render on GitHub, not in Colab; if a diagram matters on
screen, use `/build-diagrams` and embed the PNG.

---

## Workflow Summary

1. Read all context, show the plan summary, wait for approval
2. Create the notebook skeleton if missing (never overwrite an existing notebook)
3. Build in 5-cell batches with validation and approval
4. Final validation:
   - `.venv/bin/python3 validate_notebooks.py notebooks/demo<N>_*.ipynb --selfcheck`
   - Outputs cleared
   - Cell count matches SPEC
5. Update `plans/DEMOS.md`
6. Hand off: "Notebook done. Next: `/build-space <N>`."

---

## Checklist (complete before marking done)

- [ ] Cell count and order match SPEC exactly
- [ ] Cell 0 has title, purpose, how to run, "Synthetic data, toy model for teaching", and
      the instructor checklist
- [ ] Install cell pins gradio to the version in `plans/DECISIONS.md`
- [ ] `GRADIO_ANALYTICS_ENABLED=False` set before `import gradio`
- [ ] Only gradio, pandas, numpy, plotly + stdlib imported
- [ ] Pure logic cells import nothing from gradio
- [ ] Self-check prints `All Demo <N> checks passed` locally
- [ ] Every handler under 300 ms of compute (timed in the self-check)
- [ ] `header_html` and theme identical to Demo 3 (Demo 1 and 2)
- [ ] Shared state only where SPEC allows, behind a lock
- [ ] Every status colour has a word
- [ ] No real client, company or person names
- [ ] ADMIN_KEY never printed (Demo 1)
- [ ] Launch cell exact, with the 72-hour reminder
- [ ] Instructor notes cell matches SPEC's flow and minutes
- [ ] AI-tells scan clean (no em dashes, en dashes, Unicode multiplication, bare ---)
- [ ] Outputs cleared
- [ ] Validation passes

---

## Update plans/DEMOS.md on Completion

1. Read `plans/DEMOS.md`
2. Set this demo's notebook status: `in_progress` when starting, `done` when validated
3. Tick the acceptance checks the self-check proves (`[ ]` -> `[x]`); leave the click-through
   ones for the user

Use Edit, not Write.

---

## Notebook Edit Protocol (MANDATORY)

Before any cell edit, insert or delete, follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`:

- Normalize cell ids first (`nbformat.normalize`)
- `NotebookEdit` only if the notebook fits the Read limit (~25k tokens); otherwise a targeted,
  audited in-place JSON edit
- Locate every cell by id AND by asserting its current content
- Control insert position explicitly
- After every edit: read back from disk and assert the cell content
- Run the structural gate (`nbformat.validate`) and the static code gate (`ast.parse` +
  `pyflakes` on all code cells concatenated in order)

Blind bulk scripts that rewrite cells by index are forbidden.
