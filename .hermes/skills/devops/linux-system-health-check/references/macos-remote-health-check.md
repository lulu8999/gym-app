# macOS 远程健康检查 — SSH 诊断命令集

## 使用场景
通过 SSH 远程检查 Mac（Mini/笔记本）的系统状态，判断是否有硬件/软件隐患。

## 基础信息采集

```bash
ssh lulu@<ip> '
echo "=== 系统概况 ===" && uname -a &&
echo "=== 运行时间 & 负载 ===" && uptime &&
echo "=== CPU ===" &&
  sysctl -n machdep.cpu.brand_string &&
  sysctl -n hw.ncpu &&
echo "=== 内存 ===" && top -l 1 -s 0 | grep -E "PhysMem|VM" &&
echo "=== 磁盘 ===" && df -h / /Volumes/ssd 2>/dev/null &&
echo "=== 电池 ===" && pmset -g batt 2>/dev/null
'
```

## 关键指标解读

| 指标 | macOS 命令 | 健康范围 |
|------|-----------|---------|
| CPU 负载 | `uptime` → load averages | < CPU 核心数（M4=10） |
| 内存压力 | `top -l 1 \| grep PhysMem` | "unused" > 1G |
| Swap 活动 | `top -l 1 \| grep VM` → swapins/swapouts | 都为 0 最佳 |
| 磁盘空间 | `df -h /` | < 80% |
| SMART 状态 | `diskutil info disk0 \| grep SMART` | Verified |
| 睡眠设置 | `pmset -g \| grep sleep` | sleep 0 = 已禁用 |

## 进程诊断

```bash
# 内存大户 TOP 10
ps -eo pid,rss,comm | sort -rnk2 | head -10 | awk '{printf "%s %6.0fMB %s\n", $1, $2/1024, $3}'

# CPU 大户 TOP 10
ps -eo pid,%cpu,comm | sort -rnk2 | head -10

# 进程总数
ps aux | wc -l
```

## 系统日志查错

```bash
# 最近 1 小时的错误日志（macOS 用 log 命令，不是 journalctl）
log show --predicate 'eventMessage contains[c] "error" or eventMessage contains[c] "fail"' --last 1h --style compact | tail -15
```

## 磁盘 IO

```bash
# 采样 2 次，间隔 1 秒
iostat -c 2 -w 1 | head -5
```

## 温度（需要 sudo）

```bash
sudo powermetrics --samplers smc -i 1 -n 1 2>/dev/null | grep -i "temp" | head -5
```

## macOS vs Linux 差异速查

| 功能 | Linux | macOS |
|------|-------|-------|
| 系统日志 | `journalctl` | `log show` |
| 内存 | `free -h` | `top -l 1 -s 0 \| grep PhysMem` |
| 磁盘健康 | `smartctl` | `diskutil info disk0 \| grep SMART` |
| 睡眠控制 | `systemctl mask sleep.target` | `pmset sleep 0` |
| CPU 信息 | `lscpu` | `sysctl -n machdep.cpu.brand_string` |
| 温度 | `sensors` | `sudo powermetrics` |
| 电池 | `/sys/class/power_supply/` | `pmset -g batt` |

## macOS 内存哲学（向用户解释用）

macOS 的内存策略是 **"空闲内存是浪费的内存"**：

- 系统会主动用 RAM 做文件缓存（buff/cache）、压缩存储（compressor）
- `PhysMem: 11G used` 不代表内存不足，只是系统在高效利用
- **判断内存是否真的紧张，看 swap 活动：**
  - `swapins: 0, swapouts: 0` → 健康，内存完全够用
  - swap 活动持续增加 → 真的内存不足，需要关应用
- Wired（内核锁定）+ Compressor（压缩内存）是系统正常开销
- 一般 16G 的 Mac，日常使用 10-12G 是正常范围

**Kill 应用释放内存：**
```bash
# 关闭指定应用
killall <AppName>

# 关闭后验证内存释放
top -l 1 -s 0 | grep PhysMem
```

## 诊断 checklist

- [ ] 负载 < 核心数
- [ ] 内存 available > 1G
- [ ] swapins/swapouts = 0
- [ ] 磁盘 < 80%
- [ ] SMART = Verified
- [ ] 无系统错误日志
- [ ] 无异常 CPU/内存大户
