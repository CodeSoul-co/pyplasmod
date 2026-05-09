# Design Documents

Design documents for PyPlasmod features and architectural changes.

## Naming Convention

```
pyplasmod-<NNN>-<short-name>-design.md
```

| Part | Description | Example |
|------|-------------|---------|
| `pyplasmod` | Project prefix | `pyplasmod` |
| `<NNN>` | Sequential number, zero-padded to 3 digits | `001`, `002` |
| `<short-name>` | Kebab-case summary | `http-sdk` |
| `-design.md` | Suffix | `-design.md` |

Examples:

- `pyplasmod-001-http-sdk-design.md`
- `pyplasmod-002-<feature>-design.md`

Use [`pyplasmod-000-template.md`](pyplasmod-000-template.md) as a starting point for new documents.

## Required Header

Every design document must start with:

```markdown
# [Title]

- **Created:** YYYY-MM-DD
- **Updated:** YYYY-MM-DD
- **Author(s):** @github-handle
```

## Index

| Number | Title | Author | Created |
|--------|-------|--------|---------|
| 000 | [Template](pyplasmod-000-template.md) | — | — |
| 001 | [HTTP SDK (Tier A + binary RPC)](pyplasmod-001-http-sdk-design.md) | @CodeSoul-co | 2026-05-06 |
| 002 | [Gateway Tier B JSON shortcuts](pyplasmod-002-gateway-tier-b-shortcuts-design.md) | @CodeSoul-co | 2026-05-08 |

When adding a new design, increment the number, add a row to the table, and keep **Created** / **Updated** in the document body in sync with substantive edits.
