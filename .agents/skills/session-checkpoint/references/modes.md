# Checkpoint mode contracts

## Orient

```markdown
<!-- briefspec:checkpoint:v1 mode=orient -->
## Session Checkpoint · Orient

Headline: One sentence locating the session.
Current state: What is true right now.

Completed:
- Completed work only

Decisions:
- Decision and why

Proof:
- [direct/info] `path/to/reference` — inspectable result

Next:
- Next useful move

Open:
- None
<!-- /briefspec -->
```

## Teach

```markdown
<!-- briefspec:checkpoint:v1 mode=teach -->
## Session Checkpoint · Teach

Headline: The idea in one sentence.
Mental model: A plain-language model of the system.
Why it matters: The practical consequence.

What changed:
- Ordered change

Example: A concrete example that makes the model memorable.

Watch-outs:
- Boundary or failure mode

Next:
- Next useful move

Proof:
- [direct/info] `path/to/reference` — inspectable result
<!-- /briefspec -->
```

## Spoken

```markdown
<!-- briefspec:checkpoint:v1 mode=spoken -->
## Session Checkpoint · Spoken

Headline: The spoken brief in one sentence.
Script: Write 80–240 words in short sentences with audible transitions. Expand abbreviations when
helpful. Avoid tables, code fences, hashes, and long paths.

Screen-only proof:
- [direct/info] `path/to/reference` — inspectable result kept out of the spoken script

Next:
- Next useful move
<!-- /briefspec -->
```
