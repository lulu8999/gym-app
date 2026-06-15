# L123 插件 Import 路径冲突修复

## 问题

Hermes 自带 `agent/` Python 包（`/root/.hermes/hermes-agent/agent/`），L123 路由代码也在 `agent/` 包下（`/root/l123/agent/`）。当插件内执行：

```python
from agent.router import router
```

实际 import 了 **Hermes 自带的** `agent.router`，而不是 `/root/l123/agent/router.py`。

后果：路由返回 `{agent, level, reason, confidence}`（Hermes格式），不是预期的 `{type, intent, action, handler, subtasks, count}`（L123格式）。路由日志显示 `?/simple` 而非 `simple/simple`。

## 修复：importlib 直接加载文件

```python
import importlib.util
from pathlib import Path

L123_DIR = Path("/root/l123")

def _get_router():
    global _router
    if _router is None:
        spec = importlib.util.spec_from_file_location(
            "l123_router_module",                # 唯一模块名，避免冲突
            str(L123_DIR / "agent" / "router.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["l123_router_module"] = mod  # 注册到 sys.modules
        spec.loader.exec_module(mod)
        _router = mod.router
    return _router
```

## 同理修 Orchestrator

```python
def _get_orchestrator():
    global _orchestrator
    if _orchestrator is None:
        from pathlib import Path
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "l123_orchestrator_module",
            str(L123_DIR / "agent" / "orchestrator" / "orchestrator.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        sys.modules["l123_orchestrator_module"] = mod
        spec.loader.exec_module(mod)
        _orchestrator = mod.orchestrator
    return _orchestrator
```

## 为什么可以

被加载的模块只使用标准库（`json`, `re`, `time`, `typing`）和外部包（`yaml`），没有相对导入或包内交叉引用。直接 `spec_from_file_location` 加载即可独立工作。

## 验证

改完后重启网关，看日志格式：

```bash
tail -5 /root/.hermes/plugins/l123/recent_routes.log
# 应显示 simple/simple 而非 ?/simple
```

## 适用场景

任何 Hermes 插件需要加载与 Hermes 自身同名的 Python 包时，都应使用 importlib 直接加载目标文件，避免包名冲突。
