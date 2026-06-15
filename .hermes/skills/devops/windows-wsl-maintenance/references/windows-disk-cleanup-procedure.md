# Windows C Drive Cleanup via WSL SSH

Systematic approach to analyze and clean Windows C drive from VPS through WSL SSH.

## Prerequisites

- WSL SSH connected: `sshpass -p '20040422lht' ssh lulu@100.80.251.96`
- Windows drives mounted at `/mnt/c/`, `/mnt/d/`

## Step 1: Overview

```bash
df -h /mnt/c /mnt/d
```

Expected output shows total/used/available per drive.

## Step 2: Safe-to-clean Locations (scan with du)

```bash
# User Temp (usually 500MB-2GB)
du -sh /mnt/c/Users/陆海天/AppData/Local/Temp/

# Recycle Bin (can be GBs)
du -sh '/mnt/c/$Recycle.Bin/'

# Browser caches
du -sh /mnt/c/Users/陆海天/AppData/Local/Microsoft/Edge/User\ Data/Default/Cache/
du -sh /mnt/c/Users/陆海天/AppData/Local/Quark/

# Crash dumps
du -sh /mnt/c/Users/陆海天/AppData/Local/CrashDumps/

# Windows logs
du -sh /mnt/c/Windows/Logs/
```

## Step 3: Check but Don't Touch

```bash
# NVIDIA drivers (don't delete)
du -sh /mnt/c/Users/陆海天/AppData/Local/NVIDIA/
du -sh '/mnt/c/Program Files/NVIDIA Corporation/'

# Windows Installer (needed for uninstall/repair)
du -sh /mnt/c/Windows/Installer/

# UWP app data
du -sh /mnt/c/Users/陆海天/AppData/Local/Packages/
```

## Step 4: Clean (with user confirmation)

```bash
# Temp files
rm -rf /mnt/c/Users/陆海天/AppData/Local/Temp/*
rm -rf /mnt/c/Windows/Temp/*

# Recycle Bin
rm -rf '/mnt/c/$Recycle.Bin/*'

# Browser cache (Edge will rebuild)
rm -rf /mnt/c/Users/陆海天/AppData/Local/Microsoft/Edge/User\ Data/Default/Cache/*
```

## Output Format for User

Present results as a table:

| 位置 | 大小 | 说明 |
|------|------|------|
| 用户临时文件 | 1.2GB | 安全删除 |
| 回收站 | 1.3GB | 安全清空 |
| ... | ... | ... |

Split into "✅ 可以安全清理" and "⚠️ 不建议乱动" categories.

## 2026-06-15 实战数据（Lulu 的 Win 笔记本）

| 位置 | 大小 | 类别 |
|------|------|------|
| 用户 Temp | 1.2GB | ✅ 安全清理 |
| 回收站 | 1.3GB | ✅ 安全清理 |
| 夸克缓存 | 450MB | ✅ 浏览器缓存 |
| Edge 缓存 | 280MB | ✅ 浏览器缓存 |
| Windows 日志 | 125MB | ✅ 系统日志 |
| 崩溃转储 | 101MB | ✅ CrashDumps |
| NVIDIA 缓存 | 574MB | ⚠️ 别动 |
| Windows Installer | 664MB | ⚠️ 软件卸载需要 |
| Packages (UWP) | 492MB | ⚠️ 微软应用数据 |

**C盘**: 121GB总容量，100GB已用（83%），清理后可释放 ~3.2GB
