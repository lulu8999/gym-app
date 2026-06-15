# L1 插件 Slash 命令实现细节

## 2026-06-13 实现

### 文件位置

`~/.hermes/plugins/l123/__init__.py` — 在 `_on_pre_gateway_dispatch` 函数开头插入

### 代码结构

```python
# ── Slash 命令支持 ─────────────────────────────────────────────
_SLASH_COMMANDS = {
    "/model": {
        "desc": "显示当前模型配置",
        "rewrite": "[L1:simple] 查看当前模型配置",
    },
    "/help": {
        "desc": "显示可用命令",
        "rewrite": "[L1:simple] 显示可用命令",
    },
    "/stop": {
        "desc": "停止当前任务",
        "action": "abort",
    },
    "/new": {
        "desc": "开始新会话",
        "action": "new_session",
    },
    "/retry": {
        "desc": "重试上一条消息",
        "rewrite": "[L1:simple] 重试上一条消息",
    },
    "/undo": {
        "desc": "撤销上一条回复",
        "rewrite": "[L1:simple] 撤销上一条回复",
    },
}


def _handle_slash_command(
    cmd: str,
    event=None,
    gateway=None,
    session_store=None,
) -> Optional[dict]:
    """处理 slash 命令，返回网关动作或 None（未识别）"""
    info = _SLASH_COMMANDS.get(cmd)
    if not info:
        return None

    cmd_log = cmd.split()[0]

    if info.get("action") == "abort":
        # /stop — 尝试终止当前执行
        try:
            if gateway and hasattr(gateway, "cancel_current_run"):
                gateway.cancel_current_run()
                logger.info("Slash command: /stop → canceled current run")
            elif gateway and hasattr(gateway, "agent_executor"):
                gateway.agent_executor.cancel()
                logger.info("Slash command: /stop → agent executor canceled")
            else:
                logger.warning("Slash command: /stop → no cancel method available on gateway")
        except Exception as exc:
            logger.warning("Slash command: /stop → failed to cancel: %s", exc)
        return {
            "action": "rewrite",
            "text": "[system:stop] 已停止当前任务",
            "stop_processing": True,
        }

    if info.get("action") == "new_session":
        # /new — 尝试新建会话
        try:
            if gateway and hasattr(gateway, "start_new_session"):
                gateway.start_new_session(event)
                logger.info("Slash command: /new → new session started")
            elif session_store and hasattr(session_store, "create"):
                session_store.create()
                logger.info("Slash command: /new → session store create")
            else:
                logger.warning("Slash command: /new → no session method available")
        except Exception as exc:
            logger.warning("Slash command: /new → failed: %s", exc)
        return {
            "action": "rewrite",
            "text": "[system:new_session] 已开始新会话",
        }

    # 普通命令：改写为自然语言
    rewrite = info.get("rewrite")
    if rewrite:
        logger.info("Slash command: %s → %s", cmd_log, rewrite.split("] ")[-1])
        return {"action": "rewrite", "text": rewrite}

    return None
```

### 在 `_on_pre_gateway_dispatch` 中的插入点

```python
def _on_pre_gateway_dispatch(event=None, gateway=None, session_store=None, **kwargs):
    if not event or not hasattr(event, "text") or not event.text:
        return None

    text = event.text.strip()

    # ── Slash 命令检测 ─────────────────────────────────────
    if text.startswith("/"):
        cmd = text.split()[0].lower()
        result = _handle_slash_command(cmd, event=event, gateway=gateway, session_store=session_store)
        if result:
            return result
        # 未识别的 /xxx 命令 — fallthrough 到 L1 路由

    if not text:
        return None
    # ... 后续 L1 路由逻辑不变
```

### 关键设计决策

1. **检测时机**：在 `text = event.text.strip()` 之后、`if not text:` 之前插入。确保斜杠命令在 L1 路由前被拦截。
2. **return result**：返回 `{"action": "rewrite", "text": new_text}` — 和 L1 路由的返回值格式一致，gateway 看到 rewrite 动作就不再走后续 L1 处理。
3. **stop_processing**：对 `/stop` 加了 `stop_processing: True` 标记，告诉 gateway 可以停止当前会话处理（取决于 gateway 是否实现此字段）。
4. **fallthrough**：不识别的 `/xxx` 命令走自然语言处理，不会报错。
5. **异常安全**：所有 gateway 方法调用都有 try-except 保护，不会因方法不存在而崩溃。

### 测试验证

重启 gateway 后，在微信上发 `/model` 应返回模型配置信息，不再被 L1 路由拦截。