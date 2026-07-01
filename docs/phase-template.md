# Phase Template

Copy this structure when preparing or closing a new project phase.

## Phase Title

Short name of the phase.

## Objective

State the concrete outcome expected from the phase.

Example:

```text
Validate that Gold and restitution transformations produce deterministic output
from a fixed Silver fixture.
```

## Scope

In scope:

- ...

Out of scope:

- ...

## Constraints

- Keep on-premise behavior working.
- Respect `AGENTS.md`.
- Respect `cadrage.md`.
- Keep transformations pure and reusable.
- Avoid over-engineering and parallel structures.
- Do not claim runtime validation without proof.

## Start Checklist

Before implementation:

- [ ] Read `AGENTS.md`.
- [ ] Read `cadrage.md`.
- [ ] Read `docs/phase-handoff.md`.
- [ ] Inspect relevant current files with `rg` and direct reads.
- [ ] Identify the exact files expected to change.
- [ ] Identify validation commands before editing.
- [ ] Confirm what is already implemented, prepared, or unproven.

## Implementation Notes

Document the intended approach in a few bullets:

- ...

## Acceptance Criteria

- [ ] ...
- [ ] ...
- [ ] Documentation updated if architecture or practices changed.
- [ ] `docs/phase-handoff.md` updated at the end of the phase.

## Validation Plan

Static/unit checks:

- ...

Runtime checks, if applicable:

- ...

Checks not run and reason:

- ...

## End-of-Phase Summary

Completed:

- ...

Changed files:

- ...

Validation results:

- ...

Still not proven:

- ...

Next recommended phase:

- ...

Rules or docs updated:

- ...

Suggested commit message:

```text
<type>: <short imperative summary>
```

Keep it simple and synthetic. Prefer a conventional prefix such as `feat:`,
`fix:`, `docs:` or `chore:` when it clarifies the change, and avoid long
multi-topic paragraphs.
