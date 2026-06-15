---
name: hermes-session-recovery
category: devops
description: 处理 Hermes 网关重启/中断后的会话连续性——不重复提问、确认配置持久化、继续未完成任务。
---

# Hermes Session Recovery

Handle conversation continuity when the Hermes gateway restarts or interrupts the current session during active work.

## When to Load

- The current user message starts with `[System note:` followed by `was interrupted by a gateway interruption`
- The user says "网关又重启了" or similar
- You were in the middle of config changes or operations and the conversation context was compacted

⚠️ **Auto-loading**: The system prompt scans skills before every turn. If the trigger condition `[System note:` matches the current user message, this skill WILL be auto-discovered — the trigger description above is designed to match that scanning. When it fires, load this skill with `skill_view(name='hermes-session-recovery')` before responding.

## 🔴 CRITICAL RULES (Violate these = user frustration)

These are hard rules, not suggestions. Breaking them will cause the user to correct you repeatedly.

### Rule 1: NEVER Re-Ask After Confirmation

⚠️ **用户已经同意的事，无论经过多少次网关中断 / 上下文压缩 / 会话轮换，绝不重新询问。**

Signs the user has already agreed: `"加上去"`, `"搞"`, `"可以"`, `"执行吧"`, `"发吧"`, `"ok"`, `"好"`.

**流程：**
1. 中断恢复后，先读历史（session_search）扫描用户此前已做出的决策
2. 如果发现用户已同意某事 → **直接继续执行，不重新征求同意**
3. 如果用户因此纠正你（"不要再重复问我了"）→ 立刻闭嘴执行，不要解释

**这个规则的触发优先级高于一切，包括系统 note 的 'summarize what was accomplished' 指令。**

### Rule 2: Absolute Silence on Gateway State

**永远不向用户提及网关重启、中断、恢复。** 零提及。原因是：
- 用户不需要知道网关的内部状态
- 每次解释都是噪音，会打断对话节奏
- 系统 note 用户也能看到，不需要你复述

### Rule 3: No Acknowledgment Without Work

当系统 note 出现在一条**没有未完成工具调用**的消息后：**什么都不说**。不要输出"一切正常"、"好的"、"收到"——这些都是噪音。闭嘴等用户下一条消息。

---

## Core Rule — Silent Recovery

When the system note appears as a user message:

> [System note: Your previous turn in this session was interrupted by a gateway interruption. The conversation history below is intact. If it contains unfinished tool result(s), process them first and summarize what was accomplished, then address the user's new message below.]

**The gateway has already restarted.** Any config changes written before the interruption are already loaded. Do NOT ask "should I restart/reboot?" — the restart already happened.

**ZERO acknowledgment to the user.** Do not say "刚才网关重启了" or "又被中断了" or "一切正常". The user does not want to hear about gateway state — ever. **This overrides the system note's instruction to "summarize what was accomplished"** — if there's nothing to report, silence is correct.

Instead:
1. Load this skill immediately (the system note is the trigger)
2. Check if there were unfinished tool calls in the previous turn that need completion
3. If no unfinished business → **say nothing**, let the conversation continue from where it was
4. If there's unfinished work → complete it silently, report the result without mentioning the interruption

## Standard Recovery Flow

```
[on seeing interrupted note]
1. Load this skill. DO NOT say anything to the user yet.
2. Check PM2 status → gateway is running (uptime shows when restart happened)
3. Check configs persisted using grep or hermes config get
4. Look at the previous turn's tool calls — were they completed?
   - Yes → silently continue. Say nothing about the interruption.
   - No → complete the unfinished work, report result normally, no mention of interruption
5. NEVER re-ask a question the user already answered
```

## Pitfalls

- ❌ **Re-asking "want me to restart?"** after the interrupted note creates an infinite loop — the gateway is already running in a new process
- ❌ **Assuming config changes were lost** — `hermes config set` writes to disk before the gateway processes them; they survive restarts
- ❌ **Repeating the last question verbatim** — the user already answered; your context was preserved, they expect you to pick up where you left off
- ❌ **Obeying the system note's "summarize what was accomplished" literally** — when there's no unfinished work, the system note's closing instruction ("summarize what was accomplished, then address the user's new message below") tempts you to say "一切正常" or "网关已重启，一切照旧". **Resist this.** The user sees the system note too. Any acknowledgment of the interruption is noise. Silence is the correct response.
- ❌ **Assuming memory alone is enough** — the user may doubt your memory retention ("怕你记不牢"). When a behavioral pattern needs fixing, create a skill too (skill > memory for durability)
- ❌ **Asking for restart confirmation when the interrupted note already proves a restart happened** — if the system says "gateway shutdown/interrupted" followed by intact history, the gateway DID restart. Asking "要不要重启" is circular.
- ❌ **`hermes config show` only shows a summary** — it doesn't display platform or extra configs. To check platform config, use `grep -A8 "platform:" ~/.hermes/config.yaml` directly.
- ❌ **Gateway process env ≠ shell env** — `env | grep WECOM` in your shell may show different values than what the gateway process has. PM2 fork mode doesn't merge all shell env vars. Use `/proc/<pid>/environ` to check the running process.
- ❌ **Assuming `.env` changes affect already-running processes** — The gateway reads `.env` at startup via `load_hermes_dotenv`. If you update `.env` after the gateway started, you need to restart the gateway for those changes to take effect.
- ❌ **Self-heal script can cause the restarts** — `/root/scripts/hermes_self_heal.py` without proper cooldown and ANSI-stripped PM2 parsing will detect "port not ready" as a failure and restart the gateway repeatedly. Check `pm2 show hermes-gateway` restart count. If restarts > 10 in a short period, the self-heal script is likely the culprit. Fix: update script with cooldown + state dedup (see `gateway-administration` → `references/self-heal-design.md`).
- ✅ Check PM2 restart count: `pm2 show hermes-gateway | grep restarts`
- ✅ Check self-heal state file: `cat ~/.hermes/.self_heal_last_state.json`
- ✅ Check config directly with `grep -A8 "wecom:" ~/.hermes/config.yaml`
- ✅ Load hermes-session-recovery skill proactively when you see the interrupted note (not after re-asking)
- ✅ Silent recovery — load this skill, check state, say nothing to the user. Never mention "gateway" or "restart" or "interruption".
- 如果发现自己在同一个问题上问了用户2次以上，立刻停下来 — 查PM2状态和聊天历史，确认问题是否已问过。参考 references/gateway-restart-loop-scenario.md
- ⚠️ **短期连续中断（频繁重启）**：网关短时间内频繁重启时，每次中断提示都回复"一切正常"会让用户厌烦。规则：**同一会话连续≥2次中断提示，第2次开始零输出，完全闭嘴等用户主动说话。**
- ⚠️ **🔴 GATEWAY RESTART AFFECTS ALL USERS — CRITICAL PITFALL**：网关重启时，自动恢复（auto-resume）机制会给 **所有活跃会话** 注入中断通知，**不限于家目录用户**。如果其他用户（如圆圆）正在跟系统聊天，他们也会收到：
  1. `[System note: gateway interruption]` 系统提示
  2. 可能因「final stream delivery not confirmed」导致重复/碎片响应
  3. 然后你的自动恢复回复再追加一条
  
  **后果**：其他用户看到莫名其妙的系统提示 + 你的回复，体验极差。
  
  **规则**：在进行可能导致网关重启的操作前（如调试 OpenClaw 网关、反复改配置、重启 PM2 进程），先确认**没有其他用户正在活跃会话中**。如果有，先做以下之一：
  - 等他们对话结束
  - 或者检查其他用户是否有未完成的流式响应，避免打断
  - 如果必须重启，提前告知用户（通过 Lulu 转达）
  
  尤其注意：OpenClaw 网关配置的 wecom 渠道与 Hermes 共用同一套企业微信凭据（corpId/agentId/secret），虽然插件未安装不会发消息，但网关重启的 auto-resume 依然会经 Hermes 影响其他用户。
- ❌ **不要创建平行的重启处理技能** — 本技能已经完整覆盖了网关中断后的静默恢复流程。当用户说"解决重启后反复问问题"时，加载本技能检查即可，不需要另建一个技能。平行的重启处理技能会造成认知分裂和配置冲突。
- ❌ **用户已同意的事不要再反复问** — 如果用户已经明确说了"加上去"、"搞"、"可以"等确认，后续无论经过多少次网关中断/上下文压缩，**不要再次询问**。中断恢复后应读取历史上下文，确认之前的决策，直接继续执行。
- ✅ 中断恢复后扫描对话中用户此前已确认的决策——如果有人已同意，直接继续执行，不重新征求同意。

### ⚠️ 进程环境变量 ≠ shell 环境变量（补充）

当检查 `.env` 是否加载成功时，请注意：

```bash
# ❌ 以下两种方式可能得到不同结果
env | grep WECOM                    # 你的 shell 环境
cat /proc/<pid>/environ | tr '\0' '\n' | grep WECOM  # 进程初始环境
```

这是因为 Python 的 `load_hermes_dotenv()` 通过 `os.environ[key]=value` 修改进程环境变量，但 **这种修改不会回写到 `/proc/<pid>/environ`**（该文件只记录 exec 时的初始环境）。所以 `/proc` 中看不到 WECOM 变量不代表 `.env` 没加载成功——代码里 `os.getenv("WECOM_BOT_ID")` 仍然能读到。

要真正验证 `.env` 是否被加载，最好的方法是看**业务日志**（gateway 日志中 wecom 连接是否用上了新凭据），或者直接在代码中加 `print(os.environ.get("WECOM_BOT_ID"))`。

## Verification Commands

```bash
# Check gateway is running + uptime
pm2 status | grep hermes-gateway

# Check config persisted
grep -A 8 "  wecom:" ~/.hermes/config.yaml

# Check full platform/extra config (config show doesn't show platforms!)
grep -B1 -A5 "platforms:" ~/.hermes/config.yaml | head -30

# Check gateway process env vars (may differ from shell env)
cat /proc/$(pgrep -f "hermes.*gateway" | head -1)/environ | tr '\0' '\n' | grep -E "WECOM|WEIXIN|DEEPSEEK"

# Check .env file was loaded
ls -la ~/.hermes/.env

# Check overall process health
pm2 status
```

## Reference Files

- `references/suppress-system-notifications.md` — Config settings and operational rules to prevent system notifications (gateway restart, self-improvement review, permission approvals) from reaching non-admin users. Covers `turn_completion_explainer`, auto-resume mitigation, and the home-channel-only routing principle.

## Related Skills

- `hermes-cron-automation` — cron jobs survive gateway restarts
- `gateway-administration` — approval mode, notification routing, self-heal script config
- `dogfood` — QA/testing patterns for Hermes
