# WSL SSH via Tailscale 连接指南

> 最后验证：2026-06-15

## 连接参数

| 参数 | 值 |
|------|-----|
| Tailscale IP | 100.80.251.96 |
| SSH 端口 | 22 |
| 用户名 | lulu |
| 密码 | 20040422lht |

## WSL 系统信息

| 项目 | 值 |
|------|-----|
| 系统 | Ubuntu 26.04 LTS (Resolute Raccoon) |
| 内核 | WSL2 (6.18.33.1-microsoft-standard) |
| 架构 | x86_64 |
| 内存 | 6.6GB |
| CPU | AMD Ryzen 7 7735H |

## Windows 磁盘布局

| 盘符 | 大小 | 已用 | 挂载点 |
|------|------|------|--------|
| C: | 121GB | 100GB (83%) | /mnt/c |
| D: | 356GB | 211GB (60%) | /mnt/d |

⚠️ C 盘 83% 满，需清理

## 快速命令

```bash
# 连接 WSL
sshpass -p '20040422lht' ssh -o StrictHostKeyChecking=no lulu@100.80.251.96

# 查看 Windows 桌面
ls /mnt/c/Users/陆海天/Desktop/

# 查看 Windows D 盘
ls /mnt/d/

# 查看 Windows 已安装软件
ls /mnt/c/Program\ Files/
ls /mnt/c/Program\ Files\ \(x86\)/

# 查看 Windows 用户目录
ls /mnt/c/Users/陆海天/
```

## Tailscale 设备列表（截至 2026-06-15）

| 设备名 | IP | 系统 | 状态 |
|--------|-----|------|------|
| vm-0-3-opencloudos | 100.80.33.29 | Linux (VPS) | - |
| lulu | 100.80.251.96 | Windows | idle |
| lulus-mac | 100.114.207.6 | macOS | - |
| vivo-v2405a | 100.99.172.19 | Android | offline |
