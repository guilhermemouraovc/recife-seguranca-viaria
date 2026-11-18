# Outcome examples

## Done

```markdown
<!-- briefspec:outcome:v1 -->
## Outcome Brief

Status: DONE
Outcome: The formatter now preserves comments and passes the repository test suite.
Human action: None

Proof:
- [direct/info] `src/formatter.py:84` — comment nodes are retained during rendering
- [direct/pass] `uv run pytest -q` → 42 passed

Gaps:
- None

Next:
- None

Open:
- None
<!-- /briefspec -->
```

## Review

```markdown
<!-- briefspec:outcome:v1 -->
## Outcome Brief

Status: REVIEW
Outcome: The migration and rollback scripts are implemented and verified against a local fixture.
Human action: Review the migration plan before production execution.

Proof:
- [direct/info] `migrations/20260731_add_state.sql` — forward migration
- [direct/pass] `tests/test_migration.py` → 6 passed

Gaps:
- Production execution has not occurred.

Next:
- Approve or revise the production window.

Open:
- Whether to retain the compatibility column for one release.
<!-- /briefspec -->
```
