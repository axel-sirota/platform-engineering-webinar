# CLAUDE.md: Platform Engineering Foundations webinar

Three Gradio demos for a 2 hour client webinar, one Colab notebook each, with Hugging Face
Spaces folders as backup. Not an SDD repo.

## Sources of truth

| File | Role |
|---|---|
| `imp_docs/demos.md` | SPEC. Wins over any plan or prompt block |
| `imp_docs/outline.md` | Course scope: 3 modules, 2 hours |
| `plans/DECISIONS.md` | Webinar manifest (`/init-webinar`) |
| `plans/DEMOS.md` | Status tracker |
| `plans/demoN_plan.md` | Cell-by-cell plan per demo (`/research-demo N`) |

## Layout

```
notebooks/demo1_portal.ipynb        13 cells (SPEC 12 + optional deploy cell)
notebooks/demo2_funding_game.ipynb  14 cells (SPEC 13 + optional deploy cell)
notebooks/demo3_rollout.ipynb       12 cells (SPEC 11 + optional deploy cell)
spaces/demoN_<name>/                app.py, requirements.txt, README.md
diagrams/                           .mmd + .png
validate_notebooks.py               validator
```

## Build order

Demo 3, then Demo 1, then Demo 2. Demo 3 defines `header_html` and the theme; the others copy
them verbatim.

## Command pipeline

`/init-webinar` -> `/research-demo N` -> `/build-notebook N` -> `/build-space N` ->
`/validate-notebooks` -> `/build-diagrams`. Session: `/start-session`, `/read`, `/save-state`,
`/resume`.

## Hard rules (from SPEC)

- Stack: Python 3.11+, gradio (pinned), pandas, numpy, plotly. Nothing else. No PyYAML
- No network, no uploads, `GRADIO_ANALYTICS_ENABLED=False` before importing gradio
- Synthetic, seeded, fictional data. No real client, company or person names
- Per-visitor `gr.State`; shared state only for the Demo 1 room catalog and Demo 2 tally,
  behind `threading.Lock`
- Every interaction under 300 ms of compute; `demo.queue(default_concurrency_limit=64)`
- Status colours always come with a word
- Runs top to bottom on a free Colab CPU in under 60 s; self-check cell prints
  `All Demo N checks passed`
- Projector code: short functions, docstrings, type hints, a comment atop every cell
- Notebooks handed over with outputs cleared; Spaces `app.py` generated from the notebook
- English copy, no AI tells (no em dashes, en dashes, bare `---`)

## Local environment

- `.venv/bin/python3` only; `.venv/bin/python3 -m pip install -r requirements.txt`
- Every new package goes into `requirements.txt`
- Notebook edits follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`
