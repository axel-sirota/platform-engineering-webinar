# Platform Engineering Foundations: webinar demos

Three small Gradio apps used live in a 2 hour platform engineering webinar. Each one is a
self-contained Colab notebook: open it, Runtime > Run all, and the last cell prints a public
link. Synthetic data, toy models for teaching. Nothing here touches real systems.

| Demo | What it shows | Open |
|---|---|---|
| 1. Golden path portal | Get a service without a ticket, with policy checks inside the path and a shared room catalog | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/axel-sirota/platform-engineering-webinar/blob/main/notebooks/demo1_portal.ipynb) |
| 2. Platform team funding game | Headline adoption hides the story; peel the layers, then fund one bet per quarter | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/axel-sirota/platform-engineering-webinar/blob/main/notebooks/demo2_funding_game.ipynb) |
| 3. Rollout simulator | Mandate the tool, pave the path, or mandate the outcome and pave the path | [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/axel-sirota/platform-engineering-webinar/blob/main/notebooks/demo3_rollout.ipynb) |

## Layout

| Path | Contents |
|---|---|
| `notebooks/` | The three Colab notebooks |
| `spaces/` | The same apps as Hugging Face Spaces folders (`app.py`, `requirements.txt`, `README.md`) |
| `validate_notebooks.py` | Checks shape, stack, safety and self-checks; `--selfcheck --parity` |

## Run locally

```bash
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
.venv/bin/python3 spaces/demo3_rollout/app.py
```

Stack: Gradio 6.29.0, pandas, numpy, plotly. Demo 1's "Reset room" needs an `ADMIN_KEY`
environment variable.
