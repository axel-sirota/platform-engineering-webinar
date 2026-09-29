---
description: Initialize plans/DECISIONS.md by asking only the questions imp_docs/demos.md leaves open
---

Initialize the webinar manifest: $ARGUMENTS

This command creates `plans/DECISIONS.md`, the single source of truth every other command
reads before doing any work. Run it once at the start, or when webinar details change.

Read these first. They already lock most decisions, so do not re-ask anything they answer:

1. `CLAUDE.md`
2. `imp_docs/demos.md` (the build spec, called SPEC below; it wins on any conflict)
3. `imp_docs/outline.md` (the course as scoped for the client)

---

## Guard

If `plans/DECISIONS.md` already exists, read it, show the current contents, then ask:
"Do you want to update specific sections, or start fresh?"
If updating: only re-ask the sections the user wants to change.
If starting fresh: run the full interview below.

---

## Process: One Question at a Time

Ask each question individually. Wait for the answer before asking the next one.
After each answer, confirm you understood it before moving on.
Keep a running draft. After the last question, show the full draft and ask for approval
before writing the file.

---

## Questions (ask in this order)

**Block 1: Environment**

Q1: "Which Gradio version do we pin? I can research the latest stable and check `gr.Timer`,
`.release` on sliders, and `queue(default_concurrency_limit=...)` against it, or you give me a
version you already tested in Colab."

Q2: "Python version for the local `.venv` used to run the self-checks? Colab currently ships
3.11 or 3.12; I suggest matching it."

Q3: "Hugging Face Spaces: which account or org, and what Space names for the three backups?"

**Block 2: Look and copy**

Q4: "UK or US spelling in all user-visible text? SPEC already uses 'colour' and 'sanitised'."

Q5: "Theme: SPEC says `gr.themes.Soft()` on all three. Any brand colour or font to add, or keep
it stock?"

**Block 3: Delivery**

Q6: "Slide numbers the instructor notes should reference, per demo? SPEC mentions slides 26
and 28 for Demo 3. Is the slide plan final?"

Q7: "ADMIN_KEY: do you want a default for local runs, or always prompt?"

**Block 4: Anything else**

Q8: "Anything about how the 2 hours should run that SPEC does not capture: pacing, what makes
a demo land, the one thing attendees must leave with?"

---

## After All Answers: Write the File

Show the complete draft in chat and ask for approval. Once approved, write
`plans/DECISIONS.md`:

```markdown
# Webinar Manifest: Platform Engineering Foundations
# Client webinar, 2 hours, 3 Gradio demos
# Last updated: <YYYY-MM-DD>
#
# Read by every command before any work begins. Update it with /init-webinar.
# Source of truth for the demos themselves: imp_docs/demos.md.

## Environment

- **Gradio pin**: <version>
- **Local Python**: <version>
- **Spaces account / names**: <demo1>, <demo2>, <demo3>

## Look and copy

- **Spelling**: <UK / US>
- **Theme**: <gr.themes.Soft() stock / additions>

## Delivery

- **Slide references for instructor notes**: <per demo>
- **ADMIN_KEY for local runs**: <default / prompt>
- **Notes**: <answer to Q8>

## Key Decisions (locked by SPEC and CLAUDE.md)

- Three notebooks: notebooks/demo1_portal.ipynb (12 cells), notebooks/demo2_funding_game.ipynb
  (13 cells), notebooks/demo3_rollout.ipynb (11 cells). Exact cell lists in SPEC
- Three Spaces folders under spaces/, built from the same code, launching without share=True
- Build order: Demo 3, then Demo 1, then Demo 2. header_html and theme written in Demo 3 are
  copied verbatim into Demos 1 and 2
- Stack: Python 3.11+, gradio (pinned), pandas, numpy, plotly. Nothing else. No PyYAML
- No network calls, no uploads, GRADIO_ANALYTICS_ENABLED=False before importing gradio
- Synthetic data only, seeded RNG, fictional names. No real client, company or person names
- Per-visitor state in gr.State. Only the Demo 1 room catalog and Demo 2 bet tally are shared,
  behind threading.Lock
- Every interaction under 300 ms of compute, demo.queue(default_concurrency_limit=64)
- Status colours always paired with a word (PASS, FAIL, PENDING, RUNNING, LIVE, BLOCKED, UP,
  DOWN, SAME)
- Each notebook runs top to bottom on a free Colab CPU runtime in under 60 s
- Self-check cell with plain asserts, ending in print("All Demo N checks passed")
- Notebooks handed over with outputs cleared
- Code is shown on a projector: short functions, docstrings, type hints, a comment at the
  top of each cell
- No em dashes, no en dashes, no bare --- separators in any cell
```

---

## Confirm

After writing, say:

> `plans/DECISIONS.md` written.
>
> Every command now reads this file first. Run `/start-session` to see progress, or
> `/research-demo 3` to begin with Demo 3.

---

## Notebook Edit Protocol (awareness)

If this command ends up editing notebook cells (it should not), follow
`~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`: normalize cell ids, size-gate the mechanism, locate
cells by id + content, read back and assert after every edit, run the structural + static code
gates. Blind bulk index-based rewrites are forbidden.
