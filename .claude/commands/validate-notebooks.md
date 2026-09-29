---
description: Validate the demo notebooks and Spaces folders (syntax, SPEC shape, stack, safety, self-check, parity, AI-tells)
---

# Validate Notebooks

Validate one notebook, or all three: $ARGUMENTS

(Argument: a notebook path, a demo number, or nothing for all three.)

## What This Checks

`validate_notebooks.py` at the repo root runs these. Each failure prints the cell number.

### SPEC shape
- Cell count and cell types match SPEC (demo1 12, demo2 13, demo3 11)
- Cell 0 is markdown with the title and the "Synthetic data" line
- Cell 1 is the install cell and pins gradio
- Every code cell starts with a comment saying what it does
- Self-check cell ends with `print("All Demo N checks passed")`
- Launch cell uses `demo.queue(default_concurrency_limit=64).launch(share=True`
- Outputs cleared

### Stack
- Imports only from stdlib, gradio, pandas, numpy, plotly (and `google.colab` inside try)
- No PyYAML
- `GRADIO_ANALYTICS_ENABLED` set before the first `import gradio`
- Gradio pin identical in the notebook, `spaces/<demo>/requirements.txt` and README
  `sdk_version`

### Safety (public links)
- No network: flags `requests`, `urllib`, `httpx`, `socket`, `http.client`, `aiohttp`
- No `gr.File` / `gr.UploadButton` / uploads
- ADMIN_KEY never printed or returned to the UI
- No real names: a denylist of client and company names (edit `DENYLIST` in the script)

### Code
- Python syntax per code cell (IPython lines stripped)
- pyflakes over all code cells concatenated in order (catches forward references)

### Copy
- AI-tells: em dash, en dash, Unicode multiplication, bare `---` in markdown

### Optional modes
- `--selfcheck`: executes the code cells from imports up to and including the self-check
  cell in a subprocess with `.venv/bin/python3`, and requires the PASS line. This is SPEC's
  "run the logic locally and show me the self-check output"
- `--parity`: compares `spaces/<demo>/app.py` with the notebook cells it should come from

## Usage

```bash
.venv/bin/python3 validate_notebooks.py notebooks/demo3_rollout.ipynb
.venv/bin/python3 validate_notebooks.py notebooks/demo3_rollout.ipynb --selfcheck
.venv/bin/python3 validate_notebooks.py notebooks/demo3_rollout.ipynb --parity
.venv/bin/python3 validate_notebooks.py --all --selfcheck --parity
```

## CRITICAL: Cell Order Verification

Before fixing anything, print each cell's `id` and first line to confirm order. Only then
edit, following `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`.

## Pass Criteria

- All checks above pass
- `--selfcheck` prints the PASS line for each built demo
- `--parity` passes for each built Spaces folder

## What It Cannot Check (click-through, the user does these)

- Two browsers see each other's room catalog entries within 5 s (Demo 1)
- Two browsers never see each other's form, game or results
- share=True link opens in a private window without a Google login
- Layout usable at 1280x720 in a shared Teams screen and on a phone

List these as unchecked in the report.

## When to Run

- After every 5-cell batch during `/build-notebook`
- After `/build-space`
- Before the webinar, after a Run all in Colab

## See Also

- `validate_notebooks.py`
- `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`
