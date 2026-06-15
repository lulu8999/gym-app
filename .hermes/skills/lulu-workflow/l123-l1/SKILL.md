---
name: l123-l1
description: L123 工作流 L1 意图路由层 — 自动分析用户意图、拆分复杂任务、按类型分发到对应 handler
tags: [routing, l123, intent-classification]
---

# L123 L1 意图路由

## ✅ 集成状态（2026-06-13 更新 — 插件架构）

**最终方案**：Hermes 插件 (`~/.hermes/plugins/l123/`)，不是 Gateway 源码修改。

**为什么从 Gateway 源码改为插件**：
- Gateway 源码修改会被 Hermes 更新覆盖（已验证发生过）
- 插件有独立目录，不会被更新覆盖
- 插件支持钩子机制：100% 调用覆盖
- `pre_llm_call` 覆盖 CLI 模式，`pre_gateway_dispatch` 覆盖 Gateway 模式

**插件文件**：
| 文件 | 说明 |
|------|------|
| `~/.hermes/plugins/l123/__init__.py` | 478行，钩子 + 路由 + 记忆 + 工具注册 |
| `~/.hermes/plugins/l123/plugin.yaml` | 4钩子 + 2工具注册 |
| `~/.hermes/plugins/l123/route_memory.json` | 路由持久记忆（500条上限） |
| `~/.hermes/plugins/l123/recent_routes.log` | 追加模式路由日志 |

**配置**：`config.yaml` 的 `plugins.enabled` 包含 `l123`

**踩过的坑**（方案演进史）：
| 方案 | 结果 | 原因 |
|------|:----:|------|
| 自定义工具 + 系统提示词 | ❌ | agent 忽略"强制"指导 |
| 修改 Gateway 源码 `agent/router.py` | ❌ 被覆盖 | Hermes 更新时重置文件 |
| ✅ **Hermes 插件** | ✅ 持久 | 独立目录，钩子强制调用 |

## 触发条件

本技能已自动加载。每次收到用户消息时，先调用 L1 路由分析意图，再决定怎么处理。

### ⚠️ 现状：插件在工作但用户看不见

L1 路由发生在 Hermes 插件层（`pre_llm_call` 钩子），用户看不到路由过程，只看到最终回复。

用户问"L1 是不是没集成"时，检查：
```bash
tail -5 ~/.hermes/plugins/l123/recent_routes.log
```
或查看 `route_memory.json`：
```bash
python3 -c "import json; d=json.load(open('/root/.hermes/plugins/l123/route_memory.json')); print(d[-1]['route'])"
```

### 让用户感知 L1 的建议

当 L1 判非 simple 时（coding/creative/deployment），agent 可以在回复开头加一行：

> 🎯 L1 路由: 编码任务 → 用 Claude Code 执行

这样用户能直观看到路由过程，不用查日志。simple 类消息不用加（避免噪音）。

### 触发 L2 的条件

只有 L1 分类为 `is_complex=True` 的消息才会走 L2 分步执行框架。以下消息会触发 L2：
- 含连接词的复杂指令（"查天气并写报告"）
- 多于 10 字且含多意图切换的消息
- 匹配复杂任务模式的消息

简单的单意图消息（"L1 是不是没集成"、"检查一下状态"）永远归为 `simple → hermes`，不走 L2 — 这是正确行为，不是故障。

### 🔴 已知问题：Agent 自提任务不走 L1/L2 管道

**场景**：Agent 提议复杂任务 → 用户说"做" → `event.text = '做'` → L1 判 simple

**解决方案（2026-06-13）**：当 agent 收到简短确认（做吧/开搞/继续）时，不要直接执行。用 `session_search` 找到上一条用户消息的完整任务描述，手动送入 L1+L2 管道再执行。

详见 `l123-l2` 的 `references/l2-trigger-issues.md` §问题2。

## 路由流程 + L2 执行（集成）

```
用户消息 → L1 Router → 意图分类
  ├── simple      → 直接用工具执行（查、看、显示、运行等）
  ├── creative    → Hermes + LLM 生成（写、翻译、总结、分析等）
  ├── coding      → 交给 Claude Code（写脚本、重构、加功能等）
  ├── scraping    → 交给 OpenClaw（爬数据、采集、搜索等）
  ├── deployment → 交给 Claude Code（部署、安装、配置、发布等）
  └── complex    → ⚡ 自动触发 L2 执行
       ├── L1 拆分子任务（连接词/意图切换）
       ├── L2 编排器逐个执行子任务
       │    ├── handler=hermes → 自己直接干
       │    ├── handler=hermes_llm → 自己 + LLM 生成
       │    ├── handler=claude_code → delegate_task 给 Claude Code
       │    └── handler=openclaw → delegate_task 给 OpenClaw
       └── 汇总结果 → 返回用户
```

### 重点：L1+complex → 自动走 L2，不用再手动触发

当 `router.route(msg)` 返回 `type: complex` 时，**必须执行以下步骤**：

1. 加载 L2 skill：`skill_view(name='l123-l2')`
2. 逐个执行子任务（按顺序）：
   - `handler=hermes/hermes_llm` → 自己用工具执行（terminal/web_search 等）
   - `handler=claude_code` → `delegate_task(toolsets=['terminal', 'file'], ...)`
   - `handler=openclaw` → `delegate_task(toolsets=['browser', 'web', 'terminal'], ...)`
3. 汇总结果回复用户

## 注意事项

- 关键词匹配不是 100% 完美，边界情况用 agent 判断补足
- router 单例模式：`from agent.router import router`
- **YAML 编辑**：深度嵌套缩进易被 patch 损坏，大改动用 write_file 重写
- **修改后测试**：`cd /root/l123 && python3 -c "from agent.router import router; print(router.route('查天气'))"`
- **意图切换拆分**只对≥6字长消息启用，短消息不变（原为10字，2026-06-12降至6字解决「脚本并部署」等8字被拒问题）

## 双重拆分策略

### 路径一：连接词拆分（始终启用）

```
查天气并写报告 → 连接词"并" → 2步: 查天气 + 写报告
爬数据然后存数据库 → 连接词"然后" → 2步: 爬数据 + 存数据库
```

支持的连接词在 `config/routing.yaml` 中配置：
`并、然后、之后、接着、同时、并且、再、随后、最后、、`

**复杂度阈值调优**（2026-06-12 完成）：
- `_COMPLEX_MIN_LENGTH`：10 → **6**（解决「脚本并部署」8字被拒）
- 新增 `、` 到 `_COMPLEX_SEPARATORS`（支持中文顿号并列）
- routing.yaml 新增 4 个 complex_task_patterns：`、`、`之后`、`.*部署.*部署`、`.*写.*写.*`、`.*做.*做.*`
- 降低最小匹配长度：`.{3,}并.{3,}` → `.{2,}并.{2,}` 等

**防误拆**：连接词拆完如果只有1个子任务（如"然后呢"），降级为 simple。

### 路径二：意图切换拆分（≥10字长消息自动启用）

```
查天气写报告部署网站爬数据（14字，无连接词）
→ 检测到 simple→creative→deployment→scraping 切换
→ 4步: 查天气 + 写报告 + 部署 + 网站爬数据
```

**短消息保护**：<10字的消息不启用意图切换拆分（如"部署网站爬数据"保持单任务）。

## 关键词匹配策略

### 长词优先+分数制

关键词按长度降序排列（`_prepared_keywords`），匹配时用长度作为分数：
- 分数=关键词长度（字）
- 同分时按优先级排：`coding > deployment > scraping > creative > simple`

示例：`写个Python脚本` → "写个脚本"(4字, coding) > "写"(1字, creative) → coding

### 意图切换锚点

检测切换位置时，**优先使用短关键词（1-2字）作为锚点**，避免"网站"遮盖"爬"、"配置"遮盖"写代码"等。

## 合并策略（多次修复经验）

拆分后的子任务，按**拆分来源片段**分别合并：

```
✅ 连接词拆+意图切换拆:
  "查天气并写报告部署网站"
  → 连接词拆出: ["查天气", "写报告部署网站"]
  → 意图切换拆: ["查天气", "写报告", "部署网站"]
  → 片段内合并: ["查天气"] + ["写报告", "部署网站"]
  → 最终: 3步（不会把同意图跨片段合并）

✅ 同一片段内同意图合并:
  "部署网站再配置域名"
  → 连接词拆出: ["部署网站", "配置域名"]
  → 两者都是deployment，但不合并（跨片段不合并）
  → 最终: 2步（"再"说明这是两个步骤）
```

**关键经验**：连接词拆出的不同片段即使同意图也不合并，因为连接词（"再/并/然后"）本身就表示用户认为这是不同步骤。

## 插件架构（当前方案）

### 插件钩子覆盖矩阵

| 钩子 | 触发时机 | 覆盖场景 | 作用 |
|------|---------|---------|------|
| `pre_gateway_dispatch` | 每一条网关消息 | 企微、微信等外部消息 | 注入 `[L1:type/intent]` 标签到消息文本 |
| `pre_llm_call` | 每一次 LLM 调用前 | CLI、Gateway 所有对话 | 注入 L1/L2 框架指令到 LLM 上下文 |
| `on_session_start` | 新会话开始时 | CLI、Gateway | 初始化路由状态 |
| `on_session_end` | 会话结束时 | CLI、Gateway | 路由统计与持久化 |

### 2 个注册工具

| 工具 | 功能 | toolset |
|------|------|---------|
| `l1_route` | 手动 L1 路由分析 | `l123` |
| `l2_plan` | 手动 L2 任务拆分 | `l123` |

### 🔴 已知 Bug：Router import 路径错误

**症状**：路由日志 `type=?`（期望 `simple/simple`）

**根因**：`from agent.router import router` 命中了 **Hermes 自带的 router**（587行），而非自定义 L1 router（328行）

| Router | 路径 | 返回字段 |
|--------|------|----------|
| Hermes 自带 | `~/.hermes/hermes-agent/agent/router.py` | `agent, level, reason, confidence` |
| 自定义 L1 | `/root/l123/agent/router.py` | `type, intent, action, handler, subtasks` |

**为什么**：Hermes 运行时 `agent` 包已加载到 `sys.modules`，插件 `sys.path.insert(0, '/root/l123')` 无效。

**修复**：用 `importlib.util.spec_from_file_location()` 绝对路径加载：
```python
import importlib.util
spec = importlib.util.spec_from_file_location("l1_router", "/root/l123/agent/router.py")
router_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router_mod)
router = router_mod.router
```

### 🔴 CLIL： 已知 Bug：`pre_llm_call` 钩子在部分 CLI 会话中未触发

**2026-06-13 发现**：当前 L123 插件在 Gateway 消息中正常工作（`pre_gateway_dispatch` 正确注入 `[L1]` 标签到每条消息），但本 CLI 会话中消息（如「不要原盘文件」「为什么感觉不一样」「你现在这个终端上也有意图路由吗」）没有出现在 `recent_routes.log` 中，说明 `pre_llm_call` 钩子未触发。

| 证据 | 说明 |
|------|------|
| 最后一条路由记录 | `19:52 [L1:complex]` — U 盘复制任务 |
| 之后的消息（~8分钟） | 无路由记录 |
| 插件配置 | `config.yaml` 中 `plugins.enabled` 包含 `l123` ✅ |
| 进程状态 | 网关正常运行，日志无报错 |

**可能原因**：
- CLI 会话启动早于插件加载 — 旧会话的钩子链已冻结
- Hermes CLI 模式不走 `pre_llm_call` 钩子通道（插件注册的钩子只对 Gateway 线程有效）
- 插件热加载后现有会话未注册钩子回调

**诊断方法**：
```bash
# 1. 查路由日志最近一条
tail -1 /root/.hermes/plugins/l123/recent_routes.log

# 2. 查网关日志是否有 L1 路由标记（Gateway 消息才有）
grep "L1 route:" /root/.hermes/logs/gateway.log | tail -3

# 3. 查插件是否在配置中
grep "l123" /root/.hermes/config.yaml

# 4. 排查 hook 是否注册成功
grep "register_hook.*pre_llm_call" /root/.hermes/logs/gateway.log
```

**用户感知差异**：
- 微信/企微：Gateway 处理 → `pre_gateway_dispatch` 正常触发 → 每条消息带 `[L1]` 标签 → 工作流程有 L1 过滤感
- CLI/TUI：Agent 直连 → `pre_llm_call` 可能未触发 → 没有路由标签 → 用户感觉「工作流程不一样」

**临时绕过**：重启网关或新建 CLI 会话（`/new`）可能重新加载插件钩子。

**待修复**：确认 Hermes 插件框架在 CLI/TUI 模式下是否支持 `pre_llm_call` 钩子，如不支持需改插件注册方式或在 Agent 入口层强制注入。

### 🔴 L2 使用门槛（2026-06-14 新增）

**问题**：删除脚本、创建任务计划这类纯操作任务被标为 complex 走 L2，导致每步等确认、效率极低。

**规则**：L2 只用于**真正需要多 agent 协作或跨系统编排**的复杂任务。以下场景**不走 L2**，直接一口气干完：

| 场景 | 示例 | 处理方式 |
|------|------|----------|
| 纯 SSH/终端命令序列 | 删文件、建任务计划、改配置 | 直接连续执行，不等确认 |
| 单系统多步骤操作 | 装依赖→写配置→重启服务 | 自己一口气做完 |
| 简单 CRUD 操作 | 增删改查文件/记录 | 直接做 |
| **对话讨论/头脑风暴** | 聊设备选型、问概念、探索方案 | 直接回答，**绝不触发 L2** |

**走 L2 的条件**（至少满足一条）：
- 需要 Claude Code 写代码（coding 类子任务）
- 需要 OpenClaw 爬数据（scraping 类子任务）
- 跨 3 个以上系统协作
- 用户明确说"分步执行"或"走一步报告一步"

**核心原则**：能自己干的绝不拆步，能一口气干完的绝不等确认。

### 🔴 对话讨论模式不触发 L2（2026-06-14 新增）

**问题**：用户在头脑风暴/探索方案时（如"用 Surface Go 2 做终端怎么样"、"树莓派 Pico 2W 接显示屏怎么样"、"为什么不能破解加密设备"），L2 框架被反复注入触发，干扰正常对话。

**识别特征**：
- 用户问"有没有推荐的"、"怎么样"、"为什么"、"能不能"
- 连续多轮在聊同一个话题的不同方向（设备选型、方案对比）
- 没有"做"、"搞"、"执行"、"部署"等动作指令
- 用户说"让我再想想吧"——明确表示还在思考阶段

**正确行为**：
- 直接回答问题，不注入 L2 框架
- 不输出"[L2] Step N 完成"标记
- 正常聊天，等用户确定要执行时再走 L1/L2

**错误行为（已发生）**：
- 用户问"有没有推荐的型号" → 系统注入 L2 4步执行计划
- 用户问"为什么不能破解" → 系统注入 L2 5步执行计划
- 用户说"esp32板子不就能这样" → 系统注入 L2 4步执行计划

**教训**：对话 ≠ 任务。头脑风暴阶段是纯聊天，不是要执行什么。

### 核心原则

1. **简单任务自己干** — simple 类直接 Hermes 做
2. **创作类自己+LLM** — creative 类 Hermes + LLM 生成
3. **复杂任务找人干** — coding→Claude Code, scraping→OpenClaw, deployment→Claude Code
4. **长词优先匹配** — 更具体的关键词优先于泛词
5. **配不上归 simple** — fallback 到 Hermes 自己判断
6. **单子任务降级** — 拆完只有1个→误判，降级为 simple
7. **绝不伪造结果** — ⚠️ 如果 handler 的执行逻辑没实现（如 L2 orchestrator 还是 TODO 占位），必须如实告知用户「框架还没完善，执行逻辑还没接上」。**绝不能伪造执行结果假装完成**。用户曾因伪造结果发火：「真的吗，只写了框架连代码都没写，你怎么执行的」
7. **绝不伪造结果** — 如果 handler 的执行逻辑没实现，如实告知用户，不可假装完成

## 关键词陷阱实录

| 被移除的关键词 | 归属 | 误判原因 | 替代方案 |
|:---|:---:|:---|---:|
| `"写个"` | coding | "写个方案"被误归类 | 加 `"写代码""写程序""编程"` |
| `"数据库"` | coding | "存数据库"不是编码 | 加 `"写数据库""建表""SQL"` |
| `"加个"` | coding | "加个文章"不是编码 | 加 `"加功能""登录功能"` |
| `"项目"` | coding | "爬GitHub项目"误归编码 | 删除，不用替代 |

**原则**：宁可少一个词，不要误判十个场景。

## YAML 编辑陷阱

`patch` 工具对≥3层嵌套 YAML 容易损坏缩进（特别是 intent_types > coding > keywords 这种）。安全操作：

- **小幅修改**（改现有词）→ 用 `patch`，确保上下文足够唯一
- **大幅修改**（增删多行）→ 用 `write_file` 重写整个文件
- **修改后验证** → `python3 -c "import yaml; yaml.safe_load(open('config/routing.yaml'))"`

## 配置文件

路由规则定义在 `/root/l123/config/routing.yaml`（约250行），可自由增删关键词/模式。

## 集成方案：创建自定义工具（已实现）

**实现状态**：✅ 已完成

### 工具文件
`/root/.hermes/hermes-agent/tools/l1_route.py`

```python
# 关键代码结构
sys.path.insert(0, '/root/l123')
from agent.router import router

def l1_route(message: str) -> dict:
    return router.route(message.strip())

# 注册到 Hermes
from tools.registry import registry
registry.register(
    name="l1_route",
    toolset="l123",
    schema=L1_ROUTE_TOOL,
    handler=lambda args, **kw: l1_route(message=args.get("message", "")),
    check_fn=_check_l1_route,
    emoji="🎯",
)
```

### 系统提示词集成
在 `/root/.hermes/hermes-agent/agent/system_prompt.py` 的 `tool_guidance` 部分添加：
```python
if "l1_route" in agent.valid_tool_names:
    tool_guidance.append(
        "## L1 路由工具使用规范\n"
        "你有一个 `l1_route` 工具，用于分析用户消息意图。**每条用户消息必须先调用此工具**。\n"
        "..."
    )
```

### 测试验证
```bash
cd /root/.hermes/hermes-agent && python3 tools/l1_route.py
# 输出：查天气→simple, 查天气并写报告→complex(2步), ...
```

### 重启生效
修改 system_prompt.py 后需重启 Gateway 才能生效。

## 参考

- 📕 `references/conceptual-qa-overclassify-fix.md` — 修复"能不能"类问题被误判为 complex
- 📕 `references/l1-slash-command-feedback.md` — `/new` 等斜杠命令的反馈机制问题
- `references/l1-tool-integration.md` — 自定义工具集成技术详解（2026-06-11 方案，已废弃）
- `references/gateway-routing-discovery.md` — Gateway 内置路由机制发现（已废弃）
- `references/complexity-tuning-2026-06-12.md` — L1 复杂度阈值调优实录
- `references/plugin-architecture.md` — 插件架构说明（钩子、记忆、import 修复）
- `references/pdf-cjk-font-fix.md`
## 文件结构

```
/root/l123/
├── config/
│   └── routing.yaml      # 路由规则（关键词、连接词、分发策略）
├── agent/
│   ├── __init__.py        # 包声明
│   └── router.py          # 核心路由逻辑（~320行）
└── data/                  # 预留数据目录
```

## ✅ 已修复：概念性 Q&A 被误判为 complex（2026-06-13 用户发现→已修复）

**问题**：概念性问题被 L1 误判为 `complex`，触发 `l2_plan`（调 DeepSeek），浪费令牌和缓存命中率。

**修复**（2026-06-13）：在 `router.py` 新增 `_is_conceptual_qa()` 路径0拦截。验证通过：
- `高端款能否模拟信号` → **simple** ✅
- `物理方案怎么搞` → **creative** ✅ 
- `能不能切换模型` → **creative** ✅
- `为什么不能逆向` → **creative** ✅
- `查天气并写报告` → **complex**（真的多步，正常 ✅）

**用户要求**：只有**写大型程序**或**拟定复杂计划**才调 DeepSeek，其余全给 Hermes（MiMo）。OpenClaw 正常保留。

### 特征词识别

消息中如果**仅含以下特征词，而无动作类关键词**（部署/写/爬/配置/安装等），应当判为概念性问题：

| 特征词 | 消息类型 | 应判意图 |
|:-------|:--------:|:--------:|
| 能不能 / 可否 / 可以吗 | 可行性询问 | simple |
| 为什么 | 原理询问 | simple/creative |
| 是不是 / 有没有 / 是否 | 判断询问 | simple |
| 是什么 | 定义询问 | simple/creative |
| 如果……那 | 假设性询问 | simple/creative |

### 测试用例

已集成到 `scripts/verify-router-fix.py`，可直接运行验证：
```bash
cd /root/l123 && python3 ~/.hermes/skills/lulu-workflow/l123-l1/scripts/verify-router-fix.py
```

**agent 侧注意**：路由修复后，概念性 Q&A 不会再触发 L2 编排。如果仍收到 complex 结果且包含可执行关键词之外的子任务，可自行消化不调 DeepSeek。

## ✅ 已实现：消息平台 slash 命令支持（2026-06-13）

**背景**：用户在微信/企微上输入 `/model`、`/stop`、`/new` 等 slash 命令，原被 L123 插件拦截后当普通文本处理，导致无响应。

**修复**：在 `pre_gateway_dispatch` 钩子中增加 slash 命令检测，在 L1 路由之前拦截。

### 实现位置

`~/.hermes/plugins/l123/__init__.py` 的 `_on_pre_gateway_dispatch` 函数开头：

```python
# ── Slash 命令检测 ─────────────────────────────────────
if text.startswith("/"):
    cmd = text.split()[0].lower()
    result = _handle_slash_command(cmd, event=event, gateway=gateway, session_store=session_store)
    if result:
        return result
    # 未识别的 /xxx 命令 — fallthrough 到 L1 路由
```

### 支持的命令

| 命令 | 处理方式 | 实际效果 |
|------|---------|---------|
| `/model` | 改写 `[L1:simple] 查看当前模型配置` | AI 回答当前模型 |
| `/stop` | 调用 `gateway.cancel_current_run()` 或 `gateway.agent_executor.cancel()` | 尝试终止当前任务 |
| `/new` | 尝试 `gateway.start_new_session()` 或 `session_store.create()` | 尝试新建会话 |
| `/help` | 改写 `[L1:simple] 显示可用命令` | AI 返回可用命令列表 |
| `/retry` | 改写 `[L1:simple] 重试上一条消息` | AI 理解意图 |
| `/undo` | 改写 `[L1:simple] 撤销上一条回复` | AI 理解意图 |

### 代码结构

- `_SLASH_COMMANDS` 字典 — 定义命令名、描述、处理方式
- `_handle_slash_command()` — 统一处理器，根据 `action` 字段分流：
  - `"abort"`（/stop）→ 尝试 stop，返回 `stop_processing: true`
  - `"new_session"`（/new）→ 尝试新建会话
  - 其他 → 自然语言改写

### 已知限制

- `/stop` 和 `/new` 依赖 `gateway` 对象是否有相应方法，不同版本 Hermes 可能接口不同
- 未识别的 `/xxx` 命令会 fallthrough 到 L1 路由，当作普通文本处理（不报错）
- 这些命令仅对通过 `pre_gateway_dispatch` 钩子的消息平台生效，CLI/TUI 已有原生支持

## 注意事项

- 关键词匹配不是 100% 完美，边界情况用 agent 判断补足
- router 单例模式：`from agent.router import router`
- **YAML 编辑**：深度嵌套缩进易被 patch 损坏，大改动用 write_file 重写
- **修改后测试**：`cd /root/l123 && python3 -c "from agent.router import router; print(router.route('查天气'))"`
- **意图切换拆分**只对≥6字长消息启用，短消息不变（原为10字，2026-06-12降至6字解决「脚本并部署」等8字被拒问题）
