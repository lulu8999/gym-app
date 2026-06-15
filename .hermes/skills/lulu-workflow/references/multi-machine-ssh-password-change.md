# 多机器 SSH 密码统一（Win/WSL/Mac）

> 2026-06-13 实战记录。目标：将三台机器的 SSH 密码统一为同一密码。
> 2026-06-14 更新：确认 Win 笔记本 SSH 端口/用户/密码，发现 22 端口 Windows OpenSSH 故障。

## 架构

| 机器 | IP | SSH 端口 | 用户 | 状态 |
|:----|:---|:--------:|:----|:-----|
| **Windows** | 100.80.251.96 | 2222 | 陆海天 | ✅ 正常 |
| **WSL** | 100.80.251.96 | 22 (netsh转发) | lulu (hostname) | ✅ 正常（实际SSH用户名也是陆海天） |
| **Windows OpenSSH** | 100.80.251.96 | 22 | 陆海天 | ❌ 本机 ssh localhost 都 reset |
| **Mac** | 100.114.207.6 | 22 | lulu | ✅ 正常 |

### 🔴 Windows OpenSSH 22 端口故障（2026-06-14）

**症状**：端口 22 有进程监听（PID 4784），TCP 握手成功，但 SSH banner exchange 超时。
**本机测试**：`ssh localhost` → `kex_exchange_identification: read: Connection reset`
**WSL 用户**：`ssh localhost` → 同样 reset
**结论**：Windows OpenSSH sshd 进程有问题，不是网络/防火墙问题。

**诊断命令**：
```powershell
netstat -nao | findstr ":22 "     # 确认端口监听
ssh localhost                      # 本机测试
Get-Service sshd | Select Status   # 服务状态
Get-Content "C:\ProgramData\ssh\logs\sshd.log" -Tail 10  # 查日志
```

**临时方案**：走 2222 端口（WSL SSH），完全够用。

## 操作步骤

### 1. Windows（远程，可自动化）
```powershell
ssh -p 2222 陆海天@100.80.251.96 "net user 陆海天 新密码"
```

### 2. WSL（远程，需处理交互式）
用 `sshpass -p '旧密码'` 配合：
```bash
sshpass -p '旧密码' ssh lulu@100.80.251.96 'echo -e "新密码\n新密码" | passwd'
```

### 3. Mac（必须本地操作）

**原因**：Mac 的 `passwd` 需要旧密码验证，远程 SSH 时：
- SSH 密钥登录有效（可远程执行命令）
- SSH 密码登录可能不可靠（旧密码可能忘记/不对）
- `passwd` 交互式需要 `-t` 参数

```bash
# 远程正确方式（带伪终端）
ssh -t lulu@100.114.207.6 passwd

# 如果不行，必须本地执行
# 在 Mac 终端直接跑 passwd
```

### 4. Mac 钥匙串同步（密码改完后）

改完密码后，Mac 会提示钥匙串密码不同步：
```
# This tool does not update the login keychain password.
# To update it, run `security set-keychain-password` as the user in question
```

可选方案：
1. **不搞** — 下次锁屏/解锁时 macOS 自动弹窗更新
2. **现在搞** — `security set-keychain-password`（也需伪终端 `-t`）

## 陷阱与教训

| 坑 | 原因 | 解决 |
|:---|:-----|:-----|
| Mac 密码已变，记忆里存的是旧的 | 记忆中密码未更新 | 诚实告诉用户"密码不对" |
| `passwd: conversation failure` | 没加 `-t`（伪终端） | `ssh -t` 强制分配 PTY |
| `passwd: authentication token failure` | 旧密码输入错误 | 无法远程解决，用户本地改 |
| Mac 钥匙串不同步 | 密码改了但钥匙串未更新 | `security set-keychain-password` 或等自动弹窗 |

## 记忆更新

改完后必须更新 memory：
```bash
# 替换旧的密码条目
memory action=replace target=memory old_text="Mac Mini M4 SSH 密码 XXX" content="Mac(...密码新密码)"
# 也可以 add 新的 fact
fact_store action=add content="Mac Mini M4 SSH密码已更新为XXX"
```
