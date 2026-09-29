"""Golden path portal (Demo 1). Generated from notebooks/demo1_portal.ipynb cells 2 to 9.
Do not edit by hand: change the notebook and rerun /build-space 1."""


# From notebook cell 2
# Imports and config: the teams, templates and images the golden path offers
import os

os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"  # a public demo sends no telemetry

import hashlib
import random
import threading
import time
from collections import Counter
from datetime import datetime
from typing import Iterator

import gradio as gr
import pandas as pd

TEAMS = ["payments-core", "cards-risk", "markets-data", "retail-app", "lending-platform"]
TEAM_PLACEHOLDER = "Choose a team"

# Each template: the files the golden path scaffolds, plus two approved base images
TEMPLATES = {
    "REST API (Python)": {
        "language": "python",
        "files": ["src/app.py", "tests/test_app.py", "Dockerfile", "catalog-info.yaml",
                  ".ci/pipeline.yaml", "deploy/values.yaml", "README.md"],
        "default_image": "internal-registry/python:3.12-slim-approved",
        "alt_image": "internal-registry/python:3.12-approved",
    },
    "Batch job (Python)": {
        "language": "python",
        "files": ["src/job.py", "tests/test_job.py", "Dockerfile", "catalog-info.yaml",
                  ".ci/pipeline.yaml", "deploy/values.yaml", "README.md"],
        "default_image": "internal-registry/python:3.12-slim-approved",
        "alt_image": "internal-registry/python:3.12-approved",
    },
    "Web frontend (Node)": {
        "language": "node",
        "files": ["src/index.js", "src/App.jsx", "tests/app.test.js", "package.json",
                  "Dockerfile", "catalog-info.yaml", ".ci/pipeline.yaml", "deploy/values.yaml"],
        "default_image": "internal-registry/node:20-slim-approved",
        "alt_image": "internal-registry/node:20-approved",
    },
}
UNAPPROVED_IMAGES = ["python:latest", "my-team/custom:dev"]

CLASSIFICATIONS = ["Public", "Internal", "Confidential"]
EXPOSURES = ["Internal only", "Public internet"]

DEFAULT_REPLICAS = 2
STAGE_DELAY_S = 0.4  # deliberate pause so the room can watch each stage tick
ROOM_CAP = 500
REFRESH_S = 5
STAGES = ["build", "test", "policy", "deploy"]

# ADMIN_KEY: a Space secret, read from the environment only. Empty means reset is disabled.
ADMIN_KEY = os.environ.get("ADMIN_KEY", "")


# From notebook cell 3
# Service spec and the four policy rules: pure functions, the same code a CI check would import
# Stdlib only. Uses TEMPLATES and DEFAULT_REPLICAS from the config cell, nothing else.
import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class ServiceSpec:
    """Everything the developer picked in the form."""

    name: str
    team: Optional[str]
    template: str
    classification: str
    exposure: str
    base_image: str
    replicas: int


@dataclass
class RuleResult:
    """The outcome of one policy rule, with the why and the fix a developer sees."""

    rule_id: str
    title: str
    passed: bool
    message: str
    why: str
    fix: str


NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]{2,29}$")
OVERRIDE_NOTE = "Override accepted. You now own this setting, the platform won't tune it for you."


def slugify(text: str) -> str:
    """Turn whatever was typed into a name that would pass R2."""
    slug = text.strip().lower().replace(" ", "-").replace("_", "-")
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    if not slug or not slug[0].isalpha():
        slug = "svc-" + slug
    slug = slug[:30].rstrip("-")
    if len(slug) < 3:
        slug = (slug + "-svc")[:30]
    return slug


def rule_owner_required(spec: ServiceSpec) -> RuleResult:
    """R1: someone must be on call for this service."""
    ok = bool(spec.team)
    return RuleResult(
        "R1", "owner-required", ok,
        f"Owner is {spec.team}" if ok else "No owner team set",
        "Every service needs a team on call for incidents",
        "Pick your team from the list",
    )


def rule_name_format(spec: ServiceSpec) -> RuleResult:
    """R2: names become DNS entries, so they must be DNS safe."""
    ok = bool(NAME_PATTERN.match(spec.name))
    return RuleResult(
        "R2", "name-format", ok,
        "Name is valid" if ok else "Name must be 3 to 30 lowercase letters, numbers or hyphens, starting with a letter",
        "Names become DNS entries and catalog IDs",
        f"Try the name: {slugify(spec.name)}",
    )


def rule_no_public_confidential(spec: ServiceSpec) -> RuleResult:
    """R3: confidential data never sits behind a public endpoint."""
    ok = not (spec.classification == "Confidential" and spec.exposure == "Public internet")
    return RuleResult(
        "R3", "no-public-confidential", ok,
        "Exposure fits the data classification" if ok else "Confidential data can't use Public internet exposure",
        "Data protection policy",
        "Set exposure to Internal only",
    )


def rule_approved_image(spec: ServiceSpec) -> RuleResult:
    """R4: only patched and scanned base images reach production."""
    template = TEMPLATES[spec.template]
    approved = [template["default_image"], template["alt_image"]]
    ok = spec.base_image in approved
    return RuleResult(
        "R4", "approved-image", ok,
        "Base image is approved" if ok else f"{spec.base_image} is not on the approved list",
        "Approved images are patched and scanned",
        f"Switch to the approved image {template['default_image']}",
    )


def run_policies(spec: ServiceSpec) -> list[RuleResult]:
    """Run R1 to R4 in order. Every rule runs, so one submit shows every problem."""
    rules = [rule_owner_required, rule_name_format, rule_no_public_confidential, rule_approved_image]
    return [rule(spec) for rule in rules]


def override_notes(spec: ServiceSpec) -> list[str]:
    """Overrides are allowed, but the developer now owns them."""
    notes = []
    if spec.replicas != DEFAULT_REPLICAS:
        notes.append(f"Replicas set to {spec.replicas}. {OVERRIDE_NOTE}")
    if spec.base_image == TEMPLATES[spec.template]["alt_image"]:
        notes.append(f"Base image set to {spec.base_image}. {OVERRIDE_NOTE}")
    return notes


# From notebook cell 4
# What the golden path generates: repo tree and three files, built as plain text (no YAML library)


def repo_tree(spec: ServiceSpec) -> str:
    """An ASCII tree of the scaffolded repo, rooted at the service name."""
    files = TEMPLATES[spec.template]["files"]
    lines = [f"{spec.name}/"]
    for i, path in enumerate(files):
        branch = "└── " if i == len(files) - 1 else "├── "
        lines.append(branch + path)
    return "\n".join(lines)


def catalog_info_yaml(spec: ServiceSpec) -> str:
    """The catalog entry: who owns it and what data it holds."""
    return (
        "apiVersion: backstage.io/v1alpha1\n"
        "kind: Component\n"
        "metadata:\n"
        f"  name: {spec.name}\n"
        "  annotations:\n"
        f"    platform.example/data-classification: {spec.classification}\n"
        "spec:\n"
        "  type: service\n"
        f"  owner: {spec.team or 'MISSING'}\n"
        f"  template: {spec.template}\n"
        "  lifecycle: experimental\n"
    )


def pipeline_yaml(spec: ServiceSpec) -> str:
    """The CI pipeline: the bank's controls run as a stage, not as a ticket."""
    return (
        f"# Pipeline for {spec.name}, generated by the golden path\n"
        "stages:\n"
        "  - name: build\n"
        f"    image: {spec.base_image}\n"
        "  - name: test\n"
        "    run: unit tests\n"
        "  - name: policy\n"
        "    rules: [R1-owner-required, R2-name-format, R3-no-public-confidential, R4-approved-image]\n"
        "  - name: deploy\n"
        "    environment: dev\n"
    )


def values_yaml(spec: ServiceSpec) -> str:
    """Deploy values: image, replicas and where the service is reachable from."""
    ingress = "public" if spec.exposure == "Public internet" else "internal"
    return (
        f"image: {spec.base_image}\n"
        f"replicas: {spec.replicas}\n"
        "ingress:\n"
        f"  visibility: {ingress}\n"
        f"  host: {spec.name}.dev.platform.example\n"
    )


def commit_hash(spec: ServiceSpec, ts: str) -> str:
    """A short, repeatable commit id for the audit line."""
    raw = "|".join([spec.name, str(spec.team), spec.template, spec.classification,
                    spec.exposure, spec.base_image, str(spec.replicas), ts])
    return hashlib.sha1(raw.encode()).hexdigest()[:7]


def service_url(spec: ServiceSpec) -> str:
    """Where the new service lives in the dev environment."""
    return f"https://{spec.name}.dev.platform.example"


# From notebook cell 5
# The shared room catalog: the only state everyone on the link sees, guarded by one lock

ROOM_COLUMNS = ["time", "alias", "service", "team", "status", "failed_rules"]


class RoomCatalog:
    """Every service anyone in the room created, newest last, capped at ROOM_CAP."""

    def __init__(self, admin_key: str) -> None:
        self._lock = threading.Lock()
        self._admin_key = admin_key
        self.entries: list[dict] = []
        self.aliases: dict[str, str] = {}

    def alias_for(self, session_hash: Optional[str]) -> str:
        """Engineer 1, Engineer 2, ... in order of first appearance. No real names."""
        key = session_hash or "anonymous"
        with self._lock:
            if key not in self.aliases:
                self.aliases[key] = f"Engineer {len(self.aliases) + 1}"
            return self.aliases[key]

    def add(self, entry: dict) -> None:
        """Store one result. A name that failed R2 is never shown to the room."""
        safe = dict(entry)
        if not NAME_PATTERN.match(safe.get("service", "")):
            safe["service"] = "(invalid name)"
        with self._lock:
            self.entries.append(safe)
            if len(self.entries) > ROOM_CAP:
                self.entries.pop(0)  # drop the oldest so memory stays flat

    def snapshot(self) -> tuple[dict, pd.DataFrame]:
        """Counters plus the table, newest first. Copies, so readers never hold the lock."""
        with self._lock:
            rows = list(self.entries)
        failed = Counter(rule for row in rows for rule in row["failed_rules"].split(", ") if rule)
        counters = {
            "created": len(rows),
            "live": sum(row["status"] == "LIVE" for row in rows),
            "blocked": sum(row["status"] == "BLOCKED" for row in rows),
            "most_common_failed_rule": failed.most_common(1)[0][0] if failed else "none yet",
        }
        table = pd.DataFrame(list(reversed(rows)), columns=ROOM_COLUMNS)
        return counters, table

    def reset(self, key: str) -> bool:
        """Clear the room, but only for whoever holds the admin key."""
        if not self._admin_key or key != self._admin_key:
            return False
        with self._lock:
            self.entries.clear()
            self.aliases.clear()
        return True


ROOM = RoomCatalog(admin_key=ADMIN_KEY)


# From notebook cell 6
# Self-check: plain asserts on the rules, generators and room catalog before anything launches


def make_spec(**changes) -> ServiceSpec:
    """A valid spec, with any field overridden for a test."""
    fields = dict(name="payments-api", team="payments-core", template="REST API (Python)",
                  classification="Internal", exposure="Internal only",
                  base_image=TEMPLATES["REST API (Python)"]["default_image"], replicas=DEFAULT_REPLICAS)
    fields.update(changes)
    return ServiceSpec(**fields)


def failed_ids(spec: ServiceSpec) -> list[str]:
    """The ids of every rule this spec breaks."""
    return [r.rule_id for r in run_policies(spec) if not r.passed]


# A valid spec passes all four rules, with no override notes
assert failed_ids(make_spec()) == []
assert override_notes(make_spec()) == []

# Confidential plus Public internet fails only R3, and the fix says what to change
r3 = run_policies(make_spec(classification="Confidential", exposure="Public internet"))
assert [r.rule_id for r in r3 if not r.passed] == ["R3"]
assert "Internal only" in r3[2].fix

# Missing owner fails R1; a bad name fails R2 and suggests a slug that would pass
assert failed_ids(make_spec(team=None)) == ["R1"]
r2 = run_policies(make_spec(name="My Service!!"))
assert [r.rule_id for r in r2 if not r.passed] == ["R2"]
assert "my-service" in r2[1].fix
for typed in ["My Service!!", "9lives", "a", "__x__", "Payments API v2 (new)", "x" * 80]:
    assert NAME_PATTERN.match(slugify(typed)), typed

# An unapproved image fails R4 and names the approved one; the alt image passes with a note
r4 = run_policies(make_spec(base_image="python:latest"))
assert [r.rule_id for r in r4 if not r.passed] == ["R4"]
assert TEMPLATES["REST API (Python)"]["default_image"] in r4[3].fix
alt = make_spec(base_image=TEMPLATES["REST API (Python)"]["alt_image"])
assert failed_ids(alt) == [] and len(override_notes(alt)) == 1
assert len(override_notes(make_spec(base_image=alt.base_image, replicas=4))) == 2

# The generated files carry the form values
assert repo_tree(make_spec()).startswith("payments-api/")
assert "owner: payments-core" in catalog_info_yaml(make_spec())
assert "R3-no-public-confidential" in pipeline_yaml(make_spec())
assert "visibility: public" in values_yaml(make_spec(exposure="Public internet"))
assert len(commit_hash(make_spec(), "t1")) == 7 and commit_hash(make_spec(), "t1") != commit_hash(make_spec(), "t2")

# Room catalog, on a separate instance so the real ROOM starts empty
room = RoomCatalog(admin_key="test-key")
assert room.alias_for("session-a") != room.alias_for("session-b")
assert room.alias_for("session-a") == "Engineer 1"
room.add(dict(time="10:00:00", alias="Engineer 1", service="payments-api", team="payments-core",
              status="LIVE", failed_rules=""))
room.add(dict(time="10:00:05", alias="Engineer 2", service="<b>free text</b>", team="cards-risk",
              status="BLOCKED", failed_rules="R2, R3"))
counters, table = room.snapshot()
assert counters["created"] == 2 and counters["live"] == 1 and counters["blocked"] == 1
assert table.iloc[0]["service"] == "(invalid name)"  # newest first, free text never reaches the room
assert room.reset("wrong-key") is False and len(room.entries) == 2
assert room.reset("test-key") is True and room.entries == [] and room.aliases == {}
assert RoomCatalog(admin_key="").reset("") is False  # no key set means reset is disabled
for i in range(ROOM_CAP + 20):
    room.add(dict(time="t", alias="a", service=f"svc-{i}", team="cards-risk", status="LIVE", failed_rules=""))
assert len(room.entries) == ROOM_CAP
assert len(ROOM.entries) == 0

# Speed: rules plus every generator over 1,000 random specs, far under 300 ms each
rng = random.Random(42)
start = time.perf_counter()
for _ in range(1000):
    template = rng.choice(list(TEMPLATES))
    spec = make_spec(name=rng.choice(["api", "My Service!!", "ledger-sync"]), team=rng.choice(TEAMS + [None]),
                     template=template, classification=rng.choice(CLASSIFICATIONS),
                     exposure=rng.choice(EXPOSURES), replicas=rng.randint(1, 5),
                     base_image=rng.choice([TEMPLATES[template]["default_image"]] + UNAPPROVED_IMAGES))
    run_policies(spec)
    override_notes(spec)
    commit_hash(spec, "t")
    for generate in (repo_tree, catalog_info_yaml, pipeline_yaml, values_yaml, service_url):
        generate(spec)
mean_ms = (time.perf_counter() - start) * 1000 / 1000
assert mean_ms < 5, mean_ms

print(f"Mean compute per spec: {mean_ms:.3f} ms")
print("All Demo 1 checks passed")


# From notebook cell 7
# UI helpers: HTML strings and tables only, no event wiring. Theme and header shared by all three demos
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


CARD = "padding:12px 16px;border-radius:10px;margin:6px 0;color:#1f2328;"


def policy_table(results: list[RuleResult]) -> pd.DataFrame:
    """One row per rule: the id and title, PASS or FAIL as a word, and the message."""
    rows = [[f"{r.rule_id} {r.title}", "PASS" if r.passed else "FAIL", r.message] for r in results]
    return pd.DataFrame(rows, columns=["Rule", "Result", "Message"])


def stages_html(states: dict[str, str]) -> str:
    """Build, test, policy, deploy left to right, each with its status word."""
    cells = [
        f'<div style="flex:1;text-align:center;padding:8px;border:1px solid #d0d7de;border-radius:8px">'
        f'<div style="font-weight:600;color:#1f2328;margin-bottom:4px">{stage}</div>{badge(states[stage])}</div>'
        for stage in STAGES
    ]
    return f'<div style="display:flex;gap:8px">{"".join(cells)}</div>'


def service_card_html(spec: ServiceSpec, commit: str, alias: str, notes: list[str]) -> str:
    """The success card: where it lives, who owns it, and the audit line."""
    stamp = datetime.now().strftime("%H:%M:%S")
    note_html = "".join(f'<div style="margin-top:6px;color:#633c01">{note}</div>' for note in notes)
    return (
        f'<div style="{CARD}background:#dafbe1;border:1px solid #1a7f37">'
        f'<div style="font-size:1.2em;font-weight:700">{badge("LIVE")} {spec.name}</div>'
        f'<div style="margin-top:6px">URL: <code>{service_url(spec)}</code></div>'
        f'<div>Dashboard: <u>{spec.name} overview (dev)</u></div>'
        f'<div>Owner: {spec.team}</div>'
        f'<div style="margin-top:6px;font-family:monospace">Audit: commit {commit} by {alias} at {stamp}</div>'
        f"{note_html}</div>"
    )


def failure_card_html(failed: list[RuleResult]) -> str:
    """One red block per failed rule: what broke, why the rule exists, how to fix it."""
    blocks = [
        f'<div style="{CARD}background:#ffebe9;border:1px solid #cf222e">'
        f'<div style="font-weight:700">{badge("FAIL")} {r.rule_id} {r.title}: {r.message}</div>'
        f"<div>Why: {r.why}</div><div><b>Fix:</b> {r.fix}</div></div>"
        for r in failed
    ]
    header = f'<div style="font-weight:700;margin:4px 0">{badge("BLOCKED")} Change one field and press Create again</div>'
    return header + "".join(blocks)


def error_card_html() -> str:
    """Shown instead of a stack trace if anything unexpected goes wrong."""
    return (
        f'<div style="{CARD}background:#fff8c5;border:1px solid #d4a72c">'
        "Something went wrong on our side. Your form is unchanged, press Create again.</div>"
    )


def room_counters_html(counters: dict) -> str:
    """Four counters for the room readout."""
    items = [
        ("Services created", counters["created"]),
        (f'Live {badge("LIVE")}', counters["live"]),
        (f'Blocked by policy {badge("BLOCKED")}', counters["blocked"]),
        ("Most common failed rule", counters["most_common_failed_rule"]),
    ]
    tiles = [
        f'<div style="flex:1;padding:10px;border:1px solid #d0d7de;border-radius:8px;background:#ffffff">'
        f'<div style="color:#424a53">{label}</div><div style="font-size:1.6em;font-weight:700;color:#1f2328">{value}</div></div>'
        for label, value in items
    ]
    return f'<div style="display:flex;gap:8px;flex-wrap:wrap">{"".join(tiles)}</div>'


# From notebook cell 8
# The Create handler: a generator, so the page updates step by step while the stages tick


def build_spec(name: str, team: str, template: str, classification: str,
               exposure: str, base_image: str, replicas: float) -> ServiceSpec:
    """Turn raw form values into a spec. The placeholder team means no team."""
    return ServiceSpec(
        name=(name or "").strip(),
        team=None if team == TEAM_PLACEHOLDER else team,
        template=template,
        classification=classification,
        exposure=exposure,
        base_image=base_image,
        replicas=int(replicas),
    )


def record_in_room(spec: ServiceSpec, alias: str, failed: list[RuleResult]) -> None:
    """One line in the shared catalog. RoomCatalog.add hides names that failed R2."""
    ROOM.add(dict(
        time=datetime.now().strftime("%H:%M:%S"),
        alias=alias,
        service=spec.name,
        team=spec.team or "(none)",
        status="BLOCKED" if failed else "LIVE",
        failed_rules=", ".join(r.rule_id for r in failed),
    ))


def create_service(name: str, team: str, template: str, classification: str, exposure: str,
                   base_image: str, replicas: float, request: gr.Request) -> Iterator[tuple]:
    """Yields (stages, card, repo tree, catalog-info, pipeline, values, policy table) as it goes."""
    try:
        spec = build_spec(name, team, template, classification, exposure, base_image, replicas)
        files = (repo_tree(spec), catalog_info_yaml(spec), pipeline_yaml(spec), values_yaml(spec))
        states = {stage: "PENDING" for stage in STAGES}
        empty = pd.DataFrame(columns=["Rule", "Result", "Message"])
        yield (stages_html(states), "", *files, empty)

        # The controls run inside the path, on every submit, with no ticket
        results = run_policies(spec)
        failed = [r for r in results if not r.passed]
        table = policy_table(results)
        yield (stages_html(states), "", *files, table)

        for stage in ["build", "test", "policy"]:
            states[stage] = "RUNNING"
            yield (stages_html(states), "", *files, table)
            time.sleep(STAGE_DELAY_S)
            states[stage] = "FAIL" if stage == "policy" and failed else "PASS"
            yield (stages_html(states), "", *files, table)

        alias = ROOM.alias_for(request.session_hash if request else None)
        record_in_room(spec, alias, failed)
        if failed:
            yield (stages_html(states), failure_card_html(failed), *files, table)
            return

        states["deploy"] = "RUNNING"
        yield (stages_html(states), "", *files, table)
        time.sleep(STAGE_DELAY_S)
        states["deploy"] = "PASS"
        ts = datetime.now().isoformat()
        card = service_card_html(spec, commit_hash(spec, ts), alias, override_notes(spec))
        yield (stages_html(states), card, *files, table)
    except Exception:  # a friendly card on the projector, never a stack trace
        yield (gr.update(), error_card_html(), gr.update(), gr.update(), gr.update(), gr.update(), gr.update())


# From notebook cell 9
# Layout and wiring: tab 1 is per visitor, tab 2 is the room catalog everyone on the link shares


def image_choices(template: str) -> list[str]:
    """Approved images first, then the two unapproved ones so R4 has something to catch."""
    t = TEMPLATES[template]
    return [t["default_image"], t["alt_image"]] + UNAPPROVED_IMAGES


def on_template_change(template: str) -> dict:
    """A new template brings its own approved images and resets to the default one."""
    return gr.update(choices=image_choices(template), value=TEMPLATES[template]["default_image"])


def refresh_room() -> tuple[str, pd.DataFrame]:
    """Read the shared catalog. Called by the timer, the button and page load."""
    counters, table = ROOM.snapshot()
    return room_counters_html(counters), table


def reset_room(key: str) -> tuple[str, str, str, pd.DataFrame]:
    """Clear the room if the key is right. The key box is always emptied afterwards."""
    message = "Room reset" if ROOM.reset(key or "") else "Wrong key"
    counters, table = refresh_room()
    return message, "", counters, table


FIRST_TEMPLATE = list(TEMPLATES)[0]

with gr.Blocks(title="Golden path portal") as demo:
    gr.HTML(header_html(
        "Golden path portal",
        "Create a service without a ticket. The bank's controls run inside the path.",
    ))
    with gr.Tab("Create a service"):
        with gr.Row():
            with gr.Column(scale=2):
                name = gr.Textbox(label="Service name", placeholder="for example payments-api", max_length=60)
                team = gr.Dropdown([TEAM_PLACEHOLDER] + TEAMS, value=TEAM_PLACEHOLDER, label="Owner team")
                template = gr.Dropdown(list(TEMPLATES), value=FIRST_TEMPLATE, label="Template")
                classification = gr.Radio(CLASSIFICATIONS, value="Internal", label="Data classification")
                exposure = gr.Radio(EXPOSURES, value="Internal only", label="Exposure")
                with gr.Accordion("Advanced (overrides you own)", open=False):
                    base_image = gr.Dropdown(image_choices(FIRST_TEMPLATE),
                                             value=TEMPLATES[FIRST_TEMPLATE]["default_image"], label="Base image")
                    replicas = gr.Slider(1, 5, value=DEFAULT_REPLICAS, step=1, label="Replicas")
                create = gr.Button("Create", variant="primary")
            with gr.Column(scale=3):
                stages = gr.HTML(stages_html({stage: "PENDING" for stage in STAGES}))
                card = gr.HTML()
                with gr.Tab("Repo tree"):
                    tree_out = gr.Code(language=None, label="Repo tree")
                with gr.Tab("catalog-info.yaml"):
                    catalog_out = gr.Code(language="yaml", label="catalog-info.yaml")
                with gr.Tab("pipeline.yaml"):
                    pipeline_out = gr.Code(language="yaml", label=".ci/pipeline.yaml")
                with gr.Tab("values.yaml"):
                    values_out = gr.Code(language="yaml", label="deploy/values.yaml")
                policy_out = gr.Dataframe(label="Policy checks", interactive=False, wrap=True)

    with gr.Tab("Room catalog"):
        counters_out = gr.HTML()
        room_out = gr.Dataframe(label="Everyone's services, newest first", interactive=False, wrap=True, max_height=380)
        refresh = gr.Button("Refresh")
        with gr.Row():
            admin_key_box = gr.Textbox(label="Admin key", type="password", scale=2)
            reset = gr.Button("Reset room", variant="stop", scale=1)
            reset_msg = gr.Markdown()

    # Every input is read, no input is ever cleared, so people change one field and resubmit
    form = [name, team, template, classification, exposure, base_image, replicas]
    results = [stages, card, tree_out, catalog_out, pipeline_out, values_out, policy_out]
    create.click(create_service, form, results)
    template.change(on_template_change, template, base_image)

    room_view = [counters_out, room_out]
    timer = gr.Timer(REFRESH_S)
    timer.tick(refresh_room, None, room_view, show_progress="hidden")
    refresh.click(refresh_room, None, room_view)
    demo.load(refresh_room, None, room_view)
    reset.click(reset_room, admin_key_box, [reset_msg, admin_key_box] + room_view)


if __name__ == "__main__":
    demo.queue(default_concurrency_limit=64).launch(theme=THEME)
