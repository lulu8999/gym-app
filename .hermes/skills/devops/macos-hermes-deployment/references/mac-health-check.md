# Mac 综合健康检查

> 一键式远程健康检查脚本，覆盖 13+ 维度。SSH 到 Mac 后执行。
> 适用于：日常巡检、故障排查前、更新配置后验证。

## 一键检查脚本

```bash
ssh lulu@<MAC-IP> '
echo "=== 1. 系统信息 ===" && uname -a && echo "" &&
echo "=== 2. 运行时间 ===" && uptime && echo "" &&
echo "=== 3. 磁盘 ===" && df -h / /Volumes/ssd 2>/dev/null && echo "" &&
echo "=== 4. 内存 ===" && vm_stat | head -10 && echo "" &&
echo "=== 5. Hermes 进程 ===" && ps aux | grep "hermes gateway" | grep -v grep && echo "" &&
echo "=== 6. 端口监听 ===" && lsof -i -P -n | grep -E "LISTEN|hermes|litellm|postgres" | head -20 && echo "" &&
echo "=== 7. launchd 服务 ===" && launchctl list | grep -E "hermes|litellm" && echo "" &&
echo "=== 8. Tailscale ===" && ifconfig utun4 2>/dev/null | grep "inet " && echo "" &&
echo "=== 9. PostgreSQL ===" && pg_isready -h /tmp 2>&1 && echo "" &&
echo "=== 10. LiteLLM ===" && ps aux | grep litellm | grep -v grep | head -3 && echo "" &&
echo "=== 11. .env 完整性 ===" && grep -c "^[A-Z]" ~/.hermes/.env && echo "条环境变量" && echo "" &&
echo "=== 12. 外接 SSD ===" && ls -la /Volumes/ssd 2>/dev/null | head -5 && echo "" &&
echo "=== 13. 日志异常 ===" && grep -i "error\|fail\|exception\|traceback" ~/.hermes/logs/gateway-stderr.log 2>/dev/null | tail -10 || echo "无异常"
'
```

## 维度速查

| # | 检查项 | 正常值 | 异常信号 |
|:-:|:------|:------|:--------|
| 1 | 系统版本 | macOS 15.x (Darwin) | — |
| 2 | 运行时间 | uptime 显示 | 刚重启（<5min）需确认是否有意 |
| 3 | 磁盘空间 | / 剩余 >20% | <10% 需清理 |
| 4 | 内存 | Pages free + inactive 充足 | swap 大量使用 |
| 5 | Hermes 进程 | 存在 1 个 hermes gateway 进程 | 无进程 → 服务挂了 |
| 6 | 端口 | hermes(8645), litellm(41111), pg(5432) 在 LISTEN | 缺端口 → 服务未启动 |
| 7 | launchd 服务 | PID+0(正常) 或 PID+exit码 | exit 78(配置错), exit 77(启动即崩) |
| 8 | Tailscale | inet 100.x.x.x | 无 utun4 → Tailscale 未连 |
| 9 | PostgreSQL | pg_isready 返回端口 | 无响应 → PG 未启动 |
| 10 | LiteLLM | 进程存在, 端口 41111 | 无进程 → LM 代理挂了 |
| 11 | .env | >5 条环境变量 | 0 条 → .env 未加载或为空 |
| 12 | 外接 SSD | /Volumes/ssd 存在 | 不存在 → 未挂载 |
| 13 | 日志异常 | 无 error/fail/traceback | 有 error → 需排查 |

## 快捷诊断

### launchd 服务卡在 exit 78

```bash
launchctl print gui/501/com.hermes.gateway 2>&1
```
看 `state` 是否为 `spawn scheduled` 以及 `penalty box` 是否开启。

### 手动启动绕过 launchd（SSH 远程时）

```bash
eval "$(/opt/homebrew/bin/brew shellenv bash)"
export PATH=$PATH:/Users/lulu/.local/bin
cd /Users/lulu
nohup hermes gateway > ~/.hermes/logs/gateway-stdout.log 2> ~/.hermes/logs/gateway-stderr.log &
```

### 查看完整 launchd 详细信息

```bash
launchctl print gui/501/com.hermes.gateway
# 关注：runs, last exit code, state, properties(含penalty box), environment
```

## 常见问题对照

| 症状 | 可能原因 | 检查命令 |
|:----|:---------|:--------|
| Hermes 不在跑 (no process) | launchd 卡 exit 78 | `launchctl list com.hermes.gateway` |
| launchd exit 78 且手动跑正常 | plist 中 bash 路径不存在 | `ls -la /opt/homebrew/bin/bash` |
| bootout 报 Error 5 | SSH 远程无法操作 gui 域 | 用 nohup 手动启动代替 |
| 微信桌面客户端占用资源 | Mac 端登录了微信 | `ps aux | grep WeChat | grep -v grep` |
| brew/tailscale 命令找不到 | SSH 的 PATH 不含 brew 路径 | `eval "$(/opt/homebrew/bin/brew shellenv bash)"` |