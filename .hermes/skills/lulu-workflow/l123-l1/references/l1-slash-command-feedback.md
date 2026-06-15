# L123 斜杠命令反馈机制问题

## 问题（2026-06-13 发现）

用户输入 `/new`、`/model` 等斜杠命令后，**没有系统提示反馈**，看起来像没反应。

## 根因

L123 插件的 `_on_session_start()` 钩子（`__init__.py` 第419-439行）只记录日志到 `route_memory.json`，**不返回消息给用户**。

```python
def _on_session_start(session_id="", platform="", user_id="", **kwargs):
    """on_session_start — 初始化会话级路由状态。"""
    _ensure_memory_dir()
    memory = _load_memory()
    memory.append({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "session_start",
        "session_id": session_id,
        "platform": platform,
    })
    _save_memory(memory)
    logger.info("L123 session started: %s (%s)", session_id, platform)
    # 注意：没有 return，所以不会给用户发消息
```

而 `/new` 命令的处理在 `_handle_slash_command()` 中（第258-274行）：

```python
if info.get("action") == "new_session":
    # 尝试新建会话
    gateway.start_new_session(event)
    return {
        "action": "rewrite",
        "text": "[system:new_session] 已开始新会话",
    }
```

这条 `[system:new_session]` 消息被注入到对话中，但**用户看不到**——因为 WeChat 平台可能过滤了 `[system:xxx]` 前缀的消息，或者消息被重写后没有发送给用户。

## 影响

- `/new` → 看起来没反应（实际会话已重置）
- `/stop` → 看起来没反应（实际已停止）
- `/model` → 看起来没反应（实际已重写为查询）

## 待修复方案

### 方案1：让 `on_session_start` 返回欢迎消息（推荐）

```python
def _on_session_start(session_id="", platform="", user_id="", **kwargs):
    # ... 现有日志逻辑 ...
    return {"text": "✨ 新会话已开始！有什么可以帮你的？"}
```

### 方案2：在 `_handle_slash_command` 中直接发送确认

修改 `new_session` 分支，让返回的 `text` 不带 `[system:]` 前缀：

```python
return {
    "action": "rewrite",
    "text": "✨ 新会话已开始",  # 去掉 [system:new_session] 前缀
}
```

### 方案3：在网关层处理

在 `gateway/run.py` 中，检测到 slash 命令的 rewrite 结果后，直接发送确认消息给用户。

## 注意

- 这个问题**不影响 L123 路由功能**，路由仍然正常工作
- 只影响用户感知——以为命令没生效
- 修复后需要测试 WeChat 平台是否能正常显示反馈消息
