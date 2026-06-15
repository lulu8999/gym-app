# Hermes Plugin Hooks API 参考

## Hook 类型

| Hook 名称 | 触发时机 | 回调参数 | 返回值 |
|-----------|---------|---------|--------|
| `pre_tool_call` | 工具执行前 | `(tool_name, args, **kwargs)` | `None`(放行) 或 `{"action": "block", "message": "..."}` |
| `transform_tool_result` | 工具结果返回前 | `(tool_name, args, result, **kwargs)` | `None`(不变) 或 `str`(替换结果) |
| `post_tool_call` | 工具执行后 | `(tool_name, args, result, error, **kwargs)` | `None` |

## plugin.yaml 格式

```yaml
name: my-plugin
version: "1.0.0"
description: "描述"
hooks:
  - pre_tool_call
  - transform_tool_result
```

## __init__.py 注册入口

```python
def register(ctx) -> None:
    ctx.register_hook("pre_tool_call", my_handler)
```

## 获取会话上下文

```python
from gateway.session_context import get_session_env

platform = get_session_env("HERMES_SESSION_PLATFORM")  # "weixin", "telegram", etc.
user_id = get_session_env("HERMES_SESSION_USER_ID")     # 用户唯一 ID
chat_id = get_session_env("HERMES_SESSION_CHAT_ID")     # 聊天 ID
user_name = get_session_env("HERMES_SESSION_USER_NAME")  # 用户名（可能有）
thread_id = get_session_env("HERMES_SESSION_THREAD_ID")  # 线程/话题 ID
```

## 参考实现

`~/.hermes/hermes-agent/plugins/security-guidance/` — 现有参考插件，演示了 `pre_tool_call` 和 `transform_tool_result` 两种 hook 的完整用法。

## 启用插件

将插件目录放在 `~/.hermes/hermes-agent/plugins/` 下，重启网关后自动加载：

```bash
hermes gateway restart
```

或在前台启动验证：
```bash
hermes gateway  # Ctrl+C 停止
```

## 调试技巧

- 在 `register()` 中添加 `print("Access control plugin loaded")` 确认加载
- Hook 回调中抛出的异常会被捕获并记录到 `agent.log`
- 返回 `None` = 放行，返回 `{"action": "block", "message": "..."}` = 阻止
