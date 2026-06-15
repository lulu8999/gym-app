# L123 插件架构

## 概述

L1+L2 工作流通过 Hermes 插件实现，不修改 Gateway 源码。

## 文件结构

```
~/.hermes/plugins/l123/
├── __init__.py           # 478行：钩子 + 路由 + 记忆 + 工具
├── plugin.yaml           # 插件配置：4钩子 + 2工具
├── route_memory.json     # 路由持久记忆（保留最近500条）
└── recent_routes.log     # 追加模式路由日志（用于快速 tail）
```

## 钩子注册（`register(ctx)`）

```python
def register(ctx) -> None:
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)
    ctx.register_tool(name="l1_route", ...)
    ctx.register_tool(name="l2_plan", ...)
```

## 钩子行为

### pre_gateway_dispatch
- 每一条网关消息都执行 L1 路由
- 返回 `{"action": "rewrite", "text": "[L1:type/intent] 原始消息"}` 
- 在消息文本前注入路由标签，agent 处理时始终知道意图分类
- 仅对有文本的 MessageEvent 生效

### pre_llm_call
- 每一次 LLM 调用前注入 L1/L2 框架指令
- 返回 `{"context": "..."}` 注入到 LLM 上下文
- 包含：`_L1_L2_FRAMEWORK` + 当前路由结果 + 记忆回放 + L2 状态
- 第一条消息注入完整指令，后续消息注入精简提醒

### on_session_start
- 记录会话开始时间，写入 route_memory.json

### on_session_end
- 统计本轮会话的路由分布，写入 route_memory.json

## 🔴 import 路径问题

插件代码使用：
```python
from agent.router import router
```
但这会命中 **Hermes 自带的 `agent/router.py`**（587行），不是自定义 L1 router（328行）。

**原因**：Hermes 网关运行时 `agent` 包已在 `sys.modules` 中。即使 `sys.path.insert(0, '/root/l123')`，`from agent.router` 仍然解析到 Hermes 内置路径 `~/.hermes/hermes-agent/agent/router.py`。

**修复方案**：用绝对路径加载：
```python
import importlib.util
spec = importlib.util.spec_from_file_location(
    "l1_router", "/root/l123/agent/router.py"
)
router_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router_mod)
router = router_mod.router
```

## 记忆系统

### 当前实现（本地 JSON）
- `route_memory.json` — 500 条上限，保留最近
- `recent_routes.log` — 追加模式，用于快速 tail

### 待办：写入 Hermes 正式记忆
插件应调用 `memory(action="add", ...)` 或 `fact_store(action="add", ...)` 来在每次路由后写入持久记忆。这样跨会话的记忆强化才能实现。

## 插件加载验证

插件是否正在运行：
```bash
# 检查路由日志
tail -3 ~/.hermes/plugins/l123/recent_routes.log

# 检查 route_memory.json 最近的条目
python3 -c "
import json
d = json.load(open('/root/.hermes/plugins/l123/route_memory.json'))
print(f'Total entries: {len(d)}')
print(f'Last route: {d[-1]}')
"

# 检查 config 是否启用
grep 'l123' ~/.hermes/config.yaml
```
