# Windows SSH 踩坑记录

> 2026-06-12，Windows 10.0.26200 安装 SSH Server 的完整踩坑记录。

## 失败方案总结

### 方案 1: `Add-WindowsCapability`
```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
```
- 返回 `Online: True, RestartNeeded: False` 看上去成功
- 但 `C:\Windows\System32\OpenSSH\` 只有客户端工具（ssh.exe, scp.exe），没有 sshd.exe
- 手动 `sc.exe create sshd` + 初始化 host key 后仍无法启动

### 方案 2: `winget`
```powershell
winget install "OpenSSH Server"
```
- 报 `No package found matching input criteria`

### 方案 3: `dism`
```powershell
dism /Online /Add-Capability /CapabilityName:OpenSSH.Server~~~~0.0.1.0
```
- 报错 `错误: 87 - 未识别 Windows 功能名称`

### 方案 4: Win32-OpenSSH 直接下载
```powershell
Invoke-WebRequest -Uri "https://github.com/PowerShell/Win32-OpenSSH/releases/download/v9.5.0.0p1-Beta/OpenSSH-Win64.zip"
```
- GFW 拦截 GitHub，ghproxy 镜像也连不上

### 方案 5: 图形界面添加 "OpenSSH 服务器"
- Win+I → 系统 → 可选功能 → 添加 → "OpenSSH 服务器"
- 添加后 `Get-Service sshd` 显示服务存在但 Stopped
- `Start-Service sshd` 报错无法启动
- `sshd.exe` 仍不在 `C:\Windows\System32\OpenSSH\`

### 方案 6: Tailscale SSH
- Tailscale 管理后台勾选机器 SSH
- 从 VPS `ssh lulu@100.80.251.96` 超时
- 可能是 Tailscale SSH 需要额外配置或端口 22 被防火墙阻挡

## 成功替代方案

### Python HTTP Server（危险，仅紧急时用）
```powershell
cd $env:USERPROFILE\.openclaw
python -m http.server 8888 --bind 0.0.0.0
```
- ⚠️ **这是不安全的**！文件直接暴露在公网（通过 Tailscale IP 可访问）
- 仅在 SSH 彻底不可用、且用户同意的情况下作为临时手段
- **用完后立刻停掉**

## 根因推测

Windows 10.0.26200（Insider Preview 版本）的 OpenSSH Server capability 可能存在 bug：capability 安装报告成功但 sshd.exe 未实际部署。

## 未来建议

1. 如果重装 Windows SSH 仍失败，考虑用 Tailscale SSH（需排查为什么连不上）
2. 或用 `scoop install openssh` 替代（需先装 scoop）
3. 最可靠方案：等 Windows 更新或重装系统
