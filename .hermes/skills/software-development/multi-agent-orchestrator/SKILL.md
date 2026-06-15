---
name: multi-agent-orchestrator
description: Orchestrate multiple AI agents (Claude Code, OpenClaw, Hermes subagents) — task decomposition, dispatch, progress tracking, result aggregation.
---

# Multi-Agent Orchestrator

> 我是大脑，他们是手。用户只跟我说话，我拆任务派出去，汇总结果后回复用户。

## When to Load

- User asks about multi-agent collaboration, dispatching tasks to Claude Code or OpenClaw
- You're planning a complex multi-step task that benefits from parallel work
- User says "你协调"、"你指挥"、"派给别的 agent"
- User asks "你觉得还需要什么 agent"

## Architecture

```
用户（微信/企微）
  │
  ▼
┌─────────────────────────────────────────┐
│  🧠 超级大脑（本 Agent — Orchestrator） │
│  任务拆解 · 进度追踪 · 质量审查         │
│  用户统一入口                            │
└──┬──────┬──────┬──────┬──────┬──────────┘
   │      │      │      │      │
   ▼      ▼      ▼      ▼      ▼
┌─────┐┌─────┐┌──────┐┌──────┐┌─────────┐
│Claude││Open ││Hermes││Kimi  ││GitHub   │
│Code  ││Claw ││Sub-  ││视觉  ││CLI      │
│出plan││独立 ││Agent ││识别  ││PR/代码  │
│写代码││任务 ││并行  ││图片  ││管理     │
└─────┘└─────┘└──────┘└──────┘└─────────┘
```

## Agent Dispatch Rules

### 我自己（本 Agent）直接干
- 单文件小改（≤3个文件，逻辑清晰）
- 日常查看、配置微调
- 简单脚本编写
- 读取/搜索文件
- 发送消息、管理 cron

### Claude Code（claude-code-ds）
- 多文件重构/新功能搭建
- 生成实施计划（plan）
- 代码审查
- 用户明确说"用 Claude 写"
- **命令：** `claude-code-ds`（走 LiteLLM 代理 → DeepSeek API）

### OpenClaw（openclaw CLI）
- 独立长期任务（需要独立上下文）
- 需要隔离环境的任务
- **命令：** `openclaw` CLI
- **版本：** 2026.5.28

**OpenClaw 已安装技能（可直接用）：**
- `browser-automation` ✅ — 浏览器自动化（需要 OpenClaw 网关运行）
- `canvas` ✅ — 在 canvas 节点上展示 HTML
- 其他 15 个已就绪技能

**ClawHub 上可用的浏览器技能（可安装）：**
- `agent-browser-cli` — 浏览器自动化 CLI
- `stagehand-browser-cli` — Stagehand 自然语言浏览器操作
- `ws-agent-browser` — 浏览器智能控制（中文描述）

**OpenClaw 浏览器使用前提：**
1. 启动 OpenClaw 网关：`openclaw gateway run --allow-unconfigured --bind loopback`（后台运行）
2. 浏览器需要设备配对授权（scope-upgrade），auto-approve 因安全限制会拒绝
3. 解决：需要在终端中执行授权，或通过 openclaw doctor 交互式修复
4. 如果反复配对失败，考虑直接给 Hermes 装 Playwright/chromium

**当前状态：** 浏览器可用但配置门槛较高，日常用需要先解决授权问题。参考 `references/openclaw-capabilities.md`。

### Hermes SubAgent（delegate_task）
- 并行研究（最多 3 个同时）
- 代码审查
- 简单独立子任务
- 适合：互不依赖的平行工作流
- 注意：同步执行，父会话中断时子任务也被取消

### Kimi 视觉（Moonshot API）
- 图片识别、OCR、截图分析
- 调用方式：下载图片 → Kimi vision API
- 模型：`moonshot-v1-8k-vision-preview` / `moonshot-v1-32k-vision-preview`

## Standard Orchestration Flow

```
用户给需求
  │
  ▼
1. 拆解 → 判断是否可以并行
2. 哪些子任务自己能干？哪些要派出去？
3. 派发并行任务（最多 3 个 delegate_task → Claude Code / OpenClaw）
4. 汇总结果
5. 自我审查（完整性、安全性、质量）
6. 向用户报告
```

### 出 Plan 流程（复杂任务）

```
① 评估是否需要 Claude Code 出 plan
   ├─ 简单（自己搞定）→ 直接做
   └─ 复杂 → 走以下流程

② Claude Code 出 Plan
   → claude-code-ds，指令：出 implementation plan

③ Plan 给用户审核
   → 展示结构、文件列表、预估 token

④ 用户同意后执行
   → 可以自己执行，也可以再派给 Claude Code

⑤ 审查 → 报告
```

## Pitfalls

- ❌ **不需要出 plan 的非复杂任务也走完整流程** — 会浪费大量 token。判断标准：3个文件以内、改动逻辑清晰的，自己搞定。
- ❌ **delegate_task 执行期间父会话中断** — 子任务会被取消。长任务用 cronjob 或 background terminal。
- ❌ **子 agent 的结果需验证** — 子 agent 的总结是"自我报告"，不是可靠事实。有外部副作用（写文件、发请求）的，必须验证。
- ❌ **Kimi Key 过期不自知** — 调用前先测试：`curl -s https://api.moonshot.cn/v1/models -H "Authorization: Bearer $KEY"`
- ❌ **不要重复问用户同一个问题** — 用户已经同意或明确表态过的事，不要再次确认。比如用户说"加上去"之后又发"再看看"时，不要再问"要不要加"，直接执行。用户说"不要再重复问了"就是痛点信号。
- ❌ **用户确认不充分的新功能，先给方案列表让用户选择，而不是连续追问** — 比如加图片支持时，一次列出方案（改代码/装工具/等用户发图），让用户选一个，而不是每步都问"要吗"。
- ✅ 并行任务用 `delegate_task(tasks=[...])` 批量模式
- ✅ 需要持久运行的背景任务用 `terminal(background=true)` 或 `cronjob`
- ✅ 用户说"先别发"表示暂时搁置，不要忘记也不要催。等用户主动说"发"或"继续"再操作。

## Hermes-to-Hermes Desktop Computer Use

跨设备桌面操控模式，不用自建 HTTP 服务，直接用两个 Hermes 实例通信：

```
VPS Hermes (大脑/指挥官)
  │ SSH hermes run '...'
  ▼
Windows Hermes (本地执行层)
  ├─ browser  → 操控网页
  ├─ terminal → 调用 pyautogui/mss 操控桌面
  └─ vision   → 分析截图
```

### 架构原则

- **VPS 是大脑** — 分析截图、做决策、发送指令
- **目标机 Hermes 是手** — 本地执行，不依赖公网 API
- **不要自建 HTTP 服务** — 直接用 Hermes 自己的工具链（browser、terminal、vision）
- **SSH 通信** — VPS SSH 到目标机后执行 `hermes run '指令'`

### 目标机（Windows/Mac）前期准备

1. **安装 Hermes Agent**（和目标机平台部署一致）
2. **安装 Python 依赖**：
   ```bash
   pip install pyautogui mss pillow
   ```
3. **安装 Playwright**（浏览器操控）：
   ```bash
   pip install playwright
   playwright install chromium
   ```
4. **配置 SSH 免密登录**，让 VPS 能直接 SSH
5. **验证**：从 VPS SSH 过去执行 `hermes run 'echo hello'` 能正常返回

### 标准 Computer Use 工作流

每一轮操作流程：

```
① VPS: SSH → 目标机 → `hermes run '截图当前屏幕并保存'`
   返回: 截图路径 / 图片数据

② VPS: vision_analyze → 分析截图 → 找到目标元素坐标

③ VPS: SSH → 目标机 → `hermes run '点击坐标 (x, y) 然后输入"xxx"'`
   返回: 执行结果

④ VPS: SSH → 目标机 → `hermes run '截图当前屏幕'`
   返回: 新截图 → 验证操作结果

⑤ 如果不对 → 回到 ②
   如果对了 → 继续下一步
```

### 常用 Computer Use 工具组合

| 场景 | 目标机 Hermes 用的工具 | 指令示例 |
|------|----------------------|---------|
| 截图分析 | `mss`（终端）+ `vision_analyze`（Hermes） | `python -c "import mss; mss.mss().shot(output='screen.png')"` |
| 点击 | `pyautogui` | `python -c "import pyautogui; pyautogui.click(x, y)"` |
| 打字 | `pyautogui` | `python -c "import pyautogui; pyautogui.write('text')"` |
| 按键 | `pyautogui` | `python -c "import pyautogui; pyautogui.press('enter')"` |
| 打开应用 | `subprocess` / 桌面快捷方式 | `python -c "import subprocess; subprocess.Popen(['notepad.exe'])"` |
| 浏览器操作 | `playwright` | `hermes run '打开 b站搜 xxx，把第一个视频标题给我'` |
| 滚动 | `pyautogui` | `python -c "import pyautogui; pyautogui.scroll(-3)"` |

### 速度优化

- **截图压缩**：`mss` 截图时指定低质量 JPEG（~200KB），减少传输开销
- **选择性截图**：只截感兴趣区域（窗口级别而不是全屏）
- **浏览器用 Playwright**：CSS 选择器定位比视觉分析快 5-10x
- **预判断推理**：能用文字指令（Playwright CSS selector）就别走视觉

### Pitfalls

- ❌ **Windows 必须开机 + SSH 在线** — 机器休眠/关机就不可用
- ❌ **单轮 2-5 秒** — 包含截图传输 + 视觉分析 + 执行，比 Codex 原生慢
- ❌ **SSH 传图慢** — 优先用 HTTP 直推或 WebSocket 长连接（如果目标机有公网）
- ❌ **中文输入** — `pyautogui.write('中文')` 可能乱码，用 `pyautogui.typewrite()` 或粘贴板
- ❌ **UAC 弹窗** — Windows UAC 弹窗会阻截鼠标操作，需要有管理员权限
- ✅ **优先用 Hermes 内置工具** — 浏览器操作走 `playwright` 比全屏截图定位快得多
- ✅ **先验证目标机 Hermes 就绪** — SSH 过去 `hermes run 'python --version'` 保连通

## Related Skills

- `claude-code` — Claude Code CLI 技能
- `hermes-agent` — Hermes Agent 配置
- `writing-plans` — 出 plan 模板
- `wecom-callback-config` — 企微回调配置
- `windows-wsl-maintenance` — Windows 远程管理（包括 SSH 配置与 WiFi 密码检查）

## Reference Files

- `references/openclaw-capabilities.md` — OpenClaw 能力清单、浏览器使用方式、已知问题
- `references/multi-agent-architecture-plan.md` — 多 Agent 协同架构 Plan
- `references/l123-intent-routing.md` — L123 三层意图路由架构：关键词匹配 → 正则模糊 → LLM 兜底，含配置结构、Agent 分配规则、看板集成、回滚策略
