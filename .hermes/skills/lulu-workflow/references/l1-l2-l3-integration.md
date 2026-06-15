# Hermes L1+L2+L3 协同作战架构

> 版本：v1.3
> 日期：2026-06-12
> 设计师：小小陆

---

## 2026-06-12 迭代记录

### 重大里程碑：L1 路由在网关层强制执行

**之前的问题**（2026-06-11）：L1 路由代码（`agent/router.py`）和工具（`tools/l1_route.py`）都写好了，但 agent 经常跳过不调用——**工具+提示词 ≠ 强制执行**。

**解决方案**：直接改 Gateway 消息入口源码（`gateway/run.py` 第58行 + 第8609-8614行）：

```python
# 入口 import
from hermes_agent.agent.router import router  # L1

# 在 _handle_message_with_agent() 中，agent 调用前注入：
try:
    route_result = router.route(event.text or '')
    event.metadata['l1_route'] = route_result
except Exception:
    logger.debug('L1 route failed', exc_info=True)
```

**效果**：每条用户消息到达网关时，自动执行 L1 路由分析并存入 `event.metadata`，agent 处理消息时可直接读取，不再依赖自觉调用。

**安全措施**：`try/except` 包裹，L1 路由失败只记日志、不中断消息处理。

## 2026-06-11 迭代记录

### 新增：L1 意图路由正式实现

**背景**：之前 `routing.yaml` 和 `agent/__init__.py` 只是框架，这次真正实现了 `agent/router.py`

**核心实现**：`IntentRouter` 类（205 行，单文件无依赖）

**路由逻辑**：
```
用户消息 → classify_intent() → 判断意图类型
           ├── simple    → hermes_direct（Hermes 直接干）
           ├── creative  → delegate_to_hermes_llm（Hermes + LLM 生成）
           ├── coding    → delegate_to_claude_code（→ Claude Code）
           ├── scraping  → delegate_to_openclaw（→ OpenClaw）
           ├── deployment→ delegate_to_claude_code（→ Claude Code）
           └── complex   → 按连接词拆分 → 逐条再路由
```

**使用方式**：
```python
from agent.router import router

# 简单任务
result = router.route("查天气")
# → {"type": "simple", "intent": "simple", "action": "hermes_direct", "handler": "hermes"}

# 复杂任务
result = router.route("查天气并写报告")
# → {"type": "complex", "subtasks": [
#       {"task": "查天气", "intent": "simple", "handler": "hermes"},
#       {"task": "写报告", "intent": "creative", "handler": "hermes_llm"}
#   ], "count": 2}
```

**架构决策**：
1. **配置驱动**：路由规则从 `config/routing.yaml` 读取，不改代码就能调优关键词和意图
2. **优先级排序**：coding → deployment → scraping → creative → simple（deployment 必须在 scraping 前，否则"部署个网站"因含"网站"被误判为爬虫）
3. **复杂任务拆分**：用 `re.split(r"(?:并|然后|之后|接着|同时|并且|再|随后)", msg)` 切分，每个子任务重新跑 classify_intent
4. **无 pyyaml 兜底**：内建了一个极简 YAML 解析器用于无 pyyaml 环境
5. **单例模式**：导入即用的全局 `router` 实例

**已知限制**：
- "写个Python脚本"因含"写"被匹配到 creative（"写"在 creative 关键词里排得早）
- 解决方案：给 coding 加 `"脚本"` 关键词到 routing.yaml 即可

---

## 架构概览

```
用户消息
    │
    ├── L1: 意图路由 ──────┐
    │ (agent/router.py)    │
    │ 关键词匹配+优先级排序 │
    │ 复杂任务按连接词拆分  │
    │                      ▼
    │              ┌────────────┐
    │              │  任务池    │
    │              │  (SQLite)  │
    │              └────────────┘
    │                      │
    ├── L2: 看板执行 ◄──────┤
    │ (拆分/并行/串行)      │
    │                      ▼
    │              ┌────────────┐
    │              │  可视化面板  │
    │              │  (拖拽+连线) │
    └── L3: 监控面板 ◄─────────┘
```

---

## L1: 意图路由

**功能**：判断用户意图 → 决定执行策略（自己干 or 分发出去）

**核心文件**：
- `config/routing.yaml` — 意图规则配置（关键词/模式/handler）
- `agent/router.py` — 路由执行器

**优先级陷阱**（2026-06-11 教训）：
```
关键词匹配顺序是 priority list 顺序：
  coding → deployment → scraping → creative → simple

如果 deployment 排在 scraping 后面，"部署个网站"会因"网站"先匹配 scraping。
解决方案：deployment 必须排在 scraping 前面。
```

**可调优参数**：
- `routing.yaml` 的 `intent_types[n].keywords` — 增减关键词
- `agent/router.py` 的 `priority` 列表 — 调匹配优先级
- `agent/router.py` 的 `separators` 正则 — 改复杂任务分隔符

---

## L2: 看板执行

**功能**：复杂任务拆分为卡片，并行/串行执行

**核心组件**（待实现）：
- `TaskPool` - 任务池（SQLite 持久化）
- `KanbanBoard` - 看板
- `KanbanCard` - 卡片（子任务）
- `Splitter` - 任务拆分器
- `Merger` - 结果合并

**状态**：`pending` → `doing` → `done` / `failed` / `stopped`

---

## L3: 可视化面板

**功能**：Web 面板展示 Agent 状态，支持拖拽控制

**访问地址**：https://admin.lulugame.fun/kanban

**交互设计**：
- **Agent 方块** - 拖拽式卡片，显示状态
- **协作连线** - SVG 动态绘制任务关系
- **停止区域** - 拖入即停止任务
- **通知机制** - Hermes 报告任务状态变化

**技术栈**：
- 后端：Flask（集成到 admin 面板，端口 9802）
- 前端：原生 JS + HTML5 Drag & Drop + SVG
- 状态轮询：每 3 秒

---

## 数据流

| 步骤 | 操作 | 写入/读取 |
|------|------|----------|
| 1 | 用户发送复杂任务 | - |
| 2 | L1 识别 → 触发 L2 | - |
| 3 | L2 创建任务池记录 | 写入 SQLite |
| 4 | L2 执行卡片 | 更新状态 |
| 5 | L3 轮询读取 | 读取 SQLite |
| 6 | 用户拖入停止区 | - |
| 7 | 后端停止任务 | 更新 SQLite |
| 8 | Hermes 检测事件 | 读取 SQLite |
| 9 | Hermes 生成报告 | 发送微信 |

---

## 文件结构

```
~/.hermes/
├── config/
│   └── routing.yaml          # L1 路由配置（211行）
├── agent/
│   ├── router.py              # L1 核心路由（205行 ✅ 已实现）
│   ├── kanban.py              # L2 看板引擎（待实现）
│   ├── splitter.py            # L2 任务拆分（待实现）
│   └── task_pool.py           # L2 任务池（待实现）
~/admin/
├── app.py                     # L3 后端 API
├── templates/
│   ├── index.html             # 管理面板首页（含看板入口）
│   └── kanban.html            # L3 前端页面
└── static/
    └── kanban.js              # L3 拖拽逻辑（桌面+移动端）
```

---

## 协同触发条件

| 场景 | 行为 |
|------|------|
| "查天气" | L1→simple → Hermes 直接查 |
| "写个Python脚本" | L1→creative（因"写"关键词，需加"脚本"调优） → Hermes+LLM |
| "爬豆瓣电影" | L1→scraping → OpenClaw |
| "部署个网站" | L1→deployment → Claude Code |
| "查天气并写报告" | L1 识别 complex → 拆[查天气(hermes), 写报告(hermes_llm)] → L2 执行 |
| "爬数据然后存数据库" | L1→complex → 拆[爬数据(openclaw), 存数据库(hermes)] |
| 拖 Agent 方块到停止区 | L3 触发停止 → 更新任务池 → Hermes 检测 → 报告 |

---

## ⚠️ 关键教训

### L1→L2 集成断点（2026-06-10）
**问题**：routing.yaml 配置了好规则，但代码没调用 → 复杂任务没触发 L2

**验证方法**：
1. 发"查天气并写报告"
2. 检查 SQLite：`SELECT * FROM tasks ORDER BY created_at DESC`
3. 没新记录 → 断点

**教训**：多组件集成项目，必须验证**连接点**是否工作

### 关键词优先级陷阱（2026-06-11）
**问题**："部署个网站"因"网站"关键词误匹配到 scraping

**原因**：scraping 的 `keywords` 含"网站"，检查顺序在 deployment 前

**教训**：priority list 必须按具体到通用排序，deployment 放 scraping 前面

---

## 验证命令

```bash
# L1 路由测试
cd /root/l123
python3 -c "
from agent.router import router
tests = ['查天气', '写篇文章', '爬豆瓣', '部署个网站', '查天气并写报告']
for msg in tests:
    result = router.route(msg)
    print(f'{msg} → {result[\"type\"]}: intent={result[\"intent\"]}, handler={result.get(\"handler\", \"N/A\")}')
    if result.get('subtasks'):
        for st in result['subtasks']:
            print(f'  子: {st[\"task\"]} → {st[\"handler\"]}')
"
```