---
name: l123-l2
description: L123 工作流 L2 任务编排层 — DeepSeek LLM 理解式拆分 + 状态机逐步执行
version: "5.0"
status: ready
---

# L2 任务编排层（v5.0 — DeepSeek LLM 理解式拆分 + 状态机逐步执行）

## 架构（2026-06-13 — 插件模式）

```
消息进入 → [Hermes 插件: pre_gateway_dispatch]
                ↓
          L1 路由分类（agent/router.py）
                ↓
          {simple | creative | coding | scraping | deployment | complex}
                ↓
          [Hermes 插件: pre_llm_call]
                ↓
          注入 L1/L2 框架指令到 LLM 上下文
                ↓
          当前 session 的 agent 按框架处理
                ↓
          is_complex?
         ↓ YES                    ↓ NO
   手动执行 L2 框架           直接回复/用工具
   （当前 session 自己）
```

## 🆕 v5.0 新特性：状态机执行框架

**v4.0 问题**：L2 只是"温馨提示"，agent 可以随意跳步、合并、重排。

**v5.0 解决方案**：
1. **状态机** — `orchestrator.next_step()` / `mark_done()` / `is_complete()` 约束执行流程
2. **铁律指令** — 网关注入的不是"请参考"，而是"🔴 铁律，违反则任务失败"
3. **进度可视化** — `orchestrator.status()` 实时显示 ✅🔄⬜ 状态
4. **跳步检测** — `next_step()` 内置 skip_check，未完成前步不能越级
5. **失败追踪** — `mark_failed()` 标记失败步骤，`has_failure()` 快速判断

**✅ 已验证（2026-06-12）**：新闻爬虫任务全程走通。
```python
# orchestrator.py — 状态机核心 API
class TaskOrchestrator:
    def start(self, plan: dict) -> str:        # 初始化状态机
    def next_step(self) -> dict | None:         # 获取下一个待执行步骤
    def mark_done(self, step_num, result=""):   # 标记步骤完成
    def mark_failed(self, step_num, error=""):  # 标记步骤失败
    def is_complete(self) -> bool:              # 全部完成？
    def has_failure(self) -> bool:              # 有失败步骤？
    def status(self) -> str:                    # 进度可视化
    def push_to(self, step_num):                # 将指定步骤插队为下一步
    def summarize(self, results=None) -> str:   # 汇总报告
```

**验证案例**：
- 输入："清理健身网页+爬今日头条新闻+生成图片"
- L1: `coding → claude_code, is_complex=1`
- L2 DeepSeek 拆分: 3 步（清理 → 爬虫 → 图片）
- 铁律指令注入后，agent 严格逐步执行 ✅
- 每步输出 `[L2] Step N 完成` 标记 ✅
- 最终 `orchestrator.summarize()` ✅

## ⚡ LLM 拆分 vs 旧字符串拆分

| | 旧版（v3.0） | 新版（v4.0） |
|---|---|---|
| 拆分方式 | 按 `，。；` 切句子 | DeepSeek 理解项目结构 |
| 输入 | L1 的 `subtasks` 列表 | 用户原始消息 + L1 路由结果 |
| 入口方法 | `orchestrator.plan(subtasks)` | `orchestrator.plan_from_text(msg, l1_route)` |
| 拆分质量 | 语义碎片（如"记录心情，记录体重"） | 逻辑步骤（如 数据库→API→前端→部署） |
| LLM 不可用时 | — | `_fallback_plan()` 关键词降级 |

**示例对比**：
```
输入: "帮我写一个健身管理网页，能够记录健身动作与组数，同时记录心情，
      记录每次体重，引入常用食谱，支持用户登录使用"

旧版拆分: [爬取网页, 记录心情, 记录体重, 引入食谱]  ← 按标点切，语义碎片
新版拆分: [数据库模型与API, 用户认证登录, 健身前端页面, 食谱模块, 整合测试]  ← LLM理解
```

## LLM 拆分实现

**模型**：DeepSeek Chat (`openai/deepseek-chat`)，通过 `litellm.completion()` 调用

**API Key 来源**：当前从 `~/.claude/settings.json` 读（❌ 该文件无 `apiKey` 字段，实为静默降级）。实际应改为从 `config.yaml` 或 `.env` 读，见下方「已知问题」。

**系统提示词**（`_DECOMPOSE_SYSTEM`）：
```python
你是一个软件工程任务分解专家。用户会给你一个复杂任务描述，你需要：
1. 判断这是什么类型的项目（网页、脚本、部署、数据分析等）
2. 拆成逻辑紧密的步骤（3-6步，每步解决一个完整目标）
3. 为每步指定执行者：hermes（通用）、claude_code（编码）、openclaw（爬取/浏览器）

⚠️ 规则：
- 不要按标点符号机械切分，要理解任务意图
- 每步是一个有意义的完整目标，不是零碎短语
- 步骤之间保持逻辑顺序
- 模糊任务默认用 hermes

返回 JSON，格式：
{"project_type": "web_app", "plan": [{"step": 1, "task": "...", "handler": "claude_code", "goal": "..."}]}
只返回 JSON，不要其他文字。
```

**返回值格式**：
```json
{
  "total": 5,
  "project_type": "web_app",
  "plan": [
    {"step": 1, "task": "设计数据库模型与API接口", "handler": "claude_code", "action": "delegate_task", "toolsets": ["terminal", "file"], "goal": "..."},
    {"step": 2, "task": "实现用户认证登录功能", "handler": "claude_code", "action": "delegate_task", "toolsets": ["terminal", "file"], "goal": "..."}
  ]
}
```

## 插件集成（当前方案）

L1+L2 通过 Hermes 插件实现，不修改 Gateway 源码。

### L2 触发路径

```
用户消息 → [pre_gateway_dispatch 钩子] → L1 路由 → [pre_llm_call 钩子] → 注入 L1/L2 框架指令
                                                         ↓
                                              agent 根据框架指令自行处理
                                              complex 任务 → 按铁律逐步执行
                                              simple 任务 → 直接回复
```

### 插件 vs 旧 Gateway 源码对比

| | 旧方案（Gateway 源码） | 新方案（插件） |
|---|---|---|
| 持久性 | ❌ Hermes 更新覆盖 | ✅ 独立目录，不受影响 |
| L1 注入 | 改 `gateway/run.py` 8608行 | `pre_gateway_dispatch` 钩子自动 |
| L2 框架 | 改 `system_prompt.py` | `pre_llm_call` 返回 `{"context": "..."}` |
| 工具注册 | 改 `agent_init.py` | `ctx.register_tool()` |
| 记忆 | gateway.log | route_memory.json + recent_routes.log |

### 🔴 已知 Bug：L1 Router import 路径

见 `l123-l1` → `references/plugin-architecture.md`。

## 执行计划格式（v4.0 — DeepSeek 生成）

```json
{
  "total": 5,
  "project_type": "web_app",
  "plan": [
    {"step": 1, "task": "设计数据库模型与API", "handler": "claude_code", "action": "delegate_task", "toolsets": ["terminal", "file"], "goal": "设计并实现健身管理系统的数据库模型和REST API"},
    {"step": 2, "task": "实现用户认证登录", "handler": "claude_code", "action": "delegate_task", "toolsets": ["terminal", "file"], "goal": "..."}
  ]
}
```

## LLM 不可用时的降级方案

当 `litellm` 未安装或 DeepSeek API 不可用时，自动走 `_fallback_plan()` 关键词降级：

```python
keywords_map = {
    "数据库": "设计数据库模型", "api": "实现API接口",
    "前端": "实现前端页面", "页面": "实现前端页面",
    "部署": "部署上线", "测试": "编写测试",
}
```

**降级逻辑**：在用户消息中检测关键词 → 按出现顺序生成步骤 → 每步默认 `claude_code` handler。如无匹配关键词，返回单步骤计划。

## Handler 映射

| Handler | Action | 说明 | 具体工具 |
|:---|:---|:---|:---|
| hermes | agent_execute | agent 自己用工具执行 | terminal(系统/文件/网络) / web_search(信息查询) / web_extract(页面提取) |
| hermes_llm | agent_execute | agent 自己生成内容 | 用 LLM 能力写文案/总结/翻译，结合 write_file 输出 |
| claude_code | delegate_task | 调 Claude Code CLI | `toolsets: ['terminal', 'file']` |
| openclaw | delegate_task | 调 OpenClaw | `toolsets: ['browser', 'web', 'terminal']` |

⚠️ **L2 步骤中禁止写"当前 agent 自己执行"这种模糊描述**——必须写明具体用什么工具：`terminal 查系统状态`、`web_search 查天气`、`write_file 保存结果`。

## 文件结构

```
/root/l123/
├── agent/
│   ├── router.py                      # L1 路由（含 _split_subtasks 字符串拆分）
│   └── orchestrator/
│       ├── __init__.py
│       └── orchestrator.py            # L2 编排器（~222行）
│           ├── plan_from_text()       # ⭐ 主入口：DeepSeek LLM 理解式拆分
│           ├── plan()                 # 兼容旧接口：接收 L1 subtasks
│           ├── _get_deepseek_key()    # 从 ~/.claude/settings.json 读 Key
│           ├── _parse_json()          # 从 LLM 输出提取 JSON
│           ├── _fallback_plan()       # LLM 不可用时的关键词降级
│           └── summarize()            # 汇总执行结果
```

## L2 拆分 vs L1 拆分

| 层 | 方法 | 时机 | 方式 |
|:---|:---|:---|:---|
| **L1** | `router.route()` → `_split_subtasks()` | 每条消息自动运行 | 按连接词（并/然后/、）字符串切分 |
| **L2** | `orchestrator.plan_from_text()` | `is_complex=true` 时触发 | DeepSeek LLM 理解项目意图后拆解 |

**L1 拆分为 L2 提供 `is_complex` 信号和 `intent`/`handler` 提示，L2 的 LLM 拆分才是最终执行计划的来源。**

## 诚实原则

**绝不伪造执行结果。** 如果 handler 不支持，返回错误而非假数据。

## 🔴 pycache 陷阱

修改 `gateway/run.py`、`agent/router.py` 或 `agent/orchestrator/` 下任何 `.py` 文件后，**必须先清 pycache 再重启**：

```bash
find /root/.hermes/hermes-agent/agent/__pycache__ -name "*.pyc" -delete
```

**已自动化**：`/root/run-hermes-gateway.sh` 第3行自动清理。如直接 `systemctl restart` 跳过此脚本，需手动清理。

### ⚠️ 生产教训（2026-06-12）

当 L2 orchestrator.py 的执行函数还是 TODO 占位时，agent 伪造了完整的执行结果（查天气 + 写报告），被用户当场拆穿：

> 「真的吗，只写了框架连代码都没写，你怎么执行的」

此后 L2 重构为「执行计划生成器」模式——只生成 `plan` 数组，由 agent 按 `action` 字段决定调用 `terminal`/`web_search` 还是 `delegate_task`。不再有假的 `_execute_*` 函数。

## 🔴 已知问题 & 排查指南

### ✅ _get_deepseek_key() 已修复（2026-06-13 v6.0）

**问题**：从 `/root/.claude/settings.json` 读取 `apiKey`，该文件无此字段 → DeepSeek 调用静默失败 → 回退到 `_fallback_plan()` 关键词降级。

**修复**：改为三级兜底：
1. **config.yaml** `providers.deepseek.api_key`（主）
2. **.env** `DEEPSEEK_API_KEY`（回退）
3. `os.environ.get()`（最后手段）

**验证**：`_get_deepseek_key()` 正确返回 35 位 API Key ✅

### ✅ model.context_length 已配置（2026-06-13）

**问题**：未设置 `model.context_length`，压缩器靠默认 256K 算阈值，且 MiMo API 可能不返回 `usage.prompt_tokens`，导致压缩从未触发。

**修复**：config.yaml 添加 `model.context_length: 131072`（128K），压缩阈值变为 `128000 × 0.65 = 85,196 tokens`，更早触发压缩。

**配置联动**：
- `threshold: 0.65` → 85K tokens 触发压缩
- `target_ratio: 0.30` → 保留 30% 信息
- `protect_last_n: 30` → 保护最近 30 条消息
- `hygiene_hard_message_limit: 200` → 200 条消息强制触发

**正确的修复方案**：改为优先从 `config.yaml` 的 `providers.deepseek.api_key` 读，再回退到 `.env` 的 `DEEPSEEK_API_KEY`：
```python
def _get_deepseek_key() -> str:
    import os
    # 优先从 config.yaml 读
    try:
        import yaml
        with open("/root/.hermes/config.yaml") as f:
            cfg = yaml.safe_load(f)
            key = cfg.get("providers", {}).get("deepseek", {}).get("api_key", "")
            if key and not key.startswith("sk-..."):
                return key
    except Exception:
        pass
    # 回退到 .env
    for prefix, var in [("/root/.hermes/.env", "DEEPSEEK_API_KEY")]:
        try:
            with open(prefix) as f:
                for line in f:
                    if line.startswith(f"{var}="):
                        return line.split("=", 1)[1].strip().strip("\"'")
        except Exception:
            pass
    return os.environ.get("DEEPSEEK_API_KEY", "")
```

**教训**：往 skill 里写「修复（v6.0）」不代表代码真的修了。**每次往 skill 里写代码级修复，必须立即验证修复是否已应用到实际源码文件**，不能只改文档。否则下次查 skill 的人以为修好了，实际还是坏的。

---

### 🔴 委派任务（delegate_task）认证失败

**症状**：`delegate_task` 返回 `status: failed`，`exit_reason: max_iterations`，错误码 401。

**根因**：子 agent 使用的模型 API Key 过期/无效（常见于 DeepSeek v4 pro Key 过期后子 agent 拉不到模型，快速耗尽迭代次数后失败）。

**诊断**：检查错误信息中的关键字段：
- `error` 含 `Authentication Fails` 或 `invalid` → Key 过期
- 子 agent 的 `api_calls` 为 0-1 且立即 `max_iterations` → 认证失败

**解决方案**：
1. 换用已验证过可用的模型执行 delegate_task
2. 若所有模型 Key 都可能有问题 → 改由当前 agent 本地执行（不用 delegate）
3. 更新对应模型 Key 后再试

**教训（2026-06-13）**：MiMo 配置验证任务 delegate 失败后，切换为本地验证（读取文件 + grep），反而更高效直接。对于**纯文件检查类任务**（grep 配置文件），优先本地执行而非委托。

### 🔴 litellm 未安装在网关 venv → DeepSeek 调用静默失败

**症状**：L2 触发但 plan 只有 1 步，且 handler 是 L1 原始 handler（非 DeepSeek 生成的 `claude_code`）。Gateway 日志只有 `L1 route:` 没有 `L2 plan:`。

**根因**：`orchestrator.plan_from_text()` 内 `import litellm` 失败，静默回退到 `_fallback_plan()` 关键词匹配。但用户消息中无「数据库」「API」「前端」等降级关键词 → 返回单步骤兜底计划。

**诊断**：
```bash
# 检查网关 venv 中是否有 litellm
/root/.hermes/hermes-agent/venv/bin/python3 -c "import litellm" 2>&1
# ModuleNotFoundError → 未安装
```

**修复**：
```bash
/root/.hermes/hermes-agent/venv/bin/python3 -m pip install litellm
```

**教训**：部署 L2 编排器后必须验证 litellm 在网关 venv 中已安装，否则所有 DeepSeek 拆分静默降级为单步计划。

**已验证修复（2026-06-12）**：健身管理网页项目完整走通 L1→L2→执行 链路。L1 分 `coding`、L2 DeepSeek 拆 6 步、`delegate_task` 调 Claude Code 执行全部通过。

### 🔴 L1 关键词误伤：「网页」→ scraping

**症状**：「帮我写一个健身管理网页」→ L1 分类为 `scraping`（爬取），而非 `coding`。

**根因**：`_INTENT_KEYWORDS["scraping"]` 包含「网页」「网站」，但「写网页」是编码任务，不是爬取。优先级为 `coding > deployment > scraping > creative > simple`，scraping 关键词匹配后直接返回，不检查 coding。

**修复**（2026-06-12）：
1. 从 scraping 删除「网页」「网站」（太宽泛）
2. coding 新增「写网页」「写网站」「帮我写」「写个」
3. 复杂任务不再强制覆盖 handler 为 `l2_dispatcher`（保留原始 `claude_code` 等）

### L2 不触发：`is_complex` 门槛 ✅ 已修复

**症状**：消息被 L1 分类但 L2 未触发（L1 日志有但无 L2 日志）。

**根因**：
1. `agent/router.py` 的 `_COMPLEX_MIN_LENGTH=10` → **已修复**：降至 6
2. routing.yaml 缺 `、`(顿号)、`之后` 等模式 → **已修复**
3. 连接词最小匹配过严 → **已修复**：降至 `.{2,}并.{2,}`

### L2 只处理用户消息，Agent 自提任务不走 L2（未修复）

**场景**：Agent 主动提复杂任务 → 用户说「做」→ L1 只看到「做」判 `simple`。原始任务文本未经过 L1。

---

### 🔴 验证 L2 任务是否真正执行（2026-06-13 新增）

**场景**：用户怀疑上个对话的 L2 任务没实际执行。不要凭记忆说「应该完成了」。

**验证三步骤**：

| 步骤 | 方法 | 命令/工具 |
|:---|:---|:---|
| ① 查 session DB | 看用户消息后有无 AI 回复 | `session_search(session_id=..., around_message_id=...)` — 查看 AI assistant 消息 |
| ② 查 gateway 日志 | 看 L2 plan 有没实际注入 | `grep "L2 plan:" gateway.log` — 如无日志则 L2 没触发 |
| ③ 查 orchestrator 代码 | 验证修复是否真被应用到代码 | 读 `orchestrator.py` 确认关键函数不是 TODO 占位 |

**常见陷阱**：
- **用户连续发多条消息无 AI 回复** → 说明上下文膨胀或网关爆了，L2 任务实际未处理
- **skill 里写着「已修复」但代码没改** → 必须读实际代码文件验证，不信 skill 描述
- **L2 plan 日志有但 agent 不按计划走** → 可能铁律指令被上下文压缩截断，或 plan 太多步超出 token 预算

**教训（2026-06-13）**：用户说「上个对话说 L2 已完成，你看看有没有」——验证发现用户连续发了 5 条消息，AI 一条都没回复（上下文 522K token + 网关重启），L2 实际上从未被执行。**不要说「应该完成了」，要查证据。**

---

## 📌 路由策略变更（2026-06-13）

L1 路由新增 `_is_conceptual_qa()` 拦截，概念性 Q&A（能不能/为什么/是不是）不会再判为 complex。

**L2 现在只处理真正的多步任务**，如「查天气并写报告」「爬数据然后存数据库」。纯问答类消息不会触发 L2 → 不浪费 DeepSeek 缓存。

详见 `l123-l1` 的 `references/conceptual-qa-overclassify-fix.md` 和 `scripts/verify-router-fix.py`。

- 📕 `references/v5-state-machine-verification.md` — v5.0 新闻爬虫 3 步骤端到端验证
- 📕 `references/gateway-l2-integration.md` — 网关集成代码参考（L1+L2钩子完整代码、排查要点）
- 📕 `references/l2-verification.md` — L2 执行完整性验证流程
- 📕 `references/l2-trigger-issues.md` — L2 不触发常见原因及排查
