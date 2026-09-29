---
description: Build the Hugging Face Spaces backup folder for one demo from its finished notebook
---

Build Spaces folder for demo: $ARGUMENTS

(Argument is a demo number, 1 to 3. Required.)

## GUARD

```bash
ls plans/DECISIONS.md notebooks/demo$ARGUMENTS_*.ipynb 2>/dev/null
```

- No `plans/DECISIONS.md`: stop, "Run `/init-webinar` first."
- No notebook: stop, "Run `/build-notebook <N>` first."
- Notebook not marked `done` in `plans/DEMOS.md`: ask before continuing.

---

## Demo Map

| N | Notebook | Folder | Cells concatenated |
|---|---|---|---|
| 1 | notebooks/demo1_portal.ipynb | spaces/demo1_portal/ | 2 to 9 |
| 2 | notebooks/demo2_funding_game.ipynb | spaces/demo2_funding_game/ | 2 to 10 |
| 3 | notebooks/demo3_rollout.ipynb | spaces/demo3_rollout/ | 2 to 8 |

The notebook is the source. `app.py` is generated from it, never edited by hand. If the app
needs a change, change the notebook and rebuild.

---

## Step 1: Read

1. `plans/DECISIONS.md` (Gradio pin, Space names)
2. SPEC (`imp_docs/demos.md`): the demo's "SPACES FOLDER" block
3. The notebook cell map (print it with the snippet in `build-notebook.md`)

## Step 2: Generate app.py

Write a small script to the scratchpad, not the repo, that:

1. Loads the notebook with `json`
2. Takes the code cells in the range above, in order
3. Drops IPython lines (`%pip`, `!`)
4. For Demo 1, swaps the ADMIN_KEY lookup for `ADMIN_KEY = os.environ.get("ADMIN_KEY", "")`
   (no Colab userdata, no getpass). An empty key means reset is disabled
5. Joins cells with two blank lines, each preceded by a `# From notebook cell K` comment
6. Appends:
   ```python
   if __name__ == "__main__":
       demo.queue(default_concurrency_limit=64).launch(theme=THEME)
   ```
7. Writes `spaces/demo<N>_<name>/app.py`

Show the script in chat before running it. Run it with `.venv/bin/python3`.

## Step 3: requirements.txt

```
gradio==<pin>
pandas
numpy
plotly        # Demo 2 and 3 only
```

## Step 4: README.md

```markdown
---
title: <Space title>
emoji: <one emoji>
colorFrom: blue
colorTo: gray
sdk: gradio
sdk_version: <pin>
app_file: app.py
pinned: false
---

<One line: what the demo shows.> Synthetic data, toy model for teaching.
```

Demo 1 adds two lines: ADMIN_KEY must be set as a Space secret; without it, "Reset room"
does nothing.

## Step 4b: Refresh the notebook's optional deploy cell

The notebook has one code cell between the launch cell and the instructor notes (demo1
cell 11, demo2 cell 12, demo3 cell 10) that deploys to Spaces from Colab. Its template is in
`plans/DECISIONS.md` under "Optional deploy cell".

1. Assert `'''` does not occur in app.py (it would break the raw string)
2. Render the template with APP_PY, REQUIREMENTS_TXT and README_MD set to the exact text
   of the three files just written, SPACE_ID set to `your-username/<Space name from
   DECISIONS.md>`, and for Demo 1 the add_space_secret line uncommented
3. If the cell does not exist yet, insert it after the launch cell; if it exists, replace it.
   Follow the Notebook Edit Protocol (locate by id + content, read back, assert)
4. Outputs stay cleared

## Step 5: Verify

1. `.venv/bin/python3 -m pyflakes spaces/demo<N>_<name>/app.py`
2. `.venv/bin/python3 validate_notebooks.py notebooks/demo<N>_*.ipynb --parity`
3. Import smoke: `.venv/bin/python3 -c "import runpy; runpy.run_path('spaces/demo<N>_<name>/app.py', run_name='not_main')"`
   must build `demo` without launching
4. Optional local launch on request only (`/run`), then open http://127.0.0.1:7860

## Step 6: Update plans/DEMOS.md

Set this demo's Spaces status to `built`. Pushing to Hugging Face is the user's job; do not
run `git push` or `huggingface-cli upload`.

## Report

| File | Status |
|---|---|
| app.py | written, pyflakes clean, parity OK |
| requirements.txt | pin matches notebook |
| README.md | sdk_version matches pin |
