# 多模型搭配：Kimi 看图 + DeepSeek 编程

## 配置

已配好 Kimi (moonshot) API，用 `kimi-coding` provider：
- Provider name: `kimi`
- API Key: `KIMI_API_KEY`（在 ~/.hermes/.env）
- Base URL: `https://api.moonshot.cn/v1`
- Config 位置：`config.yaml` 中 `providers.kimi`

## 可用视觉模型

| 模型 | 用途 |
|------|------|
| `moonshot-v1-8k-vision-preview` | 看图，短文本 |
| `moonshot-v1-32k-vision-preview` | 看图，中等长度 |
| `moonshot-v1-128k-vision-preview` | 看图，大文档 |
| `kimi-k2.6` / `kimi-k2.5` | 编程推理 |

## 使用方式

日常对话和编程用 DeepSeek（deepseek-v4-flash）。
需要看图时通过 delegate_task 派子 agent 用 Kimi 处理，toolsets 包含 `vision`。

## 注意

- Kimi 视觉模型不支持工具调用，只能做纯文本+图片分析
- 复杂任务（看图分析 + 后续操作）需要拆成两步：Kimi 看图输出文本描述 → DeepSeek 根据描述继续操作
