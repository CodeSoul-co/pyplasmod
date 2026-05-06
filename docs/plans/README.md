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
| `<short-name>` | Kebab-case summary | `connection-manager` |
| `-design.md` | Suffix | `-design.md` |

Examples:
- `pyplasmod-001-global-client-design.md`
- `pyplasmod-002-connection-manager-design.md`

Use `pyplasmod-000-template.md` as a starting point for new documents.

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
| 001 | [Global Client Design](pyplasmod-001-global-client-design.md) | @bigsheeper | 2026-01-28 |
| 002 | [Connection Manager Design](pyplasmod-002-connection-manager-design.md) | @XuanYang-cn | 2026-02-03 |
