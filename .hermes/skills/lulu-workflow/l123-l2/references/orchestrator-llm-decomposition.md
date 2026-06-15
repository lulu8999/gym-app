# L2 Orchestrator LLM Decomposition — Implementation Details

## 核心方法：plan_from_text()

**文件**：`/root/l123/agent/orchestrator/orchestrator.py`

**功能**：用 DeepSeek LLM 理解任务意图并生成执行计划，替代旧版按标点符号切句。

### 调用链

```
gateway/run.py (L8619-8665)
  → importlib 加载 /root/l123/agent/orchestrator/orchestrator.py
  → orchestrator.plan_from_text(event.text, l1_route)
    → litellm.completion(model="openai/deepseek-chat", ...)
    → 解析 JSON 返回值
    → 为每步补全 action/toolsets/goal
    → 返回 {total, project_type, plan}
```

### DeepSeek API 配置

```python
def _get_deepseek_key() -> str:
    try:
        with open("/root/.claude/settings.json") as f:
            return json.load(f).get("apiKey", "")
    except Exception:
        return ""
```

调用参数：
```python
response = litellm.completion(
    model="openai/deepseek-chat",
    messages=[{"role": "system", "content": _DECOMPOSE_SYSTEM}, {"role": "user", "content": prompt}],
    max_tokens=800,
    temperature=0.1,
    api_key=_get_deepseek_key(),
    api_base="https://api.deepseek.com/v1",
)
```

### 系统提示词（_DECOMPOSE_SYSTEM）

设计要点：
- 限制 3-6 步（太少无意义，太细碎失去编排价值）
- 强调"理解意图"而非"机械切句"
- 每步指定 handler 让 agent 知道谁来执行
- 返回纯 JSON，通过 `_parse_json()` 容错提取

### 容错机制

1. **litellm 未安装** → `ImportError` → `_fallback_plan()`
2. **API 调用失败** → `Exception` → `_fallback_plan()`
3. **JSON 解析失败** → `_parse_json()` 尝试清洗（去 markdown 代码块、提取 `{...}` 块）→ 失败则 `_fallback_plan()`

### 降级方案 _fallback_plan()

```python
keywords_map = {
    "数据库": "设计数据库模型", "api": "实现API接口",
    "前端": "实现前端页面", "页面": "实现前端页面",
    "部署": "部署上线", "测试": "编写测试", "爬虫": "编写爬虫",
}
```

在用户消息中检测关键词 → 按出现顺序生成步骤 → 默认 `claude_code` handler。

### 测试验证

```bash
cd /root/l123 && python3 -c "
from agent.orchestrator.orchestrator import orchestrator
msg = '帮我写一个健身管理网页，能够记录健身动作与组数，同时记录心情，记录每次体重，引入常用食谱，支持用户登录使用'
result = orchestrator.plan_from_text(msg, {'intent': 'coding', 'handler': 'claude_code', 'is_complex': True})
for s in result['plan']:
    print(f'  Step {s[\"step\"]}: [{s[\"handler\"]}] {s[\"task\"]}')
"
```

### 与旧版对比

| | 旧版 plan() | 新版 plan_from_text() |
|---|---|---|
| 输入 | L1 的 `subtasks` 列表 | 用户原始消息 + L1 route |
| 拆分方式 | 按 handler 映射 | DeepSeek LLM 理解 |
| 步骤质量 | 语义碎片 | 逻辑步骤链 |
| LLM 依赖 | 无 | DeepSeek（有降级） |
| project_type | 无 | 返回项目类型 |
