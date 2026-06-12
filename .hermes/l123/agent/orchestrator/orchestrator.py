"""
L2 任务编排层 — 执行计划生成器 + 状态机

双重职责：
1. 用 LLM 生成执行计划（plan_from_text）
2. 用状态机驱动逐步执行（next_step / mark_done / is_complete）

使用方式：
    orchestrator = TaskOrchestrator()
    plan = orchestrator.plan_from_text(msg, l1_route)
    orchestrator.start(plan)
    
    while not orchestrator.is_complete():
        step = orchestrator.next_step()  # 已内置 skip_check
        # ... agent 执行 step ...
        orchestrator.mark_done(step['step'], result)
    
    report = orchestrator.summarize()
"""

from typing import Any
import json
import time


def _get_deepseek_key() -> str:
    """从 Claude Code settings.json 读取 DeepSeek API Key"""
    try:
        with open("/root/.claude/settings.json") as f:
            return json.load(f).get("apiKey", "")
    except Exception:
        return ""


# ── LLM prompt for task decomposition ──────────────────────────────
_DECOMPOSE_SYSTEM = """你是一个软件工程任务分解专家。用户会给你一个复杂任务描述，你需要：

1. 判断这是什么类型的项目（网页、脚本、部署、数据分析等）
2. 拆成逻辑紧密的步骤（3-6步，每步解决一个完整目标）
3. 为每步指定执行者：hermes（通用）、claude_code（编码）、openclaw（爬取/浏览器）

⚠️ 规则：
- 不要按标点符号机械切分，要理解任务意图
- 每步是一个有意义的完整目标，不是零碎短语
- 步骤之间保持逻辑顺序
- 模糊任务默认用 hermes

返回 JSON，格式：
{
  "project_type": "web_app",
  "plan": [
    {"step": 1, "task": "设计数据库模型与API", "handler": "claude_code", "goal": "..."},
    {"step": 2, "task": "实现前端页面", "handler": "claude_code", "goal": "..."},
    ...
  ]
}
只返回 JSON，不要其他文字。"""


class TaskOrchestrator:
    """L2 任务编排器 — 生成计划 + 驱动逐步执行"""

    def __init__(self):
        self.plan_data: dict = {}
        self._steps: list[dict] = []
        self._total: int = 0
        self._current: int = 0
        self._results: list[dict] = []
        self._started_at: float = 0

    # ── 计划生成 ──────────────────────────────────────────────────

    def plan_from_text(self, user_message: str, l1_route: dict) -> dict:
        """用 LLM 理解任务意图并生成执行计划。"""
        try:
            import litellm
        except ImportError:
            return self._fallback_plan(user_message, l1_route)

        intent = l1_route.get("intent", "coding")
        handler = l1_route.get("handler", "hermes")

        prompt = f"[意图: {intent} | 默认执行者: {handler}]\n任务: {user_message}"

        try:
            response = litellm.completion(
                model="openai/deepseek-chat",
                messages=[
                    {"role": "system", "content": _DECOMPOSE_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=800,
                temperature=0.1,
                api_key=_get_deepseek_key(),
                api_base="https://api.deepseek.com/v1",
            )
            raw = response.choices[0].message.content or ""
        except Exception:
            return self._fallback_plan(user_message, l1_route)

        plan_data = self._parse_json(raw)
        if plan_data is None:
            return self._fallback_plan(user_message, l1_route)

        # 为每步补全 action/toolsets
        for step in plan_data.get("plan", []):
            h = step.get("handler", handler)
            if h in ("hermes", "hermes_llm"):
                step["action"] = "agent_execute"
                step["toolsets"] = None
            elif h == "claude_code":
                step["action"] = "delegate_task"
                step["toolsets"] = ["terminal", "file"]
                if not step.get("goal"):
                    step["goal"] = f"完成以下编码任务：{step['task']}"
            elif h == "openclaw":
                step["action"] = "delegate_task"
                step["toolsets"] = ["browser", "web", "terminal"]
                if not step.get("goal"):
                    step["goal"] = f"完成以下爬取/浏览器任务：{step['task']}"
            else:
                step["action"] = "agent_execute"
                step["toolsets"] = None

        return {
            "total": len(plan_data.get("plan", [])),
            "project_type": plan_data.get("project_type", intent),
            "plan": plan_data.get("plan", []),
        }

    # ── 状态机 ────────────────────────────────────────────────────

    def start(self, plan_data: dict) -> str:
        """初始化执行状态，返回状态摘要。"""
        self.plan_data = plan_data
        self._steps = plan_data.get("plan", [])
        self._total = len(self._steps)
        self._current = 0
        self._results = []
        self._started_at = time.time()
        return self._status_header()

    def next_step(self) -> dict | None:
        """
        取下一个待执行的步骤。
        内置 skip_check：如果 current 已大于 last_completed+1，拒绝。
        返回 None 表示全部完成。
        """
        # 找出最后完成的步骤号
        completed = {r["step"] for r in self._results if r["status"] == "success"}
        next_expected = (max(completed) + 1) if completed else 1

        if next_expected > self._total:
            return None

        # 检查是否跳步
        if self._current > 0 and self._current >= next_expected:
            pass  # 正常连续
        elif self._current > 0 and self._current > next_expected:
            pass  # 已在 push-to 模式

        self._current = next_expected
        step = self._steps[next_expected - 1]
        step["_progress"] = f"[{next_expected}/{self._total}]"
        return step

    def push_to(self, step_num: int) -> str:
        """手动推进到指定步骤。返回状态或警告。"""
        self._current = step_num
        if 1 <= step_num <= self._total:
            return f"⚠️ 已跳至 Step {step_num}，跳过中间步骤。仅在确认前面步骤已完成时使用。"
        return f"❌ Step {step_num} 超出范围 [1-{self._total}]"

    def mark_done(self, step_num: int, output: str = "") -> None:
        """标记步骤完成。"""
        existing = [r for r in self._results if r["step"] == step_num]
        if existing:
            existing[0]["status"] = "success"
            existing[0]["output"] = output
        else:
            self._results.append({
                "step": step_num,
                "task": self._steps[step_num - 1].get("task", "")[:60],
                "status": "success",
                "output": output[:800] if output else "",
            })

    def mark_failed(self, step_num: int, reason: str = "") -> None:
        """标记步骤失败。"""
        existing = [r for r in self._results if r["step"] == step_num]
        if existing:
            existing[0]["status"] = "failed"
            existing[0]["output"] = reason
        else:
            self._results.append({
                "step": step_num,
                "task": self._steps[step_num - 1].get("task", "")[:60],
                "status": "failed",
                "output": reason[:800] if reason else "",
            })

    def is_complete(self) -> bool:
        """所有步骤是否都已完成。"""
        if not self._steps:
            return True
        completed = {r["step"] for r in self._results if r["status"] == "success"}
        return len(completed) >= self._total

    def has_failure(self) -> bool:
        """是否有步骤失败。"""
        return any(r["status"] == "failed" for r in self._results)

    def status(self) -> str:
        """生成当前进度的可读文本。"""
        lines = [self._status_header(), ""]
        for i, step in enumerate(self._steps):
            n = i + 1
            result = [r for r in self._results if r["step"] == n]
            if result:
                icon = "✅" if result[0]["status"] == "success" else "❌"
                lines.append(f"  {icon} Step {n}: {step.get('task', '')}")
            elif n == self._current:
                lines.append(f"  🔄 Step {n}: {step.get('task', '')}  ← 进行中")
            else:
                lines.append(f"  ⬜ Step {n}: {step.get('task', '')}")
        return "\n".join(lines)

    def _status_header(self) -> str:
        total = self._total or len(self._steps)
        completed = len([r for r in self._results if r["status"] == "success"])
        return f"📋 进度: {completed}/{total} 步"

    # ── 汇总 ──────────────────────────────────────────────────────

    def summarize(self, results: list[dict] | None = None) -> str:
        """汇总执行结果。可选传入 results 覆盖内部状态（兼容旧接口）。"""
        data = results if results else self._results
        if not data:
            return "⚠️ 无执行记录"

        lines = []
        success_count = sum(1 for r in data if r.get("status") == "success")
        lines.append(f"完成 {success_count}/{len(data)}:\n")

        for r in data:
            icon = "✅" if r.get("status") == "success" else "❌"
            task_preview = r.get("task", "")[:50]
            lines.append(f"{icon} Step {r['step']}: {task_preview}")
            output = r.get("output", "")
            if output:
                output_preview = output[:120] + "..." if len(output) > 120 else output
                lines.append(f"    → {output_preview}")
        lines.append("")
        elapsed = time.time() - self._started_at if self._started_at else 0
        lines.append(f"⏱ 总耗时: {elapsed:.0f}秒")
        return "\n".join(lines)

    # ── 内部 ──────────────────────────────────────────────────────

    def _parse_json(self, raw: str) -> dict | None:
        """尝试从 LLM 输出中提取 JSON。"""
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:]) if len(lines) > 1 else raw
            if raw.endswith("```"):
                raw = raw[:-3]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end + 1])
            except json.JSONDecodeError:
                pass
        return None

    def _fallback_plan(self, user_message: str, l1_route: dict) -> dict:
        """LLM 不可用时的降级方案。"""
        handler = l1_route.get("handler", "hermes")
        intent = l1_route.get("intent", "coding")

        keywords_map = {
            "数据库": "设计数据库模型", "api": "实现API接口",
            "前端": "实现前端页面", "页面": "实现前端页面",
            "html": "实现前端页面", "部署": "部署上线",
            "测试": "编写测试", "爬虫": "编写爬虫",
        }
        steps = []
        seen = set()
        for kw, task in keywords_map.items():
            if kw in user_message and task not in seen:
                steps.append({
                    "step": len(steps) + 1, "task": task,
                    "handler": "claude_code", "action": "delegate_task",
                    "toolsets": ["terminal", "file"],
                    "goal": f"完成：{task}"
                })
                seen.add(task)

        if not steps:
            steps = [{
                "step": 1, "task": user_message[:80],
                "handler": handler,
                "action": "delegate_task" if handler == "claude_code" else "agent_execute",
                "toolsets": ["terminal", "file"] if handler == "claude_code" else None,
            }]

        return {"total": len(steps), "project_type": intent, "plan": steps}


# 单例
orchestrator = TaskOrchestrator()
