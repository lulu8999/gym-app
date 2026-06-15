# Gateway 内置路由机制发现（2026-06-12）

## 关键发现

Gateway 源码 `gateway/run.py` 第8001-8030行已内置了 L1→L2 调用链：

```python
# gateway/run.py _handle_message_with_agent() 第8001行
from agent.router import route_message, detect_and_dispatch_complex
_route_result = route_message(event.text or "")
if _route_result.get("is_complex"):
    _complex_info = detect_and_dispatch_complex(event.text or "")
```

## 两套路由系统对比

| 对比 | Gateway 内置 (`/root/.hermes/hermes-agent/agent/router.py`) | 我们的 L1 (`/root/l123/agent/router.py`) |
|:---|:---|:---|
| 路由目标 | agent 分发（hermes/claude_code/openclaw） | 意图分类（simple/creative/coding/scraping/deployment） |
| 复杂任务 | 创建任务池条目（SQLite） | 拆分子任务 + 分配 handler |
| 已集成 | ✅ 每条消息都调用 | ❌ 未集成 |
| 返回格式 | `{agent, level, reason, confidence, is_complex}` | `{type, intent, handler, subtasks, count}` |

## Gateway 内置函数

### `route_message()` (第200行)
- 输入：用户消息文本
- 输出：agent 路由结果 + is_complex 标记
- 调用链：精确匹配 → 模糊匹配 → LLM fallback

### `detect_and_dispatch_complex()` (第398行)
- 输入：用户消息文本
- 输出：任务池条目 + `tasks_for_delegate` 列表
- 功能：检测复杂任务 → 创建 SQLite 条目 → 返回 delegate_task 可用的任务列表

## 正确集成方案

将我们的 L1 意图分类注入 Gateway 内置的 `route_message()` 函数：

1. 在 `route_message()` 返回值里加 `intent` 字段
2. 调用我们的 `classify_intent()` 函数
3. 结果通过系统提示词传递给 agent

**不要创建新工具** — 工具+系统提示词是「建议」，agent 可以忽略。源码修改才是「强制」。

## 修改文件清单

1. `/root/.hermes/hermes-agent/agent/router.py` — 在 `route_message()` 里注入 L1 意图分类
2. `/root/.hermes/hermes-agent/agent/system_prompt.py` — 引导 agent 使用路由返回的 intent 信息
