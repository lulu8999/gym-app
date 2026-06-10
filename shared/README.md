# 共享目录（Hermes ↔ OpenClaw）

## 目录结构
- memory/  — 记忆文件（Markdown 格式，UTF-8）
- skills/  — 技能说明（Markdown 格式）
- tasks/   — 任务交接（Hermes 跑完 cron 后写结果，OpenClaw 读取）

## 格式约定
- 文件编码：UTF-8
- 记忆格式：## 日期 \n - key: value
- 技能格式：# 技能名 \n 描述
- 任务格式：## 任务名 \n 结果: xxx

## 读写规则
- 不删对方的文件
- 只追加，不改写
- 写之前加一行时间戳
