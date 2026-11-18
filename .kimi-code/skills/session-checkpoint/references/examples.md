# Checkpoint examples

## Orient example

```markdown
<!-- briefspec:checkpoint:v1 mode=orient -->
## Session Checkpoint · Orient

Headline: The adapter is implemented; clean-room installation is next.
Current state: All three provider payloads normalize into the same event model.

Completed:
- Added Codex, Claude, and Copilot adapters.
- Added the one-repair guard.

Decisions:
- Hooks persist counters and references, never raw prompts or tool output.

Proof:
- [direct/pass] `tests/test_adapters.py` → provider fixtures passed

Next:
- Build and install the wheel in an isolated home directory.

Open:
- Live Copilot CLI testing requires its executable.
<!-- /briefspec -->
```

## Spoken example

```markdown
<!-- briefspec:checkpoint:v1 mode=spoken -->
## Session Checkpoint · Spoken

Headline: The shared contract is working, and installation is the remaining gate.
Script: Here is where we are. The three agent integrations now translate their different lifecycle
events into one small internal model. Brief-Spec stores only counters, timestamps, and source
references, so it does not become another transcript archive. The important design decision is
that time only makes a checkpoint eligible. The checkpoint waits until the agent reaches a safe
boundary. We also added a repair guard, which allows one formatting correction and then stops.
Next, we will install the built package into a clean environment, send synthetic events through the
real command, and verify that uninstall removes only files owned by Brief-Spec.

Screen-only proof:
- [direct/pass] `tests/test_hooks.py` → safe-boundary and repair cases passed

Next:
- Run the clean-room installer suite.
<!-- /briefspec -->
```
