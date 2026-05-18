# pyplasmod design documents

**English (default).** Simplified Chinese: [zh-CN/plans/README.md](../zh-CN/plans/README.md).

This directory contains **pyplasmod** architecture notes and user guides for integrators and contributors. For day-to-day onboarding, start at the repository root [README.md](../../README.md).

## Document index

| ID | Title | Audience | Description |
|----|-------|----------|-------------|
| 000 | [Template](pyplasmod-000-template.md) | Contributors | Structure template for new design documents |
| 001 | [HTTP SDK architecture](pyplasmod-001-http-sdk-design.md) | Developers | Module layout, Tier A/B/RPC, configuration, error model |
| 002 | [Tier B HTTP shortcuts](pyplasmod-002-gateway-tier-b-shortcuts-design.md) | Advanced integrators | Extended Admin / internal JSON API naming and route index |
| 003 | [SDK usage guide](pyplasmod-003-sdk-usage-guide.md) | All users | Parameter guidance, scenario examples, troubleshooting |

See also:

- [docs/SDK.md](../SDK.md) — implementation details and API quick reference
- [docs/EMBEDDING.md](../EMBEDDING.md) — gateway embedding and CPU/GPU (`PlasmodEmbedding`)

## Naming convention

```
pyplasmod-<NNN>-<short-name>-design.md
```

| Part | Description | Example |
|------|-------------|---------|
| `pyplasmod` | Project prefix | `pyplasmod` |
| `<NNN>` | Three-digit sequence | `001`, `002` |
| `<short-name>` | Kebab-case topic | `http-sdk` |
| Suffix | Design documents | `-design.md` |

User guides may use the `-usage-guide.md` suffix (e.g. 003).

## Document header (required)

```markdown
# Title

| Metadata | Value |
|----------|-------|
| **Document ID** | pyplasmod-NNN |
| **Status** | Implemented / Draft / Deprecated |
| **Created** | YYYY-MM-DD |
| **Updated** | YYYY-MM-DD |
| **Maintainer** | … |
| **Audience** | … |
```

When adding a document: increment the ID, update the table above, and maintain a **Revision history** section at the end of the body.
