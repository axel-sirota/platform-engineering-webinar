---
description: Research one Gradio demo and produce a cell-by-cell plan at plans/demoN_plan.md that /build-notebook can consume directly
---

Research and plan demo: $ARGUMENTS

(Argument is a demo number, 1 to 3. See the table below.)

## GUARD: Read the Manifest First

```bash
ls plans/DECISIONS.md 2>/dev/null
```

If it does NOT exist, stop and say:

> `plans/DECISIONS.md` not found. Run `/init-webinar` first. Every command requires it.

If it exists, read it fully along with `CLAUDE.md` and `imp_docs/demos.md` (SPEC).

---

This command is the precursor to `/build-notebook`. Its only job is a plan file at
`plans/demo<N>_plan.md` so `/build-notebook <N>` can build the notebook cell by cell.

**This command does NOT create any `.ipynb` file or any file under `spaces/`.** Markdown only.

SPEC already fixes the cell list for each demo inside its "Claude Code prompt" block. The plan
does not redesign it. The plan turns each cell description into drafted code and markdown,
verified against the pinned Gradio version, and records every place SPEC is ambiguous or wrong.

**Web research is MANDATORY.** Per cycle: hypothesis, evidence, antithesis, refinement.

**Evidence ranking, strongest first:**
1. **Running the code** in `.venv/bin/python3` against the pinned packages. Signatures,
   defaults and failure modes verified empirically beat any document.
2. Official Gradio docs, changelog and source for the exact pinned version.
3. Current third-party writing, treated as a lead to verify.
4. Recall. **Never sufficient on its own.**

If the `Skill` tool is unavailable (subagent context), run the discipline directly and log each
cycle into the plan's `# RESEARCH VALIDATED` block.

## Demo Map

| N | Demo | Notebook | Spaces folder | Cells |
|---|---|---|---|---|
| 1 | Golden path portal with room catalog | notebooks/demo1_portal.ipynb | spaces/demo1_portal/ | 12 |
| 2 | Platform team funding game | notebooks/demo2_funding_game.ipynb | spaces/demo2_funding_game/ | 13 |
| 3 | Rollout simulator, divisions A, B, C | notebooks/demo3_rollout.ipynb | spaces/demo3_rollout/ | 11 |

Build order is 3, 1, 2. Demo 3 defines `header_html` and the theme; Demos 1 and 2 copy them.

## FAILURE DEFINITION

Exactly two outcomes: COMPLETE SUCCESS or COMPLETE FAILURE.

**COMPLETE SUCCESS** = all true:
- All 5 cycles completed and visible in chat, each with hypothesis, logged evidence,
  antithesis, refinement
- PRE-WRITE SELF-CHECK printed with all YES
- Plan written to `plans/demo<N>_plan.md` with every required section
- Every cell's code and markdown drafted in full, not "write something here"

**COMPLETE FAILURE** = any of:
- Fewer than 5 cycles, or a cycle without logged evidence
- Any Gradio API asserted from memory where running it was possible
- Self-check not printed, or any NO at Write time
- Plan with stub content

On failure: report what failed and restart. Do not patch a partial result.

---

## Output Contract (NON-NEGOTIABLE)

1. **One file only**: `plans/demo<N>_plan.md`.
2. **No `.ipynb`, no `spaces/` files.**
3. **Directly executable by `/build-notebook`**: every cell has its full source.
4. **Structure** (every section required):
   - `# Demo <N>: <Title>, Cell-by-Cell Plan`
   - `## What it teaches` (copied from SPEC, one paragraph)
   - `## Slot in the webinar` (minutes from SPEC, what slide comes before and after)
   - `## Acceptance checks` (copied from SPEC, each mapped to the cell and function that
     satisfies it, and the self-check assert that proves it where one can)
   - `## Shared code` (for Demo 1 and 2: `header_html` and theme copied verbatim from the
     built Demo 3 notebook, with the cell it came from)
   - `# CELL-BY-CELL CONTENT (Target: <cells> cells)`
   - Each cell: `## Cell K - Markdown/Code: Description` with full source in a fenced block
   - `## Spaces folder` (what app.py concatenates, requirements.txt, README.md header)
   - `## SPEC DEVIATIONS` (every place the plan departs from SPEC or the prompt, and why;
     "none" if none)
   - `# VERIFICATION CHECKLIST`
   - `# RESEARCH VALIDATED (Month Year)`

If the plan will exceed ~150 lines, write the header first, then append cells in ~50-line
chunks with Edit, then the checklist and research block.

---

## Pre-Work: MANDATORY Reading

1. `CLAUDE.md`
2. `plans/DECISIONS.md`
3. `imp_docs/demos.md`: "Decisions and shared conventions", this demo's section, and this
   demo's "Claude Code prompt" block
4. `imp_docs/outline.md`: which module this demo brings to life
5. `.claude/commands/build-notebook.md`: the consumer of this plan
6. For Demo 1 or 2: the built `notebooks/demo3_rollout.ipynb` (header_html, theme) and any
   other built demo, so shared helpers stay identical

---

## MANDATORY CYCLE TRACKER

Post at the start and update after each cycle. Do NOT write the plan until all 5 are `[x]`
with `evidence logged: YES`.

```
CYCLE TRACKER
[_] Cycle 1 - SPEC alignment and shared code              evidence logged: NO
[_] Cycle 2 - Gradio API surface (pinned version)         evidence logged: NO
[_] Cycle 3 - Pure logic and self-checks                  evidence logged: NO
[_] Cycle 4 - Concurrency, performance, public-link safety evidence logged: NO
[_] Cycle 5 - Projector readability, timing, Spaces       evidence logged: NO
```

---

## Process: 5 TDD-Style Research Cycles

### Cycle 1 - SPEC alignment and shared code
- Map every SPEC acceptance check to a cell and function.
- Diff the prompt block against the demo section of SPEC. List every disagreement; SPEC wins.
- For Demo 1 or 2, extract `header_html` and the theme from the built Demo 3.
- **Invoke `/research`**: how platform teams show this concept (golden paths, adoption
  dashboards, rollout strategies), so the synthetic numbers look plausible to engineers.
- **Refutation**: does any acceptance check have no cell that proves it? Any name that
  collides with another demo's shared helper?

### Cycle 2 - Gradio API surface (pinned version)
Install the pin into `.venv` and verify by running code, not by reading:
- `gr.Blocks(theme=..., title=...)`, `gr.themes.Soft()`
- `gr.State`, `gr.Request.session_hash` inside a handler and inside `demo.load`
- Generator handlers yielding partial updates (Demo 1 stage ticks)
- `gr.Timer(value)` and its `.tick` event (Demo 1 room catalog)
- `.release` on `gr.Slider` (Demo 3), and whether it exists in the pin
- `gr.update(visible=...)` or returning components for visibility (Demo 2 peel)
- `gr.Code(language="yaml")`, `gr.Dataframe`, `gr.Plot` with plotly figures
- `demo.queue(default_concurrency_limit=64).launch(share=True, show_error=True)`
- Spaces README `sdk_version` accepted for the pin
- **Invoke `/research`**: breaking changes in the pinned Gradio major version.
- **Refutation**: any API the prompt names that the pin renamed or removed? Does share=True
  work from Colab with the pin?

### Cycle 3 - Pure logic and self-checks
- Draft every pure function (rules, generators, model, KPIs) and run it locally.
- Draft the self-check cell and run it: it must print `All Demo <N> checks passed`.
- Numbers from SPEC (targets, bet effects, model constants) reproduced within tolerance.
- **Invoke `/research`**: for Demo 3, discrete Bass diffusion formulation; for Demo 2, a
  sanity source on adoption vs satisfaction framing; for Demo 1, policy-as-code examples.
- **Refutation**: would any assert pass for the wrong reason? Does any pure function import
  gradio?

### Cycle 4 - Concurrency, performance, public-link safety
- Time every handler's compute; must be under 300 ms. Record the numbers.
- Shared state only where SPEC allows, behind `threading.Lock`; everything else per visitor.
- Public link: no free text shown to others, no uploads, no network, ADMIN_KEY never printed.
- **Invoke `/research`**: Gradio concurrency with ~100 visitors on one CPU, gr.State isolation,
  share link limits.
- **Refutation**: can two browsers see each other's form or results? Can someone post free
  text to the room? What breaks first at 100 visitors?

### Cycle 5 - Projector readability, timing, Spaces
- Code shown on a projector: short functions, docstrings, type hints, top-of-cell comment.
- Instructor notes cell matches the demo's minutes in SPEC.
- Spaces app.py = notebook cells 2..layout concatenated, no install cell, ADMIN_KEY from
  os.environ only, launch under `if __name__ == "__main__":` without share.
- Produce the VERIFICATION CHECKLIST and the RESEARCH VALIDATED block (URL + fact per source).
- **Refutation**: any unsourced claim? Any cell a 1280x720 shared screen cannot show?

---

## HARD GATE: Pre-Write Self-Check (MANDATORY before any Write)

```
PRE-WRITE SELF-CHECK
--------------------
Cycle tracker all 5 checked [x]:                   YES / NO
All 5 cycles have logged evidence:                 YES / NO
Plan path is plans/demo<N>_plan.md:                YES / NO
No .ipynb or spaces/ files created:                YES / NO
Cell count matches SPEC:                           YES / NO
Every acceptance check mapped to a cell:           YES / NO
Gradio APIs verified by running against the pin:   YES / NO
Self-check cell ran locally and printed PASS line: YES / NO
Every handler timed under 300 ms:                  YES / NO
Shared helpers identical to Demo 3:                YES / NO / N-A
SPEC DEVIATIONS section present:                   YES / NO
Only gradio, pandas, numpy, plotly + stdlib:       YES / NO
No real client, company or person names:           YES / NO
RESEARCH VALIDATED block has URLs:                 YES / NO
AI-tells scan passed (no em/en dashes):            YES / NO
```

---

## Non-Negotiables

1. Path is always `plans/demo<N>_plan.md`.
2. No `.ipynb` or `spaces/` files.
3. SPEC wins over the prompt block; every disagreement is listed.
4. Every Gradio API verified by running it against the pin.
5. Synthetic, fictional data only.
6. ZERO AI-TELLS in the plan: no em dashes, en dashes, Unicode multiplication.

---

## Handoff

> Plan written to `plans/demo<N>_plan.md`.
>
> Next step: run `/build-notebook <N>`, 5 cells at a time with approval between batches.

Do not offer to run `/build-notebook` yourself.
