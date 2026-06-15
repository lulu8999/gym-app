# L2 网关集成代码参考

## gateway/run.py 注入位置

文件 `/root/.hermes/hermes-agent/gateway/run.py`，函数 `_handle_message_with_agent()`，
约第 8608 行（`message_text = await self._prepare_inbound_message_text(` 之前）。

## L1 钩子（8609-8618行）

```python
# L1 — lightweight classification before agent invocation
try:
    route_result = router.route(event.text or '')
    event.l1_route = route_result
    intent_str = route_result.get('intent', '?')
    handler_str = route_result.get('handler', '?')
    logger.warning('L1 route: %s → %s | text=%r', intent_str, handler_str, (event.text or '')[:60])
except Exception as e:
    logger.debug('L1 route failed', exc_info=True)
    print(f'[L1] FAILED: {e}', flush=True)
```

## L2 钩子（8619-8653行）

```python
# L2 — task orchestration for complex tasks
l1_result = getattr(event, 'l1_route', None) or {}
is_complex = l1_result.get('is_complex')
subtasks = l1_result.get('subtasks')
if is_complex and subtasks:
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "orchestrator",
            "/root/l123/agent/orchestrator/orchestrator.py"
        )
        orch_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(orch_mod)
        plan_result = orch_mod.orchestrator.plan(subtasks)
        event.l2_plan = plan_result
        logger.warning('L2 plan: %d steps | handler=%s',
                       plan_result.get('total', 0), l1_result.get('handler', '?'))
    except Exception:
        logger.debug('L2 orchestration failed', exc_info=True)

# Inject L2 plan into message text for agent guidance
if getattr(event, 'l2_plan', None):
    plan_lines = []
    for step in event.l2_plan.get('plan', []):
        line = f"  Step {step['step']}: [{step['handler']}] {step['task']}"
        if step.get('goal'):
            line += f"\n    Goal: {step['goal']}"
        plan_lines.append(line)
    plan_text = "\n".join(plan_lines)
    l2_note = (
        f"\n\n[L2 执行计划 — 请严格按此计划逐步执行，每步完成后标记状态]\n"
        f"{plan_text}\n"
        f"共 {event.l2_plan.get('total', 0)} 步，完成后用 orchestrator.summarize() 汇总"
    )
```

## l2_note 拼接到 message_text（8658行后）

```python
if getattr(event, 'l2_plan', None):
    message_text += l2_note
    logger.warning('L2 plan injected: %d steps appended to message',
                   event.l2_plan.get('total', 0))
```

## 触发条件

- L1 返回 `is_complex=True` 且有 `subtasks` 列表
- orchestrator 不判断——纯接收 subtasks 映射到 action

## 排查要点

1. **日志验证**：`grep "L1 route\|L2 plan" /root/.hermes/logs/gateway.log`
2. **分类验证**：`cd /root/.hermes/hermes-agent && venv/bin/python3 -c "from agent.router import router; print(router.route('帮我写个爬虫'))"`
3. **编排验证**：`cd /root/l123 && python3 -c "from agent.orchestrator.orchestrator import orchestrator; print(orchestrator.plan([{'task':'test','handler':'claude_code'}]))"`
4. **pycache 陷阱**：修改 `agent/router.py` 后必须清 `__pycache__`，否则网关加载旧 `.pyc`
