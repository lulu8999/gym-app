---
name: claude-code-plan-execute
title: Claude Code 规划与审批执行流程
description: "复杂任务先用 Claude Code 做计划 → 展示给用户 → 自我审查 → 报预算审批 → 分步执行"
version: 1.3.0
author: Lulu
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [Planning, Approval, Claude-Code, Workflow, Budget]
    category: software-development
    requires_toolsets: [terminal, file]

---

# Claude Code 规划与审批执行流程

遇到复杂任务（改代码、写功能、重构、论文修改、搭建服务等）时，按以下流程执行。

与 `writing-plans` 的区别：`writing-plans` 教怎么写好的实施计划（内容层面），本技能教的是**从让 Claude Code 出计划到用户批准执行的完整审批闭环**。

> **别名：** 本技能吸收了 `lulu-complex-task-flow`，统称为"复杂任务执行流程"。
> 
> **分工：** Claude Code 出 plan + 写代码，Hermes 全局协调 + 审查，Lulu 审批 + 验收。

## 前置判断：是否需要 Claude Code？

**接到任务后，先判断，再决定是否走流程。** 不要盲目调 Claude Code。

**核心原则：如果自己干超过 10-15 分钟，直接让 Claude Code 干。**

| 自己干（不调 Claude Code） | 走流程（调 claude-code-ds） |
|---|---|
| ≤3 个文件，改动逻辑清晰 | ≥4 个文件，涉及多个模块 |
| 单文件 CRUD、配置微调、日常查看 | 多文件重构、新功能搭建 |
| 自己熟知的技术栈和库 | 不熟悉的框架/语言/工具 |
| 纯读/查操作（查看状态、git log） | 需要生成新代码或修改业务逻辑 |
| 错别字、格式微调 | 批量文件操作、大规模数据处理 |
| **自己干能在 10-15 分钟内搞定** | **自己预估超过 30 分钟** |

**时间基准：** 如果预估自己动手需要超过 30 分钟，**直接调 Claude Code，不要自己先干一半再换人**。用户明确纠正过"第一阶段要3-4小时？你让claude干不就行了"——耗时任务先出 plan 报用户审批，通过后让 Claude Code 执行。

**3 个文件以内、逻辑清楚的，自己直接干，不浪费 token 调 Claude Code。**

## 工作流

### 步骤 0（可选）：Hermes 自己先出草稿
如果任务刚好踩在边界上（3 个文件但逻辑复杂），可以先自己写一个简略计划展示给用户，用户决定是否升级到 Claude Code。

### 步骤 1: 让 Claude Code 做计划

尝试调 claude-code-ds 生成实施计划：

```bash
claude-code-ds -p "分析任务需求，制定详细的实施计划。列出：1) 需要改哪些文件 2) 每步做什么 3) 预计改动量 4) 风险点" --max-turns 5
```

计划应包含：
- 涉及的文件列表（完整路径）
- 具体改动步骤（可执行级别）
- 预估改动量（文件数、代码行数）
- 风险点（可能出问题的地方）

#### ⚠️ Claude Code 故障排查

`claude-code-ds` 或 `claude --bare` 调用失败时，**不要反复试**，按以下顺序诊断：

**1. 基础连通性测试**
```bash
# 测 Claude Code 能否启动
claude --version
# 测 LiteLLM 代理是否存活
curl -s http://localhost:41111/v1/models | python3 -c "import json,sys; d=json.load(sys.stdin); [print(m['id']) for m in d.get('data',[])]"
```

**2. 认证/403 错误**
→ 通常是 `~/.claude/settings.json` 中的 `apiKey` 无效或 `baseUrl` 不对。
```bash
# 验证 settings.json 中的 API Key 是否有效
source /root/.hermes/.env && curl -s "https://api.deepseek.com/v1/models" -H "Authorization: Bearer $(cat /root/.claude/settings.json | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"apiKey\"])')" | head -5
```
**修复：** 用有效的 DeepSeek API Key 更新 settings.json 中的 `apiKey` 字段。

**3. "Claude Provider 缺少 base_url 配置"**
→ `settings.json` 中 `env.ANTHROPIC_BASE_URL` 指向了已失效的代理地址（常见旧地址 `127.0.0.1:15721`）。
**修复：** 更新为 `http://localhost:41111`（PM2 管理的 LiteLLM 代理），或删除该字段让 Claude Code 直连 DeepSeek。

**4. "Invalid model name"**
→ Claude Code 发送的模型名（如 `claude-opus-4-8`）在 LiteLLM 代理中没有映射。
**修复：** 在 `/root/litellm-config.yaml` 中添加对应映射，然后 `pm2 restart litellm-proxy`。

**5. Connection refused / 404**
→ LiteLLM 代理未运行。`pm2 list | grep litellm` 检查。若不在列表中，启动：
```bash
pm2 start /root/start-litellm.sh --interpreter bash --name litellm-proxy
```

**6. API Key 被 mask（写脚本时常见）**

**症状：** 用 `write_file` 写入包含 `sk-xxx` 格式 API Key 的脚本后，实际文件里的 key 被替换成了 `***`。

**修复：** 不要用 `write_file` 写带 key 的内容。改用以下方法之一：
```bash
# 方法 1（推荐）：先写占位符，再用 sed 替换
source /root/.hermes/.env \
  && sed -i "s/PLACEHOLDER/$DEEPSEEK_API_KEY/g" 目标文件

# 方法 2：终端内用 Python 写
python3 -c "
import os
content = open('template.sh').read()
content = content.replace('PLACEHOLDER', os.environ['DEEPSEEK_API_KEY'])
open('output.sh', 'w').write(content)
"
```

**原则：** 含 API Key 的文件永远不要用 `write_file` 写。一发现 key 被 mask，直接切到 sed/Python，不要在几种方法间来回试。

**7. 快速跳过（故障不影响任务进度）**
如果 Claude Code 反复报错，**直接由 Hermes 自己写计划**：
- 简单任务（单文件修改、CRUD 页面、配置调整）：Hermes 自写更省 token
- 复杂任务：Hermes 写计划草稿 → 展示给用户，不因外部工具故障阻塞流程
- 计划的质量比"是否由 Claude Code 写出"更重要



### 步骤 2: 展示计划给用户

**输出要求（严格遵守）：**
- 用**纯中文**呈现
- 不展示原始状态码、errHTTP code、技术日志片段
- 保持简洁，不需要额外解释
- 用 clarify 工具问用户："这是 Claude Code 出的计划，你看有没有要改的地方？"

### 步骤 3: 自我审查 + 完善计划

用户确认/修改后，自己再审视一遍：
- 有没有遗漏关键步骤
- 有没有安全隐患（删文件、改系统配置等需要确认）
- 有没有更好的实现方式
- 有没有兼容性问题

### 步骤 4: 报预算 + 审批

确定最终版本后，**预估 token/费用预算**：

**DeepSeek V4 Flash 参考价：**
- 输入：约 $0.27/百万 tokens
- 输出：约 $1.10/百万 tokens

**DeepSeek V4 Pro 参考价：**
- 输入：约 $1.75/百万 tokens
- 输出：约 $3.50/百万 tokens

**估算方法：**
- 简单文件修改（1-2 文件）：~5-10K tokens → ~¥0.01
- 中等改动（3-5 文件）：~20-50K tokens → ~¥0.03-0.08
- 大型修改（10+ 文件）：~100K+ tokens → ~¥0.15+

用 clarify 报给用户批准：最终 plan + 预估 token 预算，简洁说明。

### 步骤 5: 执行

用户批准后，按步骤分步执行。
每完成一步简洁报告进度。

### 步骤 6: Token 消耗比较 + 经验反思（必须）

任务完成后，**必须**做以下三步：

6. **查实际消耗** — 获取本次会话的 token 统计
7. **对比预算** — 出 plan 时给的 token 预算 vs 实际
8. **写经验反思** — 一段话总结：做得好/不好/下次改进

## 用户偏好：网关重启后自动恢复任务

当网关重启导致会话中断时：
1. **自动检查未完成任务** — 扫描会话历史，确认之前执行中的任务
2. **继续未完成工作** — 不等待用户问才恢复，直接接上继续干
3. **主动报告状态** — 恢复后向用户报告：之前做到哪了，现在继续
4. **不重复已完成的部分** — 检查文件系统状态，已创建的文件不重建

## 多模型策略：各取所长

| 任务类型 | 模型 | 原因 |
|---------|------|------|
| 日常对话、简单查询 | deepseek-v4-flash | 便宜、响应快 |
| 复杂编程、论文修改 | deepseek-v4-pro（委托子 agent） | 推理强 |
| 看图分析 | moonshot-v1-8k-vision-preview（Kimi） | 多模态视觉 |
| 不支持看图时变通 | 用 delegate_task 调 vision toolset | 绕路方案 |

Kimi 配置：
- API Base: `https://api.moonshot.cn/v1`
- Provider: `kimi-coding`
- 可用视觉模型：`moonshot-v1-8k-vision-preview`, `moonshot-v1-32k-vision-preview`, `moonshot-v1-128k-vision-preview`
- Key 存在 `KIMI_API_KEY` env var

## 用户偏好：静默操作

memory、profile、skill 等后台操作执行完毕后，**不要输出任何"已更新""已保存""记下了"等确认文字**。直接执行，不接话。

这个偏好覆盖所有后台管理类操作（memory、skills、config）。只有面向用户的操作（文件改动、服务重启、发送消息）才报告结果。

## Pitfall: 后台进程输出缓冲

使用 `terminal(background=True, notify_on_complete=True)` 启动长时间运行的任务时，Python 进程的 stdout 默认是块缓冲（4KB 或 8KB），不会实时刷新到 `process(action='poll')` 的输出。

**症状：**
- `process(action='poll')` 或 `process(action='log')` 输出为空或只有旧数据
- 但 `ps aux` 显示进程正常运行，文件系统上也有新文件生成
- 等到进程 `notify_on_complete` 触发后，所有输出一次性出现

**原因：** Python 默认 stdout 缓冲策略：连接终端时行缓冲 → 连接管道时块缓冲。后台进程通过管道连接到 Hermes，因此是块缓冲。

**修复（二选一）：**

```bash
# 方式1：命令加 -u 禁用缓冲
python3 -u your_script.py

# 方式2：设环境变量
PYTHONUNBUFFERED=1 python3 your_script.py
```

**更好的替代方案：** 对长时间运行、需要中间状态检查的任务，不要依赖 `process(action='poll')` 的输出。直接检查文件系统状态：

```python
# 检查进度文件内容
cat /path/to/_progress.json | python3 -c "import json,sys; d=json.load(sys.stdin); print(d)"

# 检查输出文件数量
ls output_* | wc -l
```

## 用户偏好：切换模型时自动重置会话

当用户说"切模型/换模型"时，**必须自动**完成以下两步，不需要问"要不要新会话"：

1. **切换模型配置** — 修改会话默认模型
2. **自动重置会话** — 开启全新会话（不带历史上下文）

用户习惯：`deepseek-v4-flash` 日常聊天，`deepseek-v4-pro` 复杂任务委托。切换模型意味着切换到全新上下文，不要保留旧历史。

### 模型切换后的故障诊断

切换模型后如果报错，不要只猜"额度不够"。正确诊断顺序：

1. **先调 API 验证 Key 是否有效** — 401 = Key 无效/过期，余额再多也没用
2. **再查余额/配额** — 429/insufficient_quota = 额度用完

```bash
# Key 有效性验证（以千问为例）
curl -s -w "\\nHTTP %{http_code}" \\
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" \\
  https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation \\
  -H "Content-Type: application/json" \\
  -d '{"model":"qwen-plus","input":{"messages":[{"role":"user","content":"test"}]},"parameters":{"result_format":"message"}}'

# 401 → Key 无效/过期
# 200 → Key 有效

# 余额查询（DeepSeek）
curl -s -H "Authorization: Bearer $DEEPS...EY" \\
  https://api.deepseek.com/user/balance
```

## 陷阱：write_file 自动掩码 API Key

`write_file` 工具会自动将内容中的 `sk-xxx` 格式字符串替换为 `***`，导致写出的文件 key 无效。

**症状：** 写入含 API Key 的脚本后，调试时发现 key 变成了 `***`。

**修复（二选一）：**

```bash
# 方法 1：先写占位符，终端用 sed 替换
source /root/.hermes/.env \
  && sed -i "s/PLACEHOLDER_KEY/$DEEPSEEK_API_KEY/g" 目标文件

# 方法 2：终端内用 Python 写（绕过 write_file 的 mask）
terminal: python3 -c "
import os
template = open('template.yaml').read()
filled = template.replace('PLACEHOLDER', os.environ['DEEPSEEK_API_KEY'])
open('output.yaml', 'w').write(filled)
"
```

**原则：** 含 API Key 的文件**永远不要**用 `write_file` 写。一发现 key 被 mask，直接切到 sed/Python 方式，不要在几种方法间来回试。

## 什么时候走这个流程

**必须走流程：**
- 改系统配置（Caddy、cloudflared、PM2 等）
- 新增/修改服务
- 重构代码
- 搭建新功能
- 文件批量操作

**不需要走流程（直接干）：**
- 日常查看状态（git status、日志查看等）
- 简单的单文件小改（错别字、格式微调）
- 已经明确定义过的定时维护任务
