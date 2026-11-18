---
name: session-checkpoint
description: Re-orient a long, dense, or interruption-prone agent session without replacing the underlying evidence. Use when the user asks for a recap, orientation, simple teaching explanation, or spoken summary; when a session has accumulated many turns or tool calls; before context compaction; or when a Brief-Spec hook says a checkpoint is eligible.
---

# Session Checkpoint

<!-- briefspec:skill:v1 -->

Render the same bounded session state for a different human need. A timer creates eligibility; it
does not justify interrupting active work. Deliver at a natural boundary.

## Choose one mode

- `orient`: a 30–45 second operational scan—where we are, what changed, and the next move.
- `teach`: a plain-language mental model—what we did, why it works, an example, and watch-outs.
- `spoken`: an 80–240 word sequential script designed to be heard. Keep paths and dense evidence in
  the separate screen-only proof field.

Use `orient` when no mode is requested. Do not treat spoken mode as audio generation.

## Workflow

1. Re-read current artifacts or tool results; do not summarize an earlier summary.
2. Select only completed work, decisions, direct proof, gaps, and the next useful move.
3. Keep planned and completed work distinct.
4. Prefix proof items with `[direct|derived|reported]/[pass|fail|info]` and retain an
   inspectable locator.
5. Render the requested mode using the exact field order in
   [references/modes.md](references/modes.md).
6. If available, run `brief-spec validate checkpoint - --mode <mode>`.
7. Continue the original work after an automatic checkpoint unless the user asked to pause.

## Invariants

- Put an invisible marker before and after the checkpoint.
- Keep at least one inspectable proof reference outside the spoken script.
- Use explicit `None` for empty list fields.
- Never claim a checkpoint is canonical project memory.
- Never silently ingest the checkpoint into Nexo, Obsidian, or another knowledge system.
- Do not repeat a valid final Outcome Brief with an automatic orient checkpoint.

Read [references/examples.md](references/examples.md) when a concrete checkpoint would help.
