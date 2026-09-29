"""Rollout simulator (Demo 3). Generated from notebooks/demo3_rollout.ipynb, do not edit."""

# From notebook cell 2
# Imports and config: the controls, presets and model constants every later cell uses
import os

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"  # a public demo sends no telemetry

import time

import gradio as gr
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

N_TEAMS = 100  # teams per division
MONTHS = 12    # length of the rollout

# Control values, in the order the UI passes them to every handler
DEFAULTS = dict(quality=0.5, deadline=4, pilots=3, champion=0.5, sunset_on=True, sunset=9)
CONTROL_KEYS = list(DEFAULTS)

PRESETS = {
    "Default": dict(DEFAULTS),
    "Bad v1": {**DEFAULTS, "quality": 0.2},
    "Great v1": {**DEFAULTS, "quality": 0.9},
    "Impatient mandate": {**DEFAULTS, "deadline": 2},
}

# Model constants: starting points for teaching, not calibrated numbers
WORKAROUND_A = 0.8      # how much of a weak v1 that A's teams bypass underneath
WORKAROUND_BC = 0.1     # teams who chose the path rarely bypass it
WOM = 0.6               # word of mouth strength
BASE_P = 0.005          # teams that try anything new on their own
PRESSURE_BASE = 0.1     # C's extra pull once controls are mandated
PRESSURE_QUALITY = 0.2  # a better v1 is the cheapest way to prove your controls
SUNSET_SHARE = 0.5      # share of the remaining teams that move each month after the sunset

# Divisions differ by colour, dash style and label, never by colour alone
DIVISION_STYLE = {
    "A": dict(colour="#bc4c00", dash="dash", label="A: mandate the tool"),
    "B": dict(colour="#0969da", dash="dot", label="B: pave the path"),
    "C": dict(colour="#8250df", dash="solid", label="C: mandate the outcome, pave the path"),
}


# From notebook cell 3
# The model: pure numpy and pandas, one row per month, no gradio in this cell


def mandate_tool(quality: float, deadline: int) -> tuple[np.ndarray, np.ndarray]:
    """Division A: adoption follows the ordered ramp. Quality only decides how much is bypassed."""
    months = np.arange(MONTHS + 1)
    adopt = np.minimum(1.0, months / deadline)
    work = adopt * (1 - quality) * WORKAROUND_A
    return adopt, work


def pave_path(
    quality: float, deadline: int, pilots: int, champion: float,
    sunset_on: bool, sunset: int, controls_pressure: bool,
) -> np.ndarray:
    """Divisions B and C: discrete Bass diffusion. C adds pressure once controls are mandated."""
    p = BASE_P + pilots / N_TEAMS        # early adopters, lifted by pilot teams
    q = WOM * champion * quality         # word of mouth only spreads if v1 is good
    pressure = PRESSURE_BASE + PRESSURE_QUALITY * quality
    adopt = np.zeros(MONTHS + 1)
    for t in range(1, MONTHS + 1):
        prev = adopt[t - 1]
        rate = p + q * prev
        if controls_pressure and t >= deadline:
            rate += pressure
        now = prev + min(1.0, rate) * (1 - prev)
        if sunset_on and t >= sunset:
            now += SUNSET_SHARE * (1 - now)  # the old path is closing: half the rest move
        adopt[t] = now
    return adopt


def simulate(
    quality: float, deadline: int, pilots: int, champion: float, sunset_on: bool, sunset: int,
) -> pd.DataFrame:
    """Every share for every division, months 0 to 12. A pure function of the controls."""
    deadline, pilots, sunset = int(deadline), int(pilots), int(sunset)
    adopt_a, work_a = mandate_tool(quality, deadline)
    shared = (quality, deadline, pilots, champion, bool(sunset_on), sunset)
    adopt = {
        "A": adopt_a,
        "B": pave_path(*shared, controls_pressure=False),
        "C": pave_path(*shared, controls_pressure=True),
    }
    work = {
        "A": work_a,
        "B": adopt["B"] * (1 - quality) * WORKAROUND_BC,
        "C": adopt["C"] * (1 - quality) * WORKAROUND_BC,
    }
    months = pd.RangeIndex(MONTHS + 1, name="month")
    df = pd.DataFrame(index=months)
    for div in "ABC":
        df[f"adopt_{div}"] = adopt[div]
        df[f"work_{div}"] = work[div]
        df[f"real_{div}"] = adopt[div] - work[div]
        if div != "A":
            df[f"offpath_{div}"] = 1 - adopt[div]
    shares = df.columns
    df[shares] = df[shares].clip(0.0, 1.0)
    df["controls_mandated"] = months >= deadline
    return df


# From notebook cell 4
# KPIs and the readout sentence: pure functions over the simulated months


def pct(share: float) -> int:
    """A share as a whole-number percentage."""
    return int(round(100 * float(share)))


def off_path_status(division: str, month: int, deadline: int) -> str:
    """What we know about the teams not on the new pipeline."""
    if division == "A":
        return "none on paper"
    if division == "C" and month >= deadline:
        return "proving own controls"
    return "compliance unknown"


def kpis_at(df: pd.DataFrame, month: int, deadline: int) -> pd.DataFrame:
    """Adoption, real use, hidden gaps and off-path teams per division at one month."""
    row = df.loc[month]
    rows = {}
    for div in "ABC":
        rows[div] = {
            "Adoption": pct(row[f"adopt_{div}"]),
            "Real use": pct(row[f"real_{div}"]),
            "Hidden gaps": pct(row[f"work_{div}"]),
            "Off-path teams": pct(1 - row[f"adopt_{div}"]),
            "Off-path status": off_path_status(div, month, int(deadline)),
        }
    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("Division")


def readout(df: pd.DataFrame, month: int = 6) -> str:
    """One sentence built from the numbers, the line the instructor reads out."""
    row = df.loc[month]
    deadline = int(df.index[df["controls_mandated"]][0])
    a, gaps = pct(row["adopt_A"]), pct(row["work_A"])
    b, c = pct(row["adopt_B"]), pct(row["adopt_C"])
    if month >= deadline:
        c_clause = f"C has {c}% on the path and the rest proving their own controls."
    else:
        c_clause = f"C has {c}% on the path, and controls apply from month {deadline}."
    return (
        f"Month {month}: A reports {a}% but {gaps}% of teams are working around it. "
        f"B has {b}% on the path, the rest unknown. {c_clause}"
    )


# From notebook cell 5
# Charts: pure plotly functions that return figures, one per output panel

CHART_HEIGHT = 380
MONTH_AXIS = dict(title="Month", dtick=1, range=[0, MONTHS])
SHARE_AXIS = dict(range=[0, 100], ticksuffix="%")


def style_figure(fig: go.Figure, title: str) -> go.Figure:
    """Shared look: height, title with the "Toy model" subtitle, legend under the plot."""
    fig.update_layout(
        height=CHART_HEIGHT,
        title=dict(text=title, subtitle=dict(text="Toy model")),
        legend=dict(orientation="h", yanchor="top", y=-0.2, x=0),
        margin=dict(l=50, r=20, t=70, b=40),
        hovermode="x unified",
    )
    return fig


def fig_adoption(df: pd.DataFrame, deadline: int, sunset_on: bool, sunset: int) -> go.Figure:
    """Adoption for A, B and C, with markers at the deadline and the sunset month."""
    fig = go.Figure()
    for div, style in DIVISION_STYLE.items():
        fig.add_trace(go.Scatter(
            x=df.index, y=100 * df[f"adopt_{div}"], name=style["label"], mode="lines+markers",
            line=dict(color=style["colour"], dash=style["dash"], width=3),
        ))
    fig.add_vline(x=deadline, line_dash="dash", line_color="#6e7781",
                  annotation_text="Deadline", annotation_position="top left")
    if sunset_on:
        fig.add_vline(x=sunset, line_dash="dot", line_color="#6e7781",
                      annotation_text="Sunset", annotation_position="top right")
    fig.update_xaxes(**MONTH_AXIS)
    fig.update_yaxes(title="Teams on the new pipeline", **SHARE_AXIS)
    return style_figure(fig, "Adoption over 12 months")


def area(x: pd.Index, share: pd.Series, name: str, colour: str, group: str) -> go.Scatter:
    """One band of a stacked area chart, in percent."""
    return go.Scatter(x=x, y=100 * share, name=name, mode="lines", stackgroup=group,
                      line=dict(color=colour, width=1), fillcolor=colour)


def fig_split(df: pd.DataFrame) -> go.Figure:
    """Left: A's real use vs workarounds. Right: C on the path vs off it."""
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=(
        DIVISION_STYLE["A"]["label"], DIVISION_STYLE["C"]["label"]))
    x, mandated = df.index, df["controls_mandated"]
    fig.add_trace(area(x, df["real_A"], "A: real use", "#1a7f37", "a"), row=1, col=1)
    fig.add_trace(area(x, df["work_A"], "A: workarounds", "#cf222e", "a"), row=1, col=1)
    before = df["offpath_C"].where(~mandated, 0.0)
    after = df["offpath_C"].where(mandated, 0.0)
    fig.add_trace(area(x, df["adopt_C"], "C: on the path", "#8250df", "c"), row=1, col=2)
    fig.add_trace(area(x, before, "C: off the path", "#afb8c1", "c"), row=1, col=2)
    fig.add_trace(area(x, after, "C: off the path, proving controls", "#d4a72c", "c"), row=1, col=2)
    fig.update_xaxes(**MONTH_AXIS)
    fig.update_yaxes(**SHARE_AXIS)
    fig.update_yaxes(title="Share of teams", row=1, col=1)
    return style_figure(fig, "What the numbers hide")


# From notebook cell 6
# Self-checks: plain asserts that prove SPEC's acceptance checks before the app launches


def at_month(key: str, month: int, **changes) -> float:
    """One share at one month, with some controls changed from DEFAULTS."""
    return float(simulate(**{**DEFAULTS, **changes}).loc[month, key])


# Quality never moves A's adoption line, only its workaround split
runs = [simulate(**{**DEFAULTS, "quality": q}) for q in (0.1, 0.5, 0.9)]
assert all(np.array_equal(runs[0]["adopt_A"], r["adopt_A"]) for r in runs)
assert (runs[0]["work_A"] >= runs[1]["work_A"]).all() and (runs[1]["work_A"] >= runs[2]["work_A"]).all()
assert runs[0].loc[6, "work_A"] > runs[1].loc[6, "work_A"] > runs[2].loc[6, "work_A"]

# More pilots, or a stronger champion effect, lifts B and C at month 6
for div in "BC":
    assert at_month(f"adopt_{div}", 6, pilots=6) > at_month(f"adopt_{div}", 6)
    assert at_month(f"adopt_{div}", 6, champion=0.9) > at_month(f"adopt_{div}", 6)

# Over 200 random settings: C equals B before the deadline and is at or above it after
rng = np.random.default_rng(3)
for _ in range(200):
    controls = dict(
        quality=rng.uniform(0, 1), deadline=int(rng.integers(2, 13)), pilots=int(rng.integers(0, 11)),
        champion=rng.uniform(0, 1), sunset_on=bool(rng.integers(0, 2)), sunset=int(rng.integers(6, 13)),
    )
    df = simulate(**controls)
    before, after = df.index < controls["deadline"], df.index >= controls["deadline"]
    assert np.allclose(df.loc[before, "adopt_C"], df.loc[before, "adopt_B"], atol=1e-9)
    assert (df.loc[after, "adopt_C"] >= df.loc[after, "adopt_B"] - 1e-9).all()
    shares = df.drop(columns="controls_mandated")
    assert ((shares >= 0) & (shares <= 1)).all().all(), controls
    on_path = shares.filter(regex="^(adopt|work|real)_")  # off-path is 1 - adopt, so 100% at month 0
    assert (on_path.loc[0] == 0).all() and not df.loc[0, "controls_mandated"]

# Every preset sets every control
assert all(set(p) == set(DEFAULTS) for p in PRESETS.values())

# The readout switches its C clause at the deadline
assert "proving their own controls" in readout(simulate(**DEFAULTS), 6)
assert "controls apply from month 8" in readout(simulate(**{**DEFAULTS, "deadline": 8}), 6)

# A full recompute (model, KPIs, readout, both figures) stays well under 300 ms
start = time.perf_counter()
for _ in range(50):
    df = simulate(**DEFAULTS)
    kpis_at(df, 6, DEFAULTS["deadline"]), kpis_at(df, 12, DEFAULTS["deadline"]), readout(df, 6)
    fig_adoption(df, DEFAULTS["deadline"], DEFAULTS["sunset_on"], DEFAULTS["sunset"]), fig_split(df)
per_run_ms = 1000 * (time.perf_counter() - start) / 50
assert per_run_ms < 300, per_run_ms
print(f"Recompute: {per_run_ms:.1f} ms per run")
print("All Demo 3 checks passed")


# From notebook cell 7
# UI helpers: the shared theme and header (copied into Demos 1 and 2), plus Demo 3's panels
THEME = gr.themes.Soft()

STATUS_COLOURS = {
    "PASS": "#1a7f37", "LIVE": "#1a7f37", "UP": "#1a7f37",
    "FAIL": "#cf222e", "BLOCKED": "#cf222e", "DOWN": "#cf222e",
    "PENDING": "#6e7781", "SAME": "#6e7781",
    "RUNNING": "#0969da",
}


def header_html(title: str, purpose: str) -> str:
    """Page header: title, one-line purpose and the synthetic-data banner."""
    return f"""
<div style="padding:14px 18px;border-radius:10px;background:#f6f8fa;border:1px solid #d0d7de;margin-bottom:8px">
  <div style="font-size:1.6em;font-weight:700;color:#1f2328">{title}</div>
  <div style="font-size:1.05em;color:#424a53;margin-top:4px">{purpose}</div>
  <div style="display:inline-block;margin-top:8px;padding:3px 10px;border-radius:999px;background:#fff8c5;border:1px solid #d4a72c;color:#633c01;font-size:0.9em">
    Synthetic data, toy model for teaching. Nothing here touches real systems.
  </div>
</div>
"""


def badge(status: str) -> str:
    """A coloured pill that always carries the status word."""
    colour = STATUS_COLOURS.get(status, "#6e7781")
    return (
        f'<span style="display:inline-block;padding:2px 10px;border-radius:999px;'
        f'background:{colour};color:#ffffff;font-weight:600;font-size:0.85em">{status}</span>'
    )


def readout_html(sentence: str) -> str:
    """The readout sentence in large text, so the back of the room can read it."""
    return f'<div style="font-size:1.3em;font-weight:600;line-height:1.4;padding:6px 2px">{sentence}</div>'


def kpi_table(kpis: pd.DataFrame) -> pd.DataFrame:
    """KPI rows with division labels and percent signs, ready for gr.Dataframe."""
    table = kpis.copy()
    for col in ("Adoption", "Real use", "Hidden gaps", "Off-path teams"):
        table[col] = table[col].map(lambda v: f"{v}%")
    table.index = [DIVISION_STYLE[div]["label"].split(":")[0] for div in table.index]
    return table.rename_axis("Division").reset_index()


def compliance_html(kpis_6: pd.DataFrame, kpis_12: pd.DataFrame) -> str:
    """SPEC's compliance picture with the month 6 and month 12 numbers filled in."""
    def cell(div: str, col: str) -> str:
        return f"{kpis_6.loc[div, col]}% at month 6, {kpis_12.loc[div, col]}% at month 12"

    gaps = {
        "A": f"Workarounds: on paper, bypassing underneath ({cell('A', 'Hidden gaps')})",
        "B": f"Small ({cell('B', 'Hidden gaps')})",
        "C": f"Small ({cell('C', 'Hidden gaps')})",
    }
    off = {
        "A": f"None on paper ({cell('A', 'Off-path teams')})",
        "B": f"Teams not yet on it, compliance unknown ({cell('B', 'Off-path teams')})",
        "C": f"Teams not on it, proving their controls themselves from the deadline ({cell('C', 'Off-path teams')})",
    }
    td = 'style="padding:6px 10px;border:1px solid #d0d7de;vertical-align:top"'
    head = "".join(f"<th {td}>{DIVISION_STYLE[d]['label']}</th>" for d in "ABC")
    rows = "".join(
        f"<tr><th {td}>{name}</th>" + "".join(f"<td {td}>{data[d]}</td>" for d in "ABC") + "</tr>"
        for name, data in (("Hidden gaps", gaps), ("Off-path teams", off))
    )
    return (
        '<div style="font-weight:700;margin:8px 0 4px">Compliance picture</div>'
        f'<table style="border-collapse:collapse;width:100%"><tr><th {td}></th>{head}</tr>{rows}</table>'
    )


def preset_values(name: str) -> tuple:
    """A preset's control values, in the order the UI expects (CONTROL_KEYS)."""
    preset = PRESETS[name]
    return tuple(preset[key] for key in CONTROL_KEYS)


# From notebook cell 8
# Layout and wiring: controls on the left, every output on the right, one update function


def update(
    quality: float, deadline: int, pilots: int, champion: float, sunset_on: bool, sunset: int,
) -> tuple:
    """Recompute every output from the controls. Stateless, so visitors never see each other."""
    df = simulate(quality, deadline, pilots, champion, sunset_on, sunset)
    kpis_6, kpis_12 = kpis_at(df, 6, deadline), kpis_at(df, 12, deadline)
    return (
        readout_html(readout(df, 6)),
        fig_adoption(df, deadline, sunset_on, sunset),
        fig_split(df),
        kpi_table(kpis_6),
        kpi_table(kpis_12),
        compliance_html(kpis_6, kpis_12),
    )


def toggle_sunset(sunset_on: bool) -> dict:
    """The sunset month slider only works while the sunset checkbox is on."""
    return gr.update(interactive=sunset_on)


def apply_preset(name: str) -> tuple:
    """Set every control from a preset. The sunset slider comes last in CONTROL_KEYS."""
    *values, sunset = preset_values(name)
    sunset_on = values[CONTROL_KEYS.index("sunset_on")]
    return (*values, gr.update(value=sunset, interactive=sunset_on))


with gr.Blocks(title="Rollout simulator") as demo:
    gr.HTML(header_html("Rollout simulator", "Toy model to make the argument visible, not a forecast."))
    with gr.Row():
        with gr.Column(scale=1):
            quality = gr.Slider(0, 1, step=0.05, value=DEFAULTS["quality"],
                                label="v1 platform quality")
            deadline = gr.Slider(2, 12, step=1, value=DEFAULTS["deadline"],
                                 label="Mandate deadline (month)")
            pilots = gr.Slider(0, 10, step=1, value=DEFAULTS["pilots"],
                               label="Pilot teams")
            champion = gr.Slider(0, 1, step=0.05, value=DEFAULTS["champion"],
                                 label="Champion effect")
            sunset_on = gr.Checkbox(value=DEFAULTS["sunset_on"], label="Sunset the old path")
            sunset = gr.Slider(6, 12, step=1, value=DEFAULTS["sunset"],
                               label="Sunset month for the old path",
                               interactive=DEFAULTS["sunset_on"])
            gr.Markdown("**Presets**")
            preset_buttons = [gr.Button(name, size="sm") for name in PRESETS]
        with gr.Column(scale=2):
            readout_box = gr.HTML()
            adoption_plot = gr.Plot(label="Adoption")
            split_plot = gr.Plot(label="Real use vs hidden gaps")
            with gr.Row():
                kpi_6 = gr.Dataframe(label="Month 6", interactive=False)
                kpi_12 = gr.Dataframe(label="Month 12", interactive=False)
            compliance_box = gr.HTML()

    controls = [quality, deadline, pilots, champion, sunset_on, sunset]
    outputs = [readout_box, adoption_plot, split_plot, kpi_6, kpi_12, compliance_box]

    # .release fires once when the slider is let go, so dragging does not flood the queue
    for slider in (quality, deadline, pilots, champion, sunset):
        slider.release(update, inputs=controls, outputs=outputs)
    # .input fires on a user click only, not when a preset sets the checkbox
    sunset_on.input(toggle_sunset, inputs=sunset_on, outputs=sunset).then(update, inputs=controls, outputs=outputs)
    # A button passed as an input hands the handler its own label, the preset name
    for button in preset_buttons:
        button.click(apply_preset, inputs=button, outputs=controls).then(update, inputs=controls, outputs=outputs)
    demo.load(update, inputs=controls, outputs=outputs)


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=64).launch(theme=THEME)
