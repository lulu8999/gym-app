# Hermes 看门狗脚本运维指南

## 脚本位置

```
/root/.hermes/scripts/hermes_watchdog.py
```

## 功能说明

- 检查系统服务状态
- 异常时自动尝试重启
- 连续失败 3 次后停止重试并通知
- 配合 cron `no_agent=True` 使用，无异常时静默

## 2026-06-09 修复：Gateway 检查错误

### 问题现象

看门狗报错：
```
⚠️  Gateway(hermes-gateway) 未运行
🔄 开始自动恢复（第3次尝试）...
❌ Gateway 重启失败
❌ Gateway 仍未恢复，需要人工介入
```

### 根本原因

看门狗代码检查的是 **systemd user service**：
```python
services = [
    ('hermes-gateway', 'Gateway'),
]
```

但实际 Gateway 运行方式是：
- 启动脚本：`/root/run-hermes-gateway.sh`
- 运行进程：直接 `hermes gateway run`（Python 进程）
- **不是 systemd 服务**

导致检测一直失败，误报不断。

### 修复方案

删除对 gateway 的错误检查：
```python
services = []  # 不再检查 gateway，因为它不是 systemd 服务
```

### 后续运维原则

**重要**：如果 Gateway 需要被监控，应该：
1. 检查实际运行方式（进程名、端口、脚本路径）
2. 不要假设服务一定是 systemd 托管
3. 或者让 Gateway 通过 systemd 托管（但目前不是）

## 常用运维命令

```bash
# 手动运行看门狗（测试用）
python3 /root/.hermes/scripts/hermes_watchdog.py

# 查看看门狗状态
ps aux | grep hermes_watchdog

# 查看最近的重试记录
cat /tmp/hermes_watchdog_retries 2>/dev/null || echo "无记录"

# 查看冷却状态
cat /tmp/hermes_watchdog_last_restart 2>/dev/null || echo "无记录"

# 删除锁文件（如需强制重新运行）
rm -f /tmp/hermes_watchdog.lock
```

## 注意事项

- 看门狗只检查 `services` 列表中定义的服务
- 当前列表为空（修复后），所以不会产生任何输出
- Gateway 实际由其他方式监控（如端口检查）
