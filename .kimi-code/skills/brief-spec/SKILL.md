---
name: brief-spec
description: Classify substantive coding-agent work and shape the full explanation for reviews, explorations, implementations, debugging, planning, research, operations, or general questions. Use when a task begins or clearly pivots; when the user asks Brief-Spec to explain work; or when a Brief-Spec lifecycle hook supplies a type decision.
---

# Brief-Spec Router

<!-- brief-spec:skill:v1 -->

Choose one primary work type and one subject. Adapt the full explanation to the selected profile;
retain the Outcome Brief or Session Checkpoint as the shared terminal contract.

## Route the task

1. Honor an explicit type from the user or host.
2. On Grok Build, do not run the classifier from the model or search for its executable. Grok's
   native passive hooks record the deterministic decision but cannot inject stdout into the model
   turn. Select the matching profile provisionally, then copy the authoritative metadata supplied
   by the native Stop hook's single correction. Do not invent or retain placeholder metadata.
3. On other harnesses, when available, run `brief-spec classify - --json` with only the bounded
   current task text. Do not send task text to another model or network service.
4. Use `general` when signals conflict or remain ambiguous.
5. Normalize the subject to a short slug, such as `pull-request`, `codebase`, `bug`, or `release`.
6. Keep the selection stable for the task. Change it only for an explicit override, a new task, or a
   clear user pivot; tool choice alone is not a pivot.
7. Read exactly one matching profile:
   - [general](references/general.md)
   - [exploration](references/exploration.md)
   - [review](references/review.md)
   - [implementation](references/implementation.md)
   - [debugging](references/debugging.md)
   - [planning](references/planning.md)
   - [research](references/research.md)
   - [operations](references/operations.md)

## Preserve the shared contract

- Use the profile for the main explanation; do not force all work into one generic narrative.
- Keep direct, derived, and reported evidence distinct.
- Do not imply that classification proves the answer.
- End substantive terminal work with `outcome-brief`.
- Use `session-checkpoint` only at an explicit or eligible lifecycle boundary.
- Subagents contribute evidence and work state; the main task owns the user-facing brief.

At a terminal Outcome or Checkpoint, use one outer typed region around the profile explanation and
the unchanged legacy brief. Copy the classification metadata supplied by the hook or classifier:

```markdown
<!-- brief-spec:typed:v1 type={work_type} subject={subject} confidence={confidence} origin={origin} classified_at={classified_at} profile=1.0 -->
### {first profile section}

Type-specific content.

<!-- briefspec:outcome:v1 -->
...the unchanged Outcome Brief contract...
<!-- /briefspec -->
<!-- /brief-spec -->
```

The braced values above are placeholders. Replace every one with the classifier result; never copy
the placeholder text or invent a fixed example timestamp.

Do not create new timestamps while rendering downloads; canonical creation and classification times
must be captured once.
