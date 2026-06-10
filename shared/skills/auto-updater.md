---
name: auto-updater
description: "Check OpenClaw version against npm registry on startup and auto-update if a newer version exists."
---

# Auto-Updater

开机对比 npm 版本，有更新自动升。

## 流程

1. 对比 `package.json` vs npm registry latest
2. 版本相同 → 结束
3. 有新版本 → `npm install -g openclaw@latest` → 重启 gateway

## 手动调用

"检查更新"、"update openclaw"

## 脚本

- Windows: `scripts/check-update.ps1`（已接入 gateway.cmd）
- Linux/VPS: `scripts/check-update.sh`

## 安全

仅从 npm 升级。失败不阻塞 gateway 启动。
