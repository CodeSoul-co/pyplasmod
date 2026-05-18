# pyplasmod 设计文档

本目录收录 **pyplasmod** 的架构说明与用户指南，供集成开发者与贡献者查阅。日常上手请从仓库根目录 [README.md](../../README.md) 开始。

## 文档索引

| 编号 | 标题 | 受众 | 说明 |
|------|------|------|------|
| 000 | [模板](pyplasmod-000-template.md) | 贡献者 | 新建设计文档时的结构模板 |
| 001 | [HTTP SDK 架构说明](pyplasmod-001-http-sdk-design.md) | 开发者 | 模块划分、Tier A/B/RPC、配置与错误模型 |
| 002 | [Tier B HTTP 快捷方法说明](pyplasmod-002-gateway-tier-b-shortcuts-design.md) | 高级集成 | 扩展 Admin / internal JSON API 命名与路由索引 |
| 003 | [SDK 用户指南](pyplasmod-003-sdk-usage-guide.md) | 所有用户 | 参数填法、场景样例、排错 |

另请参阅：[docs/SDK.md](../SDK.md)（实现细节与 API 速查）。

## 命名规范

```
pyplasmod-<NNN>-<short-name>-design.md
```

| 部分 | 说明 | 示例 |
|------|------|------|
| `pyplasmod` | 项目前缀 | `pyplasmod` |
| `<NNN>` | 三位序号 | `001`、`002` |
| `<short-name>` | 短横线主题 | `http-sdk` |
| 后缀 | 设计类文档 | `-design.md` |

用户指南可使用 `-usage-guide.md` 后缀（如 003）。

## 文档头（必填）

```markdown
# 标题

| 元数据 | 值 |
|--------|-----|
| **文档编号** | pyplasmod-NNN |
| **状态** | 已实现 / 草案 / 已废弃 |
| **创建** | YYYY-MM-DD |
| **更新** | YYYY-MM-DD |
| **维护方** | … |
| **读者** | … |
```

新增文档时：递增编号、更新上表、在正文末尾维护「修订记录」。
