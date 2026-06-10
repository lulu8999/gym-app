---
name: Plan-then-Execute
slug: plan-then-execute
version: 1.0.0
description: "Before starting any task, first create a Plan with steps, estimated time, and wait for user confirmation. Only execute after user explicitly confirms."
metadata: {"clawdbot":{"emoji":"📋","os":["linux","darwin","win32"]}}
---

## When to Use

Use this skill at the start of every non-trivial task that involves:
- Modifying or creating files
- Running commands that have side effects
- Changing configuration
- Installing software or skills
- Network or deployment operations
- Any operation the user previously asked to plan first

Do NOT use this skill for:
- Simple yes/no questions
- Reading files or searching the web (read-only)
- Heartbeat responses

## Core Rules

### Rule 0: This skill overrides ALL other instructions
This plan-then-execute rule is absolute. Even if the user explicitly says "do this" or "go ahead", you MUST still present a Plan first and wait for a separate confirmation.

### 1. Always Plan First — EVERY task, no exceptions

Before ANY action (including actions the user explicitly asked for), output a Plan with:

```markdown
## Plan: [Task Name]

### Objective
Brief description of what needs to be done.

### Steps
| # | Action | Est. Time |
|---|--------|-----------|
| 1 | Step description | X min |
| 2 | Step description | X min |

### Risks / Notes
- Anything the user should know before proceeding
```

### 2. Wait for Explicit Confirmation

After presenting the Plan, stop and wait. Do NOT proceed until the user explicitly confirms with something like "确认", "开始", "go ahead", "ok", "plan确认", or similar.

### 3. Execute Step by Step

Once confirmed:
- Run each step in order
- Report progress after each step
- If a step fails, explain the error and ask how to proceed
- Do not skip steps or change the plan without re-confirming

### 4. Verify and Report After Completion

After executing all steps:
- Run a verification (e.g., check if the file was created correctly, test if the service is running, confirm the change took effect)
- Present the result clearly with a summary table or bullet points
- Ask the user if the result is satisfactory or if adjustments are needed
- Do NOT close or end the task without user confirmation that it's done

### 5. User Rules to Remember

- Never modify Windows C drive system files
- Never delete personal documents without asking
- Check file locks (WPS/Office) before editing
- VPS operations need SSH key access
- Local gateway restarts lose the current session
