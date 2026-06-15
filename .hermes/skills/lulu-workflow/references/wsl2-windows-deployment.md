# WSL2 Windows 部署参考

## 核心要点

### 1. WSL 不支持图形界面应用
- WSL默认没有X Server
- Electron应用（如Hermes Desktop）无法在WSL中显示窗口
- **解决方案**：在Windows原生安装GUI应用，通过SSH连接WSL后端

### 2. SSH连接超时处理
- Windows原生SSH端口：2222（用户陆海天）
- WSL SSH端口：22（用户lulu）
- 连续3次超时 → 告诉用户检查网络/Tailscale
- 不要无限重试

### 3. 监控脚本路径验证
- 创建快捷方式前必须验证目标文件路径
- 用`dir`或`ls`确认文件存在
- 检查文件内容确认功能正确

### 4. GitHub下载超时
- 尝试在VPS下载，再scp到目标机器
- 使用代理镜像（如ghproxy.com）
- 告诉用户手动下载

### 5. 游戏日志查找
- VALORANT不在标准位置存储详细性能日志
- 依赖自定义监控脚本（`C:\tmp\valorant_monitor.csv`）
- Riot Games日志路径：`C:\Users\陆海天\AppData\Local\Riot Games\`

## 常用命令

```bash
# 测试网络连接
ping -c 2 100.80.251.96

# 检查Tailscale状态
tailscale status

# Windows原生SSH
ssh -p 2222 陆海天@100.80.251.96

# WSL SSH
sshpass -p '111111' ssh -o StrictHostKeyChecking=no lulu@100.80.251.96

# 验证文件存在
sshpass -p '      ' ssh -o StrictHostKeyChecking=no -p 2222 陆海天@100.80.251.96 "if exist C:\path\to\file (echo 存在) else (echo 不存在)"
```

## 教训记录

| 日期 | 问题 | 解决方案 |
|------|------|----------|
| 2026-06-13 | 桌面启动脚本路径错误 | 验证目标文件路径后再创建快捷方式 |
| 2026-06-13 | SSH连接频繁超时 | 连续3次超时后告诉用户检查网络 |
| 2026-06-13 | WSL无法运行GUI应用 | 建议在Windows原生安装 |
| 2026-06-13 | GitHub下载超时 | 在VPS下载后scp到目标机器 |
