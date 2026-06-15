# L1 自定义工具集成技术

## 概述

通过创建 Hermes 自定义工具 + 修改系统提示词，强制每条消息都经过 L1 路由。

## 文件清单

| 文件 | 作用 |
|:---|:---|
| `/root/.hermes/hermes-agent/tools/l1_route.py` | L1 路由工具（调用 `/root/l123/agent/router.py`） |
| `/root/.hermes/hermes-agent/agent/system_prompt.py` | 系统提示词（添加 L1 路由指导） |

## 关键代码片段

### 1. 工具注册（tools/l1_route.py）

```python
import sys
sys.path.insert(0, '/root/l123')
from agent.router import router

def l1_route(message: str) -> dict:
    return router.route(message.strip())

from tools.registry import registry

def _check_l1_route():
    return _ROUTER_AVAILABLE, "L1 路由器不可用"

registry.register(
    name="l1_route",
    toolset="l123",
    schema=L1_ROUTE_TOOL,
    handler=lambda args, **kw: l1_route(message=args.get("message", "")),
    check_fn=_check_l1_route,
    emoji="🎯",
)
```

### 2. 系统提示词注入（agent/system_prompt.py）

在 `tool_guidance` 部分添加：
```python
if "l1_route" in agent.valid_tool_names:
    tool_guidance.append(
        "## L1 路由工具使用规范\n"
        "你有一个 `l1_route` 工具...**每条用户消息必须先调用此工具**。\n"
        "..."
    )
```

## 测试方法

```bash
# 测试工具本身
cd /root/.hermes/hermes-agent && python3 tools/l1_route.py

# 测试注册是否成功
cd /root/.hermes/hermes-agent && python3 -c "
from tools.registry import registry
entries = registry._entries
print('l1_route' in entries)
"
```

## 重启生效

修改 system_prompt.py 后需重启 Gateway：
```bash
systemctl --user restart hermes-gateway
```

## 注意事项

- 工具通过 `tools/registry.py` 的 `registry.register()` 注册
- 系统提示词修改后需要重启 Gateway 才能生效
- 工具返回结果是 dict，LLM 会解析并根据 type 字段决定执行方式
