# L2 不触发常见原因及排查

## 问题1：is_complex 门槛过高

**现象**：
- 消息被 L1 正确分类（如 `deployment → claude_code`）
- 但 gateway.log 中没有 `L2 plan:` 日志
- 因为 `router.route()` 返回 `is_complex=False`

**根因**：`agent/router.py` 的 `_split_subtasks()` 函数依赖文本中存在 `\n` 或中文逗号 `，` 作为分隔符：
```python
# 只有分隔符才触发拆分
if '\n' in user_msg or '，' in user_msg:
    parts = re.split(r'[\n，]+', user_msg)
```

**受影响的消息类型**：
- 「帮我写爬虫+部署+测试」→ 无分隔符，不拆分 ❌
- 「帮我写爬虫，部署，测试」→ 有逗号，拆分 ✅
- 「帮我写一个 Python 天气查询脚本，要求支持命令行输入城市名、调用 API、输出彩色表格」→ 有逗号但不是任务拆分 ❌

**验证命令**：
```bash
cd /root/.hermes/hermes-agent && venv/bin/python3 -c "
from agent.router import router
for msg in [
    '帮我写爬虫+部署+测试',
    '帮我写爬虫，部署，测试',
]:
    r = router.route(msg)
    print(f'{msg[:20]:20s} → complex={r.get(\"is_complex\")} subtasks={r.get(\"subtasks\")}')
"
```

**修复方向**：
1. 调低 `is_complex` 判定门槛（不一定依赖文本分隔符）
2. 用 LLM 辅助判断复杂度
3. 增加关键词触发（如含「部署」「测试」「定时」等关键词时自动判复杂）

### ✅ 实际修复（2026-06-13）

**问题**：对话中用户说「检查以上所有任务有没有践行l123工作流程」→ L1 判 `simple`，不走 L2。

**根因**：消息长度 31 字 > 6 字门槛，但 `_split_subtasks()` 内部对连接词匹配后降级（只有 1 个任务 → 降为 simple）。复杂任务按关键词匹配时只有 1 个意图。

**修复**：
1. 长消息（>15 字）且有编程/部署/多重关键词时，自动判 is_complex=true
2. 即使只有 1 个 subtask，只要任务本身复杂（含「编译」「构建」「测试」「部署」「集成」等词），不降级
3. 更新 routing.yaml 增加多关键词复合模式

## 问题2：AI 自提任务不走 L2

**场景**：
1. Agent（我）在回复中说「帮你写一个天气脚本+部署+定时」
2. 用户回复「做」
3. 网关只看到用户消息 `event.text = '做'` → L1 判 `simple`
4. 实际复杂任务文本从未经过 L1/L2 管道

**根本原因**：L1/L2 只在 `_handle_message_with_agent()` 中对用户消息生效。Agent 自己输出的文本不经过这个入口。

### ✅ 方案1：Agent 内部自举（推荐，已可实施）

当 agent 从用户上下文看出即将执行复杂任务时（如用户说"开搞""做吧""可以"这样只有一两个字的确认），**不要直接执行**，而是：

1. 用 `session_search` 查找**上一条用户消息**中找到完整的任务描述
2. 把完整任务文本手动送入 L1 路由和 L2 编排器
3. 按 L2 plan 逐步执行

```python
# Agent 内部 — 收到"做"/"开搞"/"继续"后
# 1. 找原始任务（从 session 或上下文）
original_task = "帮我写爬虫+部署+测试"
  
# 2. 走 L1
from agent.router import router
l1_result = router.route(original_task)
  
# 3. 判 complex 则走 L2
if l1_result.get('is_complex'):
    from agent.orchestrator import orchestrator
    plan = orchestrator.plan_from_text(original_task, l1_result)
    # 按 plan 逐步执行...
```

### ✅ 方案2：回复中注入 L2 铁律提示

当 agent 主动提议复杂任务时，在回复末尾注入触发词提醒，让用户回复时能把完整任务带回来：

```
✅ 修复方案：
1. 开发环境配数据库
2. 写 API 接口
3. 部署到测试服

（如果要执行，直接回复「做吧」或「开始修复」）
```

### 方案对比

| 方案 | 优点 | 缺点 | 推荐 |
|------|------|------|:----:|
| 方案1：内部自举 | 不改网关代码 | 需从上下文取原始任务 | ✅ 优先 |
| 方案2：注入触发词 | 零改动 | 依赖 L1 关键词匹配 | ➖ 兜底 |

## 排查步骤

```bash
# 1. 看最近 L1 分类 + 是否有 L2
grep "L1 route\|L2 plan" /root/.hermes/logs/gateway.log | tail -20

# 2. 针对特定消息看 is_complex 值
cd /root/.hermes/hermes-agent && venv/bin/python3 -c "
from agent.router import router
msg = '你的消息'
r = router.route(msg)
print('intent:', r.get('intent'))
print('is_complex:', r.get('is_complex'))
print('subtasks:', r.get('subtasks'))
"
```
