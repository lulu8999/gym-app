当 `openclaw gateway start` 报 `systemctl restart failed: process exited with code 203/EXEC` 时，通常意味着 systemd 单元文件中的 ExecStart 路径或配置有误。

**诊断：**
```bash
journalctl --user -xeu openclaw-gateway.service | grep "203/EXEC"
# → exec 路径解析失败
```

**修复流程（不要直接重试 `gateway start`）：**
1. 检查并修正 `~/.openclaw/openclaw.json` 中的配置（auth mode、插件条目等）
2. 运行 `openclaw gateway install` — 这会重新生成 systemd 单元文件，修复二进制路径
3. 运行 `openclaw gateway start` — 此时应能正常启动

📌 **核心区别：** `gateway start` 是启动服务，`gateway install` 是重写 systemd 单元。配置改动后一定要先 install 再 start，否则错误的单元文件会导致 203 错误。
