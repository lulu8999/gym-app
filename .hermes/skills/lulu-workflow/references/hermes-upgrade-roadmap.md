# Hermes 升级路线图（2026-06-15）

基于"爆改Hermes：五步直达满配版"视频分析，对比 Lulu 当前配置。

## 当前状态评估

| 维度 | 状态 | 评分 |
|------|------|------|
| 身份记忆 | CLAUDE.md + memory + fact_store（55实体） | ⭐⭐⭐⭐ |
| 长期记忆 | fact_store 支持实体关系、信任评分 | ⭐⭐⭐⭐⭐ |
| 定时任务 | cron 系统完善 | ⭐⭐⭐⭐⭐ |
| Skills 生态 | 100+ 自定义 skill | ⭐⭐⭐⭐ |
| 子代理委派 | delegate_task 并行任务 | ⭐⭐⭐⭐ |
| 多平台接入 | 微信 + 企微 + TUI | ⭐⭐⭐⭐⭐ |
| 三层架构 | VPS + Mac + ESP32 | ⭐⭐⭐⭐⭐ |

## 待升级项

### 1. 深度爬取工具（用户已确认要装）

| 工具 | 作用 | 优先级 |
|------|------|--------|
| Jina Reader | 单页精准抓取，AI 友好输出 | ⭐⭐⭐⭐⭐ |
| Crawl4AI | 批量深度爬取，支持反爬 | ⭐⭐⭐⭐ |
| Scrapling | 反爬绕过 | ⭐⭐⭐ |
| CamoFox | 动态网页渲染 | ⭐⭐⭐ |

**建议**：先装 Jina Reader（最实用）

### 2. Tavily 搜索（用户有 API key，待配置）

- AI 专用搜索引擎，每月 1000 次免费调用
- 配置为"主力搜索 + DuckDuckGo 兜底"双引擎模式
- 用户说"晚点给你 API key"

### 3. Token 成本管控（用户已确认要装）

**推荐方案**：

| 工具 | 作用 | 推荐度 |
|------|------|--------|
| RTK (Rust Token Killer) | 终端输出压缩，省 60-90% | ⭐⭐⭐⭐⭐ |
| Caveman | 模板化输出，进一步压缩到 95-99% | ⭐⭐⭐⭐ |
| 辅助模型配置 | 后台任务用便宜模型 | ⭐⭐⭐⭐⭐ |

**关键发现：辅助模型配置**

Hermes 有 8 个隐藏的后台任务，默认用主模型执行，可以换成便宜模型：
- compression（上下文压缩）— 最费 token
- web extract（网页提取）
- vision（图片分析）
- flush memories（记忆写入）
- session search（会话搜索）
- skills hub（技能搜索）
- MCP dispatch
- approval classification

配置方式：
```yaml
auxiliary:
  compression:
    model: "google/gemini-3-flash-preview"  # 便宜模型
    provider: "openrouter"
```

**参考**：`hermes config set auxiliary.compression.model "gemini-2.0-flash"`

## 执行计划

**第一步（立即可做）**：
- [ ] 安装 Jina Reader
- [ ] 安装 RTK
- [ ] 配置辅助模型（后台任务用便宜模型）

**第二步（等用户 API key）**：
- [ ] 配置 Tavily 搜索

**第三步（可选）**：
- [ ] 安装 Caveman
- [ ] 安装 Crawl4AI
- [ ] 配置 tokscale 监控

## 参考资源

- CSDN 文章：https://blog.csdn.net/u010359778/article/details/160478418
- RTK 仓库：https://github.com/adityahimaone/hermes-agent-rtk-caveman
- Tavily：https://tavily.com
- Hermes 配置文档：https://hermes-agent.nousresearch.com/docs/user-guide/configuration
