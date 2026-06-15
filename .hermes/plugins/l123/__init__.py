"""
l123 插件 — L1 意图路由 + L2 任务编排

强制调用机制：
  1. pre_gateway_dispatch — 每一条网关消息都经过 L1 分类
  2. pre_llm_call — 每一次 LLM 调用都注入 L1/L2 框架指令
  3. on_session_start — 初始化会话级路由状态
  4. on_session_end — 将会话摘要写入持久记忆

100% 覆盖：网关消息 → pre_gateway_dispatch | CLI 消息 → pre_llm_call
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── 路径配置 ──────────────────────────────────────────────────
L123_DIR = Path("/root/l123")

MEMORY_DIR = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))) / "plugins" / "l123"
MEMORY_FILE = MEMORY_DIR / "route_memory.json"
RECENT_LOG = MEMORY_DIR / "recent_routes.log"

# ── 延迟导入（插件启动时才加载） ──────────────────────────────────
_router = None
_orchestrator = None


def _get_router():
    """加载自定义 L1 路由器 — 用 importlib 避免与 Hermes 自带 agent.router 冲突。"""
    global _router
    if _router is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "l123_router",
            str(L123_DIR / "agent" / "router.py"),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载路由器: {L123_DIR / 'agent' / 'router.py'}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["l123_router"] = mod
        spec.loader.exec_module(mod)
        _router = mod.router
    return _router


def _get_orchestrator():
    """加载自定义 L2 编排器 — 用 importlib 避免包名冲突。"""
    global _orchestrator
    if _orchestrator is None:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "l123_orchestrator",
            str(L123_DIR / "agent" / "orchestrator" / "orchestrator.py"),
        )
        if spec is None or spec.loader is None:
            raise ImportError(f"无法加载编排器: {L123_DIR / 'agent' / 'orchestrator' / 'orchestrator.py'}")
        mod = importlib.util.module_from_spec(spec)
        sys.modules["l123_orchestrator"] = mod
        spec.loader.exec_module(mod)
        _orchestrator = mod.orchestrator
    return _orchestrator


# ── 记忆持久化 ──────────────────────────────────────────────────


def _ensure_memory_dir():
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_memory() -> list[dict]:
    _ensure_memory_dir()
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return []
    return []


def _save_memory(data: list[dict]):
    _ensure_memory_dir()
    # 只保留最近 500 条，防止膨胀
    trimmed = data[-500:]
    MEMORY_FILE.write_text(json.dumps(trimmed, ensure_ascii=False, indent=2), encoding="utf-8")


def _log_route(message: str, route: dict, extra: Optional[dict] = None):
    """记录一次路由事件到持久记忆。"""
    memory = _load_memory()
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "msg_preview": message[:80],
        "msg_len": len(message),
        "route": route,
    }
    if extra:
        entry.update(extra)
    memory.append(entry)
    _save_memory(memory)

    # 也写近日志（用于快速 tail）
    _ensure_memory_dir()
    try:
        with open(RECENT_LOG, "a", encoding="utf-8") as f:
            route_type = route.get("type", "?")
            intent = route.get("intent", "?")
            f.write(f"[{entry['ts']}] {route_type}/{intent}: {message[:60]}\n")
    except IOError:
        pass


def _get_recent_route_stats(hours: int = 4) -> dict:
    """获取近几小时的路由统计，用于注入模型记忆。"""
    memory = _load_memory()
    cutoff = time.time() - (hours * 3600)

    recent = [
        r for r in memory
        if r.get("ts", "").startswith(time.strftime("%Y-%m-%d"))
    ]
    total = len(recent)
    type_counts: dict[str, int] = {}
    intent_counts: dict[str, int] = {}
    for r in recent:
        rt = r.get("route", {}).get("type", "?")
        type_counts[rt] = type_counts.get(rt, 0) + 1
        it = r.get("route", {}).get("intent", "?")
        intent_counts[it] = intent_counts.get(it, 0) + 1
    return {
        "total_routes": total,
        "type_distribution": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "intent_distribution": dict(sorted(intent_counts.items(), key=lambda x: -x[1])),
        "last_route": recent[-1] if recent else None,
    }


def _inject_memory_reinforcement(route: dict, source: str = "") -> str:
    """生成&#34;L123 记忆回放&#34;文本，让模型能感知L1/L2一直在工作。"""
    stats = _get_recent_route_stats()
    lines = [
        "═══════════════════════════════════════════",
        "🧠 L123 工作流 — 系统级记忆回放",
        "═══════════════════════════════════════════",
        f"• 今日已路由 {stats['total_routes']} 条消息",
        f"• 类型分布: {stats['type_distribution']}",
        f"• 意图分布: {stats['intent_distribution']}",
        "",
        "⚡ L1/L2 是底层逻辑，100% 强制调用，不可绕过。",
        f"   当前消息: [{route.get('type','?')}/{route.get('intent','?')}]",
        "═══════════════════════════════════════════",
    ]
    return "\n".join(lines)


# ── L1/L2 框架注入文本 ──────────────────────────────────────────

_L1_L2_FRAMEWORK = """## 🎯 L123 工作流框架（系统级）

Lulu 的项目使用 L1+L2 两层工作流。你必须严格遵守以下规则，不可忽略。

### L1 意图路由规则
每条用户消息都必须先判断意图类型：
- **simple** — 简单查询/操作，直接使用工具执行（查天气、看状态、显示等）
- **creative** — 创作类任务，自己 + LLM 生成（写文章、翻译、总结、分析等）
- **coding** — 编码任务，用 Claude Code 执行（写脚本、重构、加功能等）
- **scraping** — 爬取/浏览器任务，用 OpenClaw / delegate_task 执行
- **deployment** — 部署/配置任务，用 Claude Code 执行
- **complex** — 复杂任务，必须走 L2 分步执行框架

### L2 执行框架（仅 complex 任务）
当任务被标为 complex 时，必须：
1. 用 L2 Orchestrator 生成分步执行计划
2. 每轮只执行一个步骤
3. 完成后标记完成，取下一步
4. 全部完成后调用 summarize() 生成汇总
5. 定期汇报进度给用户

### 重要规则
- ⚡ 快速确认（"做吧"、"继续"、"开搞"）→ 用 session_search 找回上一条完整任务，重新走 L1+L2
- 🔴 绝不伪造数据 — 如果执行失败，如实告知
- ⏱ 长期任务定期汇报进度"""


# ── 钩子实现 ──────────────────────────────────────────────────

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
        # 无论如何，停止当前会话处理
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


def _on_pre_gateway_dispatch(
    event=None,
    gateway=None,
    session_store=None,
    **kwargs,
) -> Optional[dict]:
    """
    pre_gateway_dispatch — 每一条网关消息都执行 L1 路由。

    返回 rewrite 动作，在消息文本前注入 L1 路由标签，
    使 agent 在处理时始终知道意图分类。
    """
    if not event or not hasattr(event, "text") or not event.text:
        return None

    text = event.text.strip()

    # ── Slash 命令检测 ─────────────────────────────────────
    # 所有 / 开头的命令直接放行给 Hermes，不走路由
    if text.startswith("/"):
        logger.info("Slash command: %s → passthrough to Hermes (no L1 route)", text.split()[0])
        return None  # 不拦截，让 Hermes 原生处理

    if not text:
        return None

    try:
        router = _get_router()
        route = router.route(text)

        # 记录到持久记忆
        _log_route(text, route, {"source": "gateway"})

        # 注入路由标签到消息文本
        route_type = route.get("type", "simple")
        intent = route.get("intent", "simple")

        if route_type == "complex":
            count = route.get("count", 0)
            tag = f"[L1:complex|{count}步] "
            subtasks = route.get("subtasks", [])
            if subtasks:
                steps_str = " → ".join(s.get("task", "")[:20] for s in subtasks)
                tag = f"[L1:complex|{count}步|{steps_str}] "
        elif route_type == "single_dispatch":
            tag = f"[L1:{intent}→{route.get('handler', 'hermes')}] "
        else:
            tag = f"[L1:{intent}] "

        new_text = tag + text

        logger.info(
            "L1 route: %s | intent=%s | type=%s",
            text[:40], intent, route_type,
        )

        return {"action": "rewrite", "text": new_text}

    except Exception as exc:
        logger.warning("L1 pre_gateway_dispatch failed: %s", exc, exc_info=True)
        return None


def _on_pre_llm_call(
    user_message: str = "",
    session_id: str = "",
    task_id: str = "",
    turn_id: str = "",
    is_first_turn: bool = False,
    platform: str = "",
    conversation_history: Optional[list] = None,
    **kwargs,
) -> Optional[str]:
    """
    pre_llm_call — 每一次 LLM 调用都注入 L1/L2 框架指令。

    在 CLI 模式下，这是 100% 强制调用的唯一路径。
    在 Gateway 模式下，它作为补充，确保框架规则始终存在。
    """
    if not user_message:
        return None

    # Slash 命令不走路由，直接跳过
    if user_message.strip().startswith("/"):
        return None

    try:
        router = _get_router()
        route = router.route(user_message)

        _log_route(user_message, route, {
            "source": "llm_call",
            "session_id": session_id,
            "is_first_turn": is_first_turn,
        })

        route_type = route.get("type", "simple")
        intent = route.get("intent", "simple")

        # 注入上下文的框架指令 + 记忆回放
        parts = [_L1_L2_FRAMEWORK]

        # 当前消息的 L1 路由结果
        route_summary = f"\n### 当前消息路由\n消息: {user_message[:80]}\n路由: {route_type}/{intent}"
        if route_type == "complex":
            subtasks = route.get("subtasks", [])
            if subtasks:
                route_summary += f"\n拆分 {route.get('count', 0)} 步:"
                for st in subtasks:
                    route_summary += f"\n  - [{st['intent']}] {st['task'][:40]} → {st['handler']}"
        else:
            handler = route.get("handler", "hermes")
            route_summary += f"\n执行者: {handler}"

        parts.append(route_summary)

        # 🔴 强制注入 L123 记忆回放（让模型始终感知 L1/L2 在工作）
        parts.append(_inject_memory_reinforcement(route, source="llm_call"))

        # L2 如果近期有活跃的 orchestrator 状态，也注入
        try:
            orch = _get_orchestrator()
            if orch and not orch.is_complete() and orch._steps:
                parts.append(f"\n### 活跃 L2 执行状态\n{orch.status()}")
        except Exception:
            pass

        return "\n\n".join(parts)

    except Exception as exc:
        logger.warning("L1 pre_llm_call failed: %s", exc, exc_info=True)
        return _L1_L2_FRAMEWORK  # 即使分类失败也至少注入框架


def _on_session_start(
    session_id: str = "",
    platform: str = "",
    user_id: str = "",
    **kwargs,
) -> Optional[str]:
    """
    on_session_start — 初始化会话级路由状态。

    记录会话开始时间，返回简短欢迎提示。
    """
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

    # 返回简短提示，让用户知道新会话已开始
    return "✅ 新会话已开始"


def _on_session_end(
    session_id: str = "",
    completed: bool = True,
    interrupted: bool = False,
    **kwargs,
) -> None:
    """
    on_session_end — 将会话摘要写入持久记忆。

    记录本轮会话已完成的消息数和 L1 路由分布统计。
    """
    _ensure_memory_dir()

    # 统计本轮会话的路由分布
    all_routes = _load_memory()
    session_routes = [r for r in all_routes if r.get("session_id") == session_id]

    type_counts: dict[str, int] = {}
    intent_counts: dict[str, int] = {}
    for r in session_routes:
        rt = r.get("route", {}).get("type", "?")
        type_counts[rt] = type_counts.get(rt, 0) + 1
        it = r.get("route", {}).get("intent", "?")
        intent_counts[it] = intent_counts.get(it, 0) + 1

    summary = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "session_end",
        "session_id": session_id,
        "completed": completed,
        "interrupted": interrupted,
        "total_messages": len(session_routes),
        "type_distribution": type_counts,
        "intent_distribution": intent_counts,
    }

    all_routes.append(summary)
    _save_memory(all_routes)
    logger.info(
        "L123 session ended: %s | %d msgs | %s",
        session_id, len(session_routes), type_counts,
    )


# ── 工具（可选：手动 L1 路由） ──────────────────────────────────

_L1_ROUTE_TOOL = {
    "name": "l1_route",
    "description": "分析消息的 L1 意图路由，返回分类结果和子任务拆分（如果复杂）",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "要分析的文本",
            },
        },
        "required": ["message"],
    },
}


def _handle_l1_route(args: dict, **kw) -> str:
    msg = args.get("message", "")
    if not msg:
        return "请提供消息文本"
    try:
        router = _get_router()
        result = router.route(msg)
        return router.describe(msg)
    except Exception as exc:
        return f"L1 路由出错: {exc}"


_L2_PLAN_TOOL = {
    "name": "l2_plan",
    "description": "对复杂任务生成 L2 执行计划（使用 DeepSeek LLM 拆分）",
    "parameters": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "要拆分的完整任务描述",
            },
            "intent": {
                "type": "string",
                "description": "L1 路由得出的意图（可选）",
            },
            "handler": {
                "type": "string",
                "description": "默认执行者（可选）",
            },
        },
        "required": ["message"],
    },
}


def _handle_l2_plan(args: dict, **kw) -> str:
    msg = args.get("message", "")
    if not msg:
        return "请提供消息文本"
    try:
        # 先做 L1 路由
        router = _get_router()
        route = router.route(msg)
        orch = _get_orchestrator()
        plan = orch.plan_from_text(msg, route)
        if not plan or not plan.get("plan"):
            return "L2 计划生成失败（LLM 无返回）"
        summary = orch.start(plan)
        lines = [
            summary,
            f"项目类型: {plan.get('project_type', '?')}",
        ]
        for step in plan.get("plan", []):
            lines.append(
                f"  Step {step['step']}: {step['task']} → {step['handler']}"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"L2 计划出错: {exc}"


# ── 插件注册入口 ──────────────────────────────────────────────────


def register(ctx) -> None:
    """注册 L123 插件到 Hermes。"""

    # 1. 注册钩子（强制调用）
    ctx.register_hook("pre_gateway_dispatch", _on_pre_gateway_dispatch)
    ctx.register_hook("pre_llm_call", _on_pre_llm_call)
    ctx.register_hook("on_session_start", _on_session_start)
    ctx.register_hook("on_session_end", _on_session_end)

    # 2. 注册工具（可选手动路由）
    ctx.register_tool(
        name="l1_route",
        toolset="l123",
        schema=_L1_ROUTE_TOOL,
        handler=_handle_l1_route,
        description="L1 意图路由 — 分析消息意图并返回分类",
        emoji="🎯",
    )
    ctx.register_tool(
        name="l2_plan",
        toolset="l123",
        schema=_L2_PLAN_TOOL,
        handler=_handle_l2_plan,
        description="L2 任务编排 — 使用 LLM 生成分步执行计划",
        emoji="📋",
    )

    logger.info("L123 plugin loaded: pre_gateway_dispatch + pre_llm_call + tools")
