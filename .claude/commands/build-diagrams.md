---
description: Build Mermaid diagrams one by one into diagrams/, for the notebooks' intro cells and the slides
---

Build diagrams: $ARGUMENTS

(Argument is a demo number 1 to 3, or `delivery` for the share-link diagram. With no
argument, list every diagram in SPEC and build the unbuilt ones.)

## GUARD

```bash
ls plans/DECISIONS.md 2>/dev/null
```

If missing: "Run `/init-webinar` first."

---

Diagrams come from SPEC (`imp_docs/demos.md`), which already has a Mermaid draft for each
demo flow and for delivery. This command refines each draft, writes it to
`diagrams/<slug>.mmd`, and renders a PNG for Colab, since Colab does not render Mermaid.

## Diagram Index (from SPEC)

| Slug | Source in SPEC | Used in |
|---|---|---|
| demo1-golden-path-flow | Colab 1 flowchart | demo1 Cell 0, slides |
| demo2-peel-and-bet | Colab 2 flowchart | demo2 Cell 0, slides |
| demo3-three-divisions | new: A, B, C strategies side by side | demo3 Cell 0, slides |
| delivery-share-links | Delivery flowchart | instructor runbook, slides |

Add a row here and in `plans/DEMOS.md` if a plan's diagram index names a new one.

---

## Step 1: Read Context

1. SPEC's Mermaid block for the diagram
2. The notebook cell that embeds it (if built), to see what it must serve
3. `plans/demo<N>_plan.md` if it names extra diagrams

## Step 2: List and ask

```
Diagrams to build:
1. <slug>.mmd - <what it shows>
...
I'll build them one at a time and ask for approval before each file.
```

Ask: "Ready to start with diagram 1?"

## Step 3: One at a Time, Approval Between Each

### 3a. Show the Mermaid source in chat first

```
Diagram <K>: <slug>
Shows: <one line>
Used in: <cell / slide>

<mermaid source>

Does this look right? I'll write the file once you approve.
```

**Wait for approval.**

### 3b. Write `diagrams/<slug>.mmd`

Raw Mermaid only, no fences.

### 3c. Render the PNG

```bash
npx -y @mermaid-js/mermaid-cli -i diagrams/<slug>.mmd -o diagrams/<slug>.png -w 1600 -b white
```

If `npx` is unavailable, say so and stop; do not install global packages without asking.

### 3d. Embed

Colab cannot read repo-relative files after upload, so the notebook cell embeds the PNG via
its raw GitHub URL once the repo is pushed, or as an attachment. Ask the user which before
editing any notebook cell, then follow the Notebook Edit Protocol.

### 3e. Ask before the next

"`<slug>.mmd` and `.png` written. Ready for `<next-slug>`?"

---

## Diagram Design Rules

- One idea per diagram, max ~10 nodes; split if it needs more
- `flowchart LR` for flows and pipelines, `flowchart TD` for hierarchies
- Labels short, English, plain ASCII, no em dashes
- Status nodes carry a word, never colour alone (PASS, FAIL, LIVE, BLOCKED)
- Legible on a 1280x720 shared Teams screen
- No real client or company names

---

## Step 4: Summary

| Slug | .mmd | .png | Embedded |
|---|---|---|---|

Next step: `/validate-notebooks`.

---

## Notebook Edit Protocol (MANDATORY when embedding)

Follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`: normalize ids, size-gate the mechanism, locate
by id + content, read back and assert, run `nbformat.validate` and the `ast.parse` +
`pyflakes` gate. Blind bulk index-based rewrites are forbidden.
