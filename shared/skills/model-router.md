---
name: model-router
description: "Fast model for chat, deep model for tasks. Route messages based on complexity."
---

# Model Router

按复杂度在 DeepSeek 模型间切换。

## 模型分工

| 档次 | 模型 | 用途 |
|------|------|------|
| ⚡ 快 | `deepseek-chat` | 日常聊天、简单问答、状态汇报、信息确认 |
| 🧠 深 | `deepseek-v4-flash` | 编程开发、数据分析、方案设计、论文润色、复杂推理 |
| 💰 省 | `deepseek-chat` | 心跳检查、NO_REPLY 决策、极简问答 |

## 触发规则

**快模型**（直接回复）：日常闲聊、状态确认、信息传递、简单指令

**深模型**（spawn sub-agent）：代码/开发、分析/推理、文档/论文、方案/计划、Web搜索/调研

## 执行流程

```
闲聊/简单 → 快模型直接回
复杂任务 → spawn sub-agent(model=deepseek-v4-flash, timeout=120s)
           等待结果 → 摘要交付
敏感操作 → 主会话执行，不做 delegate
```
