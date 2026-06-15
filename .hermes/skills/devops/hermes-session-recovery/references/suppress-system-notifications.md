# Suppressing System Notifications to Non-Admin Users

## Principle

All system-level notifications — gateway interruption, self-improvement review, permission approval requests — must only be delivered to the **admin user (KuHai)**. Never to other users (圆圆, 师父, 老爹, 妈妈, LuHaiTian).

## Config Settings

### 1. `turn_completion_explainer`

Controls the "Self-improvement review: Memory updated · Skill 'X' created." messages:

```bash
hermes config set display.turn_completion_explainer false
```

### 2. `approvals.mode`

Controls command approval prompts. Smart mode = auto-approve low-risk, prompt on high-risk:

```bash
hermes config set approvals.mode smart
```

High-risk triggers (always prompt): system service changes, file deletion, .env/config overwrite, gateway restart, script execution via -c heredoc.

### 3. Gateway Shutdown Notifications

The Hermes gateway sends shutdown notifications only to the home channel (KuHai):

```
Sent shutdown notification to active chat weixin:o9cq80-Ct2fnApV5l3YGq1e2gWLQ@im.wechat
```

Set via `/sethome` or `WECOM_CALLBACK_HOME_CHANNEL` env var.

### 4. Auto-Resume After Gateway Restart (Unavoidable Leak)

When the gateway restarts, auto-resume injects `[System note: interrupted]` into **all** active sessions — cannot be disabled per-user. The only control is timing the restart when other users (圆圆 etc.) have no active session.

**Mitigation:** Handle the interruption silently for non-admin users — respond without mentioning the restart. The `hermes-session-recovery` skill encodes this pattern.

## Lulu's Explicit Rules (Asia/Shanghai, 江苏警官学院)

- 网关中断通知 → 只发给 KuHai ✅ (home channel set)
- Self-improvement review → 已关闭 ✅ (`turn_completion_explainer: false`)
- 权限审批通知 → 只给 KuHai 批 ✅ (`approvals.mode: smart`)
- 圆圆、师父、老爹、妈妈 → 不应收到任何系统级消息
- [已删除] gateway-restart-handler skill — 内容已合并入 hermes-session-recovery 和 gateway-administration
