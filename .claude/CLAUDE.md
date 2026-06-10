# CLAUDE.md — 关于 Lulu

## 你是谁

- 叫我 **Lulu** 就行
- 江苏警官学院学生，东八区（Asia/Shanghai）

## 沟通风格

- 直接说需求，不需要客套话
- 偏好通过任务/命令来传达意图
- 信任度高，但不能滥用
- 技术能力不错，可以聊细节

## 技术环境

- Windows 10.0.26200 (x64), Node 24.x
- 两块 SSD：Predator 1TB + KINGSTON 512GB
- 这台服务器是 VPS（Linux），用来跑后台服务

## 当前项目

1. **微信小游戏** — 计划中，还没开始
3. **网页/小程序** — 计划中

## 规则红线

- 不动 C 盘系统文件
- 不动个人文档，删改前必须问
- 清理缓存日志前确认范围
- 改配置前先检查现有状态

## 关于这个 Claude Code

- 后端走的是 DeepSeek API（通过 LiteLLM 代理翻译）
- 代理运行在 localhost:41111
- PM2 管理，会自动重启
- API Key 在 /root/.claude-code-litellm/.env
- 快捷命令：`claude-code-ds`
