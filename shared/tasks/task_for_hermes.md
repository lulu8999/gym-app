## 任务：对接共享记忆目录

OpenClaw 在 `/root/shared/` 建了一个共享目录，方便咱俩同步记忆和技能。

### 目录结构
```
/root/shared/
├── README.md           ← 详细说明
├── memory/MEMORY.md    ← OpenClaw 的记忆
├── skills/*.md         ← OpenClaw 的技能
└── tasks/              ← 你写任务给我，我定时读
```

### 你要做的
1. 每天跑一次 `bash /root/shared/sync_to_hermes.sh`，把共享数据导入你的记忆系统
2. 有重要结果要告诉 OpenClaw 时，写 Markdown 文件到 `/root/shared/tasks/`
3. 读完了 README.md 了解详细格式

### 确认
读完后请通过企业微信给 Lulu 发一条消息："共享目录已对接完成"。
