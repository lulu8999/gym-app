# L123 Intent Routing — Multi-Agent Task Dispatch

> 三层路由架构：把用户消息按意图自动分派到对应 Agent（Claude Code / OpenClaw / Hermes 自处理）

## 架构总览

```
用户消息
  │
  ▼ L1: 精确关键词匹配 (<10ms)
  │  routing.yaml → exact_match
  │  命中 → 直接路由
  │  未命中 ↓
  │
  ▼ L2: 正则模糊匹配 (<50ms)
  │  routing.yaml → fuzzy_match
  │  命中 → 路由到对应 Agent
  │  未命中 ↓
  │
  ▼ L3: LLM 兜底判断
  │  ~10% 的复杂/模糊消息
  │  prompt-based 意图识别
```

**复杂任务自动拆分**：命中 `complex_task_patterns`（含"并/然后/接着/再"等连接词）→ 触发 L2 任务拆分

## 文件结构

| 路径 | 角色 | 状态 |
|------|------|------|
| `~/.hermes/config/routing.yaml` | 路由规则配置（关键词/正则/复杂模式） | ✅ 持久化 |
| `~/.hermes/admin/app.py` | Flask 看板 + kanban API 路由 | ✅ Flask 应用 |
| `~/.hermes/admin/templates/kanban.html` | 看板前端页面 | ✅ |
| `~/.hermes/admin/static/kanban.js` | 拖拽逻辑 + 触屏支持 | ✅ |
| `~/.hermes/agent/router.py` | L1-L2-L3 路由逻辑 | 🔲 实现层（可清除重建） |
| `~/.hermes/agent/task_pool.py` | SQLite 任务持久化 | 🔲 同上 |
| `~/.hermes/agent/kanban.py` | 任务执行引擎 | 🔲 同上 |
| `~/.hermes/agent/splitter.py` | 复杂任务拆分 | 🔲 同上 |
| `~/.hermes/agent/reporter.py` | 停止回调 + 报告 | 🔲 同上 |

## routing.yaml 配置结构

```yaml
exact_match:
  claude_code: ["写代码", "写报告", "部署", ...]
  openclaw: ["查网页", "搜索", "下载", "查天气", ...]

fuzzy_match:
  claude_code:
    - pattern: "^写.*(脚本|代码|程序)"
    - pattern: ".*(生成|写|整理).*(报告|文档|总结)"
  openclaw:
    - pattern: "^查(?!数据库|代码)"
    - pattern: ".*(天气|新闻|热点)"

complex_task_patterns:
  - pattern: ".*并.*"     # 查天气并写报告
  - pattern: ".*然后.*"   # 查数据然后分析
  - pattern: ".*接着.*"   # 下载文件接着处理

llm_fallback:
  enabled: false
  prompt: "判断路由：代码类→claude_code，网页类→openclaw，其他→hermes"
```

## Agent 路由分配规则

| Agent | 关键词类 | 使用场景 |
|-------|---------|---------|
| **claude_code** | 代码/脚本/部署/数据库/SQL/报告/文档/调试 | 代码编写、报告生成、数据分析 |
| **openclaw** | 网页/搜索/下载/天气/新闻/浏览器/爬虫/截图 | 信息获取、浏览器操作 |
| **hermes** | 其他或不确定 | 日常对话、配置操作、简单任务 |

## 看板（L3）集成

- **接口**: `/kanban` → kanban 看板页面
- **API**: `/api/kanban/agents`, `/api/kanban/tasks`, `/api/kanban/agent/<name>/stop` 等
- **Lazy import 模式**: Flask app 中 agent 模块用函数内延迟导入，启动时不阻塞
- **移动端**: kanban.js 支持 touch 事件 + 长按激活拖拽

## 回滚策略

> "保留框架，别的恢复原状"

需要清理实现层时：
1. **保留**: `routing.yaml`（配置骨架）、`admin/app.py`（kanban 路由）、看板前端文件
2. **清除**: `agent/` 下所有模块（router.py, task_pool.py, kanban.py, splitter.py, reporter.py）
3. **验证**: 原管理页面（登录/用户/cron）不受影响（lazy import 不会报错）

## 已知 Pitfalls

- ❌ agent 模块未实现时访问 `/kanban` 会 500（lazy import 找不到模块）
- ❌ 子任务路由默认都走 hermes，需要在 router.py 的 complex_task dispatch 里按关键词分给 OC/CC
- ❌ admin-panel 和 location-server 可能端口冲突（确保不同端口）
- ✅ 关键词可动态调整：直接改 routing.yaml 后重启 admin-panel 即可
