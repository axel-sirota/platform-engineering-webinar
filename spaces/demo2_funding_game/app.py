"""Demo 2: platform team funding game. Generated from notebooks/demo2_funding_game.ipynb, do not edit."""

# From notebook cell 2
# Imports and config: Division X's Q1 story targets, the four bets and fixed chart colours
import os

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"  # no telemetry from a public link

import copy
import hashlib
import threading
import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import gradio as gr

# Q1 targets for the story, not facts. The generator hits them so the room sees the same picture.
CAPABILITIES: dict[str, dict] = {
    "CI pipelines": {"adoption": 0.85, "mandated_share": 0.75, "csat": 2.4,
                     "workaround_rate": 0.35, "story": "Golden cage"},
    "Databases": {"adoption": 0.60, "mandated_share": 0.0, "csat": 4.1,
                  "workaround_rate": 0.05, "story": "Healthy"},
    "Secrets": {"adoption": 0.30, "mandated_share": 0.0, "csat": 4.3,
                "workaround_rate": 0.02, "story": "Hidden gem"},
    "Preview environments": {"adoption": 0.20, "mandated_share": 0.0, "csat": 2.6,
                             "workaround_rate": 0.15, "story": "Rethink or retire"},
}
CI = "CI pipelines"
N_SERVICES = 120
QUARTERS = 4
BASE_SEED = 42      # same starting data for everyone in the room
NOISE_SD = 0.03     # small per-visitor noise on bet outcomes

# Service timing targets in days: the paved road is faster
LEAD_ON, LEAD_WORKAROUND, LEAD_OFF = 3, 6, 9
ONBOARD_ON, ONBOARD_OFF = 5, 20

# Bet effects are invented for teaching. "add" adds, "mul" multiplies; "*" means every capability.
BETS: dict[str, dict] = {
    "fix_ci": {
        "label": "Fix CI build time and error messages",
        "description": "CI satisfaction +1.0, CI workarounds halve, voluntary CI share +20 pts",
        "lesson": "Fix the cage before you grow.",
        "immediate": [(CI, "csat", "add", 1.0), (CI, "workaround_rate", "mul", 0.5),
                      (CI, "mandated_share", "add", -0.2)],
        "delayed": [],
    },
    "onboard_wave": {
        "label": "Onboard the next wave now",
        "description": "Adoption +15 pts everywhere, satisfaction -0.3 everywhere, workarounds +20%",
        "lesson": "Scaling a weak path spreads the pain.",
        "immediate": [("*", "adoption", "add", 0.15), ("*", "csat", "add", -0.3),
                      ("*", "workaround_rate", "mul", 1.2)],
        "delayed": [],
    },
    "market_secrets": {
        "label": "Market secrets management",
        "description": "Secrets adoption +25 pts, satisfaction steady",
        "lesson": "Hidden gems need marketing, not features.",
        "immediate": [("Secrets", "adoption", "add", 0.25)],
        "delayed": [],
    },
    "preview_v2": {
        "label": "Build preview environments v2",
        "description": "Nothing next quarter, preview satisfaction +0.8 the quarter after, others -0.1",
        "lesson": "New features take time and cost focus.",
        "immediate": [("Databases", "csat", "add", -0.1), ("Secrets", "csat", "add", -0.1),
                      (CI, "csat", "add", -0.1)],
        "delayed": [("Preview environments", "csat", "add", 0.8)],
    },
}

HEALTH_FORMULA_TEXT = (
    "Health index = average of four parts, each scaled 0 to 1: "
    "satisfaction (mean of (csat - 1) / 4), voluntary adoption, "
    "1 - mean workaround rate, and control evidence. A teaching formula, not a real metric."
)

CAP_COLOURS: dict[str, str] = {
    "CI pipelines": "#0969da",
    "Databases": "#1a7f37",
    "Secrets": "#8250df",
    "Preview environments": "#bc4c00",
}


# From notebook cell 3
# The state model (pure): one CapabilityState per capability, one GameState per visitor
@dataclass
class CapabilityState:
    """What the platform team knows about one capability this quarter."""

    adoption: float          # share of services using it, mandated users included
    mandated_share: float    # share of its users who were told to use it
    csat: float              # satisfaction survey, 1 to 5
    workaround_rate: float   # share of its users bypassing it


@dataclass
class GameState:
    """One visitor's game. Lives in gr.State, never shared."""

    quarter: int                          # quarter being funded, 1 to 4
    caps: dict[str, CapabilityState]
    ci_mandated: bool = True
    pending: list = field(default_factory=list)       # (due_quarter, effects)
    history: list = field(default_factory=list)       # KPI dict per quarter
    bets_played: list = field(default_factory=list)
    finished: bool = False
    seed: int = BASE_SEED                 # per-visitor seed for bet noise


def new_game(seed: int) -> GameState:
    """A fresh game at Q1, built from the CAPABILITIES targets."""
    caps = {
        name: CapabilityState(t["adoption"], t["mandated_share"], t["csat"], t["workaround_rate"])
        for name, t in CAPABILITIES.items()
    }
    return GameState(quarter=1, caps=caps, seed=seed)


def effective_caps(state: GameState) -> dict[str, CapabilityState]:
    """Capabilities as measured. Without the CI mandate only voluntary CI users remain.

    Satisfaction and workaround rate never change with the toggle: dropping a
    mandate changes who is counted, not how the tool feels to use.
    """
    caps = copy.deepcopy(state.caps)
    if not state.ci_mandated:
        ci = caps[CI]
        ci.adoption = ci.adoption * (1 - ci.mandated_share)
        ci.mandated_share = 0.0
    return caps


# From notebook cell 4
# Synthetic services and KPIs (pure): 120 fictional services, then the numbers a platform team reads
def uses_col(capability: str) -> str:
    """Column name for 'this service uses the capability'."""
    return "uses_" + capability.lower().replace(" ", "_")


def pick(rng: np.random.Generator, pool: np.ndarray, share: float) -> np.ndarray:
    """Pick round(share * len(pool)) members of pool at random, so counts hit the target."""
    k = int(round(min(max(share, 0.0), 1.0) * len(pool)))
    return rng.permutation(pool)[:k]


def generate_services(state: GameState) -> pd.DataFrame:
    """One row per service. Seeded from BASE_SEED and the quarter, so the room sees one Division X."""
    rng = np.random.default_rng([BASE_SEED, state.quarter])
    caps = effective_caps(state)
    everyone = np.arange(N_SERVICES)
    df = pd.DataFrame({"service_id": [f"svc-{i:03d}" for i in everyone]})
    for name, cap in caps.items():
        users = pick(rng, everyone, cap.adoption)
        df[uses_col(name)] = df.index.isin(users)
    ci_users = np.flatnonzero(df[uses_col(CI)].to_numpy())
    df["ci_mandated"] = df.index.isin(pick(rng, ci_users, caps[CI].mandated_share))
    df["ci_workaround"] = df.index.isin(pick(rng, ci_users, caps[CI].workaround_rate))
    df["on_platform"] = df[uses_col(CI)] & ~df["ci_workaround"]
    lead = np.where(df["on_platform"], LEAD_ON, np.where(df["ci_workaround"], LEAD_WORKAROUND, LEAD_OFF))
    onboard = np.where(df["on_platform"], ONBOARD_ON, ONBOARD_OFF)
    df["lead_time_days"] = np.round(lead * rng.lognormal(0.0, 0.2, N_SERVICES), 1)
    df["onboarding_days"] = np.round(onboard * rng.lognormal(0.0, 0.2, N_SERVICES), 1)
    df["policy_auto_pass"] = df["on_platform"]  # only the paved road produces evidence for free
    return df


def safe_median(values: pd.Series) -> float:
    """Median, or 0.0 when nobody is in the group."""
    return float(values.median()) if len(values) else 0.0


def capability_table(state: GameState, df: pd.DataFrame) -> pd.DataFrame:
    """Per-capability users, voluntary vs mandated, satisfaction and workarounds."""
    rows = []
    for name, cap in state.caps.items():
        users = int(df[uses_col(name)].sum())
        mandated = int(df["ci_mandated"].sum()) if name == CI else 0
        rows.append({
            "capability": name, "users": users, "mandated": mandated,
            "voluntary": users - mandated, "adoption": users / N_SERVICES,
            "voluntary_adoption": (users - mandated) / N_SERVICES,
            "csat": cap.csat, "workaround_rate": cap.workaround_rate,
        })
    return pd.DataFrame(rows)


def health_index(by_cap: pd.DataFrame, control_evidence: float) -> float:
    """Mean of four parts scaled 0 to 1. See HEALTH_FORMULA_TEXT."""
    parts = [
        float(((by_cap["csat"] - 1) / 4).mean()),
        float(by_cap["voluntary_adoption"].mean()),
        1 - float(by_cap["workaround_rate"].mean()),
        control_evidence,
    ]
    return float(np.mean(parts))


def kpis(state: GameState, df: pd.DataFrame) -> dict:
    """Every number the dashboard shows, from one quarter's services."""
    by_cap = capability_table(state, df)
    on, off = df[df["on_platform"]], df[~df["on_platform"]]
    control = float(df["policy_auto_pass"].mean())
    return {
        "headline_adoption": float(df[uses_col(CI)].mean()),  # on paper, workarounds included
        "voluntary_adoption": float(by_cap["voluntary_adoption"].mean()),
        "mean_csat": float(by_cap["csat"].mean()),
        "mean_workaround": float(by_cap["workaround_rate"].mean()),
        "lead_on": safe_median(on["lead_time_days"]),
        "lead_off": safe_median(off["lead_time_days"]),
        "onboard_on": safe_median(on["onboarding_days"]),
        "onboard_off": safe_median(off["onboarding_days"]),
        "control_evidence": control,
        "audit_evidence_days": 2 + 10 * (1 - control),
        "health_index": health_index(by_cap, control),
        "by_cap": by_cap,
    }


# From notebook cell 5
# Bets and the quarter step (pure): fund one bet, live with the next quarter
HEADLINE_KPIS: list[tuple[str, str]] = [
    ("headline_adoption", "Headline adoption (CI)"),
    ("voluntary_adoption", "Voluntary adoption (avg)"),
    ("mean_csat", "Satisfaction (avg, 1 to 5)"),
    ("mean_workaround", "Workaround rate (avg)"),
    ("control_evidence", "Control evidence"),
    ("health_index", "Health index (0 to 1)"),
]
MOVE_LABELS = {"adoption": "adoption", "mandated_share": "mandated share",
               "csat": "satisfaction", "workaround_rate": "workarounds"}


def compute_kpis(state: GameState) -> dict:
    """Generate this quarter's services and read the KPIs off them."""
    return kpis(state, generate_services(state))


def headline_values(k: dict) -> dict[str, float]:
    """Just the headline numbers, small enough to keep in history."""
    return {key: round(k[key], 4) for key, _ in HEADLINE_KPIS}


def apply_effects(caps: dict[str, CapabilityState], effects: list) -> None:
    """Apply (capability or '*', attribute, 'add' or 'mul', value) effects in place."""
    for target, attr, op, value in effects:
        names = list(caps) if target == "*" else [target]
        for name in names:
            old = getattr(caps[name], attr)
            setattr(caps[name], attr, old + value if op == "add" else old * value)


def add_noise_and_clamp(caps: dict[str, CapabilityState], rng: np.random.Generator, sd: float) -> None:
    """Small Gaussian noise so no two games are identical, then keep values in range."""
    for cap in caps.values():
        cap.adoption = float(np.clip(cap.adoption + rng.normal(0, sd), 0, 1))
        cap.csat = float(np.clip(cap.csat + rng.normal(0, sd), 1, 5))
        cap.workaround_rate = float(np.clip(cap.workaround_rate + rng.normal(0, sd), 0, 1))
        cap.mandated_share = float(np.clip(cap.mandated_share, 0, 1))


def direction(before: float, after: float, tol: float = 0.005) -> str:
    """UP, DOWN or SAME: a word, so colour never carries the meaning alone."""
    if after - before > tol:
        return "UP"
    if before - after > tol:
        return "DOWN"
    return "SAME"


def biggest_moves(old: dict[str, CapabilityState], new: dict[str, CapabilityState]) -> list[str]:
    """The two largest changes this quarter, on different measures, in words.

    Satisfaction is divided by 4 so a 1 to 5 score compares with 0 to 1 shares.
    """
    moves = []
    for name in old:
        for attr, label in MOVE_LABELS.items():
            delta = getattr(new[name], attr) - getattr(old[name], attr)
            size = abs(delta) / 4 if attr == "csat" else abs(delta)
            amount = f"{abs(delta):.1f}" if attr == "csat" else f"{abs(delta) * 100:.0f} pts"
            if size > 1e-9:
                moves.append((size, attr, f"{name} {label} {direction(0, delta)} {amount}"))
    moves.sort(key=lambda m: m[0], reverse=True)
    picked, seen = [], set()
    for _, attr, text in moves:
        if attr not in seen and len(picked) < 2:
            picked.append(text)
            seen.add(attr)
    return picked


def narrative_line(quarter: int, moves: list[str], lesson: str) -> str:
    """One sentence: what moved, then the lesson."""
    if not moves:
        return f"Q{quarter}: nothing moved yet, the work lands later. Lesson: {lesson}"
    subject = "biggest moves were" if len(moves) > 1 else "biggest move was"
    return f"Q{quarter}: {subject} {' and '.join(moves)}. Lesson: {lesson}"


def apply_bet(state: GameState, bet_key: str, noise_sd: float = NOISE_SD) -> tuple[GameState, list[dict], str]:
    """Fund one bet for the current quarter and return (new_state, deltas, narrative)."""
    if state.finished:
        raise ValueError("The game is over after Q4. Press Reset to play again.")
    bet = BETS[bet_key]
    before = compute_kpis(state)
    new = copy.deepcopy(state)  # never mutate the visitor's previous state
    if not new.history:
        new.history.append({"label": "Start of Q1", "bet": "", **headline_values(before)})

    apply_effects(new.caps, bet["immediate"])
    if bet["delayed"]:
        new.pending.append((new.quarter + 2, bet["delayed"]))
    next_q = new.quarter + 1
    for due, effects in new.pending:
        if due == next_q:
            apply_effects(new.caps, effects)
    new.pending = [(due, eff) for due, eff in new.pending if due != next_q]
    planned = copy.deepcopy(new.caps)  # the narrative names what the bet did, not the noise
    add_noise_and_clamp(new.caps, np.random.default_rng([new.seed, new.quarter]), noise_sd)

    played = new.quarter
    new.bets_played.append(bet_key)
    new.finished = next_q > QUARTERS
    new.quarter = min(next_q, QUARTERS)
    after = compute_kpis(new)
    new.history.append({"label": f"End of Q{played}", "bet": bet["label"], **headline_values(after)})

    deltas = [
        {"kpi": label, "before": before[key], "after": after[key],
         "direction": direction(before[key], after[key])}
        for key, label in HEADLINE_KPIS
    ]
    narrative = narrative_line(played, biggest_moves(state.caps, planned), bet["lesson"])
    return new, deltas, narrative


# From notebook cell 6
# Charts (pure): one plotly figure or HTML block per layer, 360 px high, fixed colour per capability
FIG_HEIGHT = 360


def style(fig: go.Figure, title: str, x_title: str, y_title: str) -> go.Figure:
    """Shared look: title, 'Synthetic data' subtitle, axis labels, fixed height."""
    fig.update_layout(
        title={"text": f"{title}<br><sup>Synthetic data</sup>"},
        xaxis_title=x_title, yaxis_title=y_title, height=FIG_HEIGHT,
        template="plotly_white", margin={"l": 60, "r": 20, "t": 70, "b": 50},
        legend={"orientation": "h", "y": -0.25},
    )
    return fig


def cap_colours(by_cap: pd.DataFrame) -> list[str]:
    """Capability colours in table order."""
    return [CAP_COLOURS[name] for name in by_cap["capability"]]


def headline_html(k: dict) -> str:
    """Layer 0: one big number and the question."""
    return f"""
<div style="padding:18px;border-radius:10px;border:1px solid #d0d7de;text-align:center">
  <div style="font-size:1.0em;color:#424a53">Headline adoption: services on the CI pipeline</div>
  <div style="font-size:3.4em;font-weight:800;color:#1f2328">{k['headline_adoption']:.0%}</div>
  <div style="font-size:1.3em;font-weight:600;color:#0969da">Is this platform healthy?</div>
</div>
"""


def fig_voluntary_vs_mandated(k: dict) -> go.Figure:
    """Layer 1: stacked users per capability, voluntary solid, mandated hatched."""
    by_cap = k["by_cap"]
    fig = go.Figure([
        go.Bar(name="Voluntary", x=by_cap["capability"], y=by_cap["voluntary"],
               marker={"color": cap_colours(by_cap)}),
        go.Bar(name="Mandated", x=by_cap["capability"], y=by_cap["mandated"],
               marker={"color": cap_colours(by_cap), "opacity": 0.45, "pattern": {"shape": "/"}}),
    ])
    fig.update_layout(barmode="stack")
    return style(fig, "Who chose it, who was told to", "Capability", "Services using it")


def fig_satisfaction(k: dict) -> go.Figure:
    """Layer 2: satisfaction per capability against a 'good enough' line."""
    by_cap = k["by_cap"]
    fig = go.Figure(go.Bar(x=by_cap["capability"], y=by_cap["csat"], marker={"color": cap_colours(by_cap)},
                           text=[f"{v:.1f}" for v in by_cap["csat"]], textposition="outside"))
    fig.add_hline(y=3.5, line_dash="dash", line_color="#6e7781",
                  annotation_text="good enough", annotation_position="top left")
    fig.update_yaxes(range=[1, 5.4])
    return style(fig, "Satisfaction per capability", "Capability", "Survey score (1 to 5)")


def fig_workarounds(k: dict) -> go.Figure:
    """Layer 3: share of users bypassing each capability."""
    by_cap = k["by_cap"]
    fig = go.Figure(go.Bar(x=by_cap["capability"], y=by_cap["workaround_rate"],
                           marker={"color": cap_colours(by_cap)},
                           text=[f"{v:.0%}" for v in by_cap["workaround_rate"]], textposition="outside"))
    fig.update_yaxes(tickformat=".0%", range=[0, max(0.5, by_cap["workaround_rate"].max() + 0.1)])
    return style(fig, "Workaround rate", "Capability", "Users bypassing it")


def fig_on_vs_off(k: dict) -> go.Figure:
    """Layer 4: median lead time and onboarding, on vs off the platform."""
    metrics = ["Lead time", "Idea to first prod deploy"]
    fig = go.Figure([
        go.Bar(name="On platform", x=metrics, y=[k["lead_on"], k["onboard_on"]], marker={"color": "#1a7f37"},
               text=[f"{k['lead_on']:.0f} d", f"{k['onboard_on']:.0f} d"], textposition="outside"),
        go.Bar(name="Off platform", x=metrics, y=[k["lead_off"], k["onboard_off"]], marker={"color": "#6e7781"},
               text=[f"{k['lead_off']:.0f} d", f"{k['onboard_off']:.0f} d"], textposition="outside"),
    ])
    fig.update_layout(barmode="group")
    fig.update_yaxes(range=[0, max(k["onboard_off"], k["onboard_on"]) * 1.25 + 1])
    return style(fig, "On vs off platform (medians)", "Measure", "Days")


def fig_quadrant(k: dict) -> go.Figure:
    """Layer 5: adoption vs satisfaction, bubble size = services using it."""
    by_cap = k["by_cap"]
    fig = go.Figure(go.Scatter(
        x=by_cap["adoption"], y=by_cap["csat"], mode="markers+text", text=by_cap["capability"],
        textposition="top center", marker={"size": 12 + by_cap["users"] / 3, "color": cap_colours(by_cap),
                                           "opacity": 0.8}))
    fig.add_vline(x=0.5, line_dash="dot", line_color="#6e7781")
    fig.add_hline(y=3.5, line_dash="dot", line_color="#6e7781")
    for x, y, label in [(0.97, 4.9, "Healthy"), (0.03, 4.9, "Hidden gem"),
                        (0.03, 1.1, "Rethink"), (0.97, 1.1, "Golden cage")]:
        fig.add_annotation(x=x, y=y, text=f"<b>{label}</b>", showarrow=False,
                           xanchor="right" if x > 0.5 else "left", font={"color": "#424a53"})
    fig.update_xaxes(range=[0, 1.05], tickformat=".0%")
    fig.update_yaxes(range=[1, 5])
    fig.update_layout(showlegend=False)
    return style(fig, "Adoption vs satisfaction", "Adoption (share of services)", "Satisfaction (1 to 5)")


def control_evidence_html(k: dict) -> str:
    """Layer 6: controls as evidence, not as tickets."""
    return f"""
<div style="padding:16px;border-radius:10px;border:1px solid #d0d7de;height:{FIG_HEIGHT - 40}px">
  <div style="font-size:1.2em;font-weight:700;color:#1f2328">Control evidence</div>
  <div style="font-size:0.85em;color:#6e7781;margin-bottom:10px">Synthetic data</div>
  <div style="font-size:2.6em;font-weight:800;color:#1f2328">{k['control_evidence']:.0%}</div>
  <div style="color:#424a53">of services deploy with policy checks passing automatically</div>
  <div style="font-size:2.0em;font-weight:800;color:#1f2328;margin-top:14px">{k['audit_evidence_days']:.1f} days</div>
  <div style="color:#424a53">to produce audit evidence (2 + 10 x share without automatic evidence)</div>
</div>
"""


LAYER_TITLES = ["Voluntary vs mandated", "Satisfaction", "Workarounds",
                "On vs off platform", "Adoption vs satisfaction quadrant", "Control evidence"]
LAYER_RENDERERS = [fig_voluntary_vs_mandated, fig_satisfaction, fig_workarounds,
                   fig_on_vs_off, fig_quadrant, control_evidence_html]


# From notebook cell 7
# Optional shared tally: which bet the room funded each quarter. The only shared state, behind a lock
class BetTally:
    """Counts of (quarter, bet) across every visitor. Stores no names and no free text."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[tuple[int, str], int] = {}

    def record(self, quarter: int, bet_key: str) -> None:
        """Add one vote for bet_key in the given quarter."""
        if bet_key not in BETS or not 1 <= quarter <= QUARTERS:
            return
        with self._lock:
            self._counts[(quarter, bet_key)] = self._counts.get((quarter, bet_key), 0) + 1

    def snapshot(self) -> pd.DataFrame:
        """One row per quarter, one column per bet, counts as values."""
        with self._lock:
            counts = dict(self._counts)
        rows = []
        for q in range(1, QUARTERS + 1):
            row = {"Quarter": f"Q{q}"}
            for key, bet in BETS.items():
                row[bet["label"]] = counts.get((q, key), 0)
            rows.append(row)
        return pd.DataFrame(rows)


TALLY = BetTally()


# From notebook cell 8
# Self-checks with plain asserts: targets, mandate toggle, bet directions, game end, isolation, speed
def by_name(k: dict, capability: str) -> dict:
    """One capability's row from the KPI table."""
    table = k["by_cap"].set_index("capability")
    return table.loc[capability].to_dict()


# 1. Q1 adoption lands within 5 points of every target
start = new_game(seed=1)
k0 = compute_kpis(start)
for name, target in CAPABILITIES.items():
    assert abs(by_name(k0, name)["adoption"] - target["adoption"]) <= 0.05, name

# 2. Mandate off: headline and CI adoption drop, satisfaction never moves
no_mandate = copy.deepcopy(start)
no_mandate.ci_mandated = False
k_off = compute_kpis(no_mandate)
assert k_off["headline_adoption"] < k0["headline_adoption"]
assert by_name(k_off, CI)["adoption"] < by_name(k0, CI)["adoption"]
assert list(k_off["by_cap"]["csat"]) == list(k0["by_cap"]["csat"])

# 3. With no noise, each bet moves its KPIs the way SPEC's table says
after, _, _ = apply_bet(start, "fix_ci", noise_sd=0)
k1 = compute_kpis(after)
assert by_name(k1, CI)["csat"] > by_name(k0, CI)["csat"]
assert by_name(k1, CI)["workaround_rate"] < by_name(k0, CI)["workaround_rate"]
assert by_name(k1, CI)["voluntary"] > by_name(k0, CI)["voluntary"]

after, _, _ = apply_bet(start, "onboard_wave", noise_sd=0)
k1 = compute_kpis(after)
for name in CAPABILITIES:
    assert by_name(k1, name)["adoption"] > by_name(k0, name)["adoption"], name
    assert by_name(k1, name)["csat"] < by_name(k0, name)["csat"], name
    assert by_name(k1, name)["workaround_rate"] > by_name(k0, name)["workaround_rate"], name

after, _, _ = apply_bet(start, "market_secrets", noise_sd=0)
k1 = compute_kpis(after)
assert by_name(k1, "Secrets")["adoption"] > by_name(k0, "Secrets")["adoption"]
assert by_name(k1, "Secrets")["csat"] == by_name(k0, "Secrets")["csat"]

# 4. preview_v2: nothing for Preview next quarter, a lift the quarter after, others pay 0.1
q2, _, _ = apply_bet(start, "preview_v2", noise_sd=0)
preview = "Preview environments"
assert q2.caps[preview].csat == start.caps[preview].csat
assert abs(q2.caps[CI].csat - (start.caps[CI].csat - 0.1)) < 1e-9
q3, _, _ = apply_bet(q2, "market_secrets", noise_sd=0)
assert abs(q3.caps[preview].csat - (start.caps[preview].csat + 0.8)) < 1e-9

# 5. Four quarters, then apply_bet refuses
game = new_game(seed=7)
for bet_key in ["fix_ci", "onboard_wave", "market_secrets", "preview_v2"]:
    game, deltas, narrative = apply_bet(game, bet_key)
    assert len(deltas) == len(HEADLINE_KPIS) and narrative
assert game.finished and len(game.history) == QUARTERS + 1
try:
    apply_bet(game, "fix_ci")
    raise AssertionError("apply_bet should refuse after Q4")
except ValueError:
    pass

# 6. Two games never share objects
a, b = new_game(seed=1), new_game(seed=2)
a.caps[CI].csat = 5.0
a.history.append({"label": "x"})
assert b.caps[CI].csat == CAPABILITIES[CI]["csat"] and b.history == []
assert new_game(seed=1).caps[CI].csat == CAPABILITIES[CI]["csat"]

# 7. The tally counts per quarter; a separate instance keeps the real TALLY empty
test_tally = BetTally()
test_tally.record(1, "fix_ci")
test_tally.record(1, "fix_ci")
test_tally.record(9, "fix_ci")
assert test_tally.snapshot().loc[0, BETS["fix_ci"]["label"]] == 2
assert int(TALLY.snapshot().iloc[:, 1:].to_numpy().sum()) == 0

# 8. One quarter plus every chart stays well under 300 ms (worst of 20 runs)
worst = 0.0
for i in range(20):
    t0 = time.perf_counter()
    stepped, _, _ = apply_bet(new_game(seed=i), "onboard_wave")
    k = compute_kpis(stepped)
    headline_html(k)
    for render in LAYER_RENDERERS:
        render(k)
    worst = max(worst, time.perf_counter() - t0)
assert worst < 0.3, f"too slow: {worst * 1000:.0f} ms"
print(f"Worst quarter step plus charts: {worst * 1000:.0f} ms")
print("All Demo 2 checks passed")


# From notebook cell 9
# UI helpers: shared header and badge (identical in all three demos), deltas table, end-of-game summary
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


ARROWS = {"UP": "↑ UP", "DOWN": "↓ DOWN", "SAME": "= SAME"}
DELTA_COLUMNS = ["KPI", "Before", "After", "Change"]


def fmt_kpi(kpi_label: str, value: float) -> str:
    """Satisfaction and the health index as numbers, everything else as a percentage."""
    if kpi_label.startswith("Satisfaction"):
        return f"{value:.2f}"
    if kpi_label.startswith("Health"):
        return f"{value:.3f}"
    return f"{value:.1%}"


def deltas_table(deltas: list[dict]) -> pd.DataFrame:
    """KPI, before, after and an arrow with its word."""
    rows = [[d["kpi"], fmt_kpi(d["kpi"], d["before"]), fmt_kpi(d["kpi"], d["after"]),
             ARROWS[d["direction"]]] for d in deltas]
    return pd.DataFrame(rows, columns=DELTA_COLUMNS)


def summary_html(history: list[dict]) -> str:
    """Quarter by quarter health index, the bets played, and the formula on screen."""
    rows = ""
    for prev, row in zip(history, history[1:]):
        word = direction(prev["health_index"], row["health_index"])
        rows += (f"<tr><td>{row['label']}</td><td>{row['bet']}</td>"
                 f"<td>{row['health_index']:.2f}</td><td>{badge(word)}</td></tr>")
    return f"""
<div style="padding:14px;border-radius:10px;border:1px solid #d0d7de">
  <div style="font-size:1.2em;font-weight:700">Game over: four quarters funded</div>
  <div>Health index at the start: {history[0]['health_index']:.2f}</div>
  <table style="width:100%;margin-top:8px">
    <tr><th align="left">Quarter</th><th align="left">Bet</th><th align="left">Health index</th><th align="left">Change</th></tr>
    {rows}
  </table>
  <div style="margin-top:10px;color:#424a53;font-size:0.9em">{HEALTH_FORMULA_TEXT}</div>
</div>
"""


def quarter_label(state: GameState) -> str:
    """Where the visitor is in the game."""
    if state.finished:
        return f"### All {QUARTERS} quarters played. Press Reset to start over."
    return f"### Q{state.quarter} of {QUARTERS}: pick one bet to fund"


def seed_from_session(session_hash: str | None) -> int:
    """A stable per-visitor seed, so any single game can be replayed."""
    digest = hashlib.sha256((session_hash or "local").encode()).hexdigest()
    return int(digest[:8], 16)


# From notebook cell 10
# Layout and wiring: headline first, Peel reveals one layer per click, then the per-visitor funding game
N_LAYERS = len(LAYER_RENDERERS)
EMPTY_DELTAS = pd.DataFrame(columns=DELTA_COLUMNS)
BET_CHOICES = [(f"{bet['label']}: {bet['description']}", key) for key, bet in BETS.items()]


def peel_status(level: int) -> str:
    """How far this visitor has peeled, and what comes next."""
    if level >= N_LAYERS:
        return f"Showing all {N_LAYERS} layers."
    return f"Layer {level} of {N_LAYERS}. Next: {LAYER_TITLES[level]}."


def view(state: GameState, level: int) -> list:
    """Headline, peel status and the six layer slots. Only visible layers are drawn."""
    k = compute_kpis(state)
    slots = [
        gr.update(value=render(k), visible=True) if i < level else gr.update(visible=False)
        for i, render in enumerate(LAYER_RENDERERS)
    ]
    return [headline_html(k), peel_status(level)] + slots


def reset_game(level: int, request: gr.Request) -> list:
    """A new game for this visitor only, seeded from their session. The peel level stays."""
    state = new_game(seed_from_session(request.session_hash if request else None))
    hidden = gr.update(value="", visible=False)
    return [state, level, True, quarter_label(state), EMPTY_DELTAS, "", hidden,
            gr.update(interactive=True)] + view(state, level)


def start_game(request: gr.Request) -> list:
    """Page load: a fresh game with every layer hidden, so the first screen is the headline."""
    return reset_game(0, request)


def peel(state: GameState, level: int) -> list:
    """Reveal the next layer."""
    state = state or new_game(BASE_SEED)  # clicked before the page finished loading
    level = min(level + 1, N_LAYERS)
    return [level] + view(state, level)


def show_all(state: GameState) -> list:
    """Skip ahead: reveal every layer."""
    state = state or new_game(BASE_SEED)  # clicked before the page finished loading
    return [N_LAYERS] + view(state, N_LAYERS)


def toggle_mandate(state: GameState, mandated: bool, level: int) -> list:
    """Switch the CI mandate on or off and recompute everything on screen."""
    state = state or new_game(BASE_SEED)  # clicked before the page finished loading
    new = copy.deepcopy(state)
    new.ci_mandated = mandated
    return [new] + view(new, level)


def play_quarter(state: GameState, bet_key: str, level: int) -> list:
    """Fund one bet, show the next quarter, and after Q4 the summary."""
    state = state or new_game(BASE_SEED)  # clicked before the page finished loading
    if state.finished or bet_key not in BETS:
        message = "The game is over after Q4. Press Reset to play again." if state.finished else "Pick a bet first."
        return [state, quarter_label(state), gr.update(), message,
                gr.update(), gr.update(interactive=not state.finished)] + view(state, level)
    TALLY.record(state.quarter, bet_key)
    new, deltas, narrative = apply_bet(state, bet_key)
    if new.finished:
        summary = gr.update(value=summary_html(new.history), visible=True)
    else:
        summary = gr.update(visible=False)
    return [new, quarter_label(new), deltas_table(deltas), narrative, summary,
            gr.update(interactive=not new.finished)] + view(new, level)


with gr.Blocks(title="Platform team dashboard") as demo:
    game = gr.State(None)
    peel_level = gr.State(0)
    gr.HTML(header_html("Platform team dashboard",
                        "Headline adoption lies. Peel the layers, then fund one bet per quarter and live with it."))
    with gr.Row():
        headline = gr.HTML(scale=3)
        with gr.Column(scale=1):
            mandate = gr.Checkbox(value=True, label="CI mandated",
                                  info="Untick to count only teams who chose CI themselves")
            peel_btn = gr.Button("Peel", variant="primary")
            show_all_btn = gr.Button("Show all")
            peel_md = gr.Markdown()
    slots = []
    for pair in range(0, N_LAYERS, 2):
        with gr.Row():
            for i in (pair, pair + 1):
                if LAYER_RENDERERS[i] is control_evidence_html:
                    slots.append(gr.HTML(visible=False))
                else:
                    slots.append(gr.Plot(visible=False, show_label=False))

    with gr.Accordion("Fund next quarter", open=True):
        quarter_md = gr.Markdown()
        bet = gr.Radio(choices=BET_CHOICES, value="fix_ci", label="One bet per quarter")
        gr.Markdown("Bet effects are invented for teaching and applied with small seeded noise.")
        with gr.Row():
            play_btn = gr.Button("Play quarter", variant="primary")
            reset_btn = gr.Button("Reset")
        narrative_md = gr.Markdown()
        deltas_df = gr.Dataframe(value=EMPTY_DELTAS, interactive=False, label="Next quarter, KPI by KPI")
        summary = gr.HTML(visible=False)

    with gr.Accordion("Instructor: room tally", open=False):
        tally_df = gr.Dataframe(value=TALLY.snapshot, interactive=False, label="Bets funded by the room")
        tally_btn = gr.Button("Refresh")

    view_outputs = [headline, peel_md] + slots
    game_outputs = [game, peel_level, mandate, quarter_md, deltas_df, narrative_md, summary, play_btn]
    play_outputs = [game, quarter_md, deltas_df, narrative_md, summary, play_btn]

    demo.load(start_game, None, game_outputs + view_outputs)
    reset_btn.click(reset_game, peel_level, game_outputs + view_outputs)
    peel_btn.click(peel, [game, peel_level], [peel_level] + view_outputs)
    show_all_btn.click(show_all, game, [peel_level] + view_outputs)
    mandate.input(toggle_mandate, [game, mandate, peel_level], [game] + view_outputs)
    play_btn.click(play_quarter, [game, bet, peel_level], play_outputs + view_outputs)
    tally_btn.click(TALLY.snapshot, None, tally_df)


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=64).launch(theme=THEME)
