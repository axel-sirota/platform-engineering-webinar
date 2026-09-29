---
description: Read all project context files before starting any work
---

Read these files to load full project context:

1. `CLAUDE.md` - stack, conventions, build order, critical rules
2. `plans/DECISIONS.md` - the webinar manifest
3. `imp_docs/demos.md` - SPEC, the source of truth for the three demos
4. `imp_docs/outline.md` - the course as scoped for the client
5. `plans/DEMOS.md` - status tracker, if it exists

Then report, as a table:

| Demo | Plan (`plans/demoN_plan.md`) | Notebook (cells built / SPEC) | Self-check | Spaces folder |
|---|---|---|---|---|

Plus:
- Diagrams in `diagrams/` vs the index in `.claude/commands/build-diagrams.md`
- The next demo to work on (build order: 3, 1, 2)

---

## Notebook Edit Protocol (awareness)

If this command ends up editing notebook cells, follow `~/.claude/NOTEBOOK_EDIT_PROTOCOL.md`.
Blind bulk index-based rewrites are forbidden.
