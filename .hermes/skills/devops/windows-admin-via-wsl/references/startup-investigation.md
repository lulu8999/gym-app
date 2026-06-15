# Windows 开机启动项排查（Win工具箱 实战记录）

## 背景

Lulu 电脑开机右下角弹出"Win工具箱"，之前通过 OpenClaw 在 C/D/E 盘搜索文件名没找到。怀疑是隐藏程序、服务、或启动项别名。

## 排查路线图（由浅入深）

### 第1层：启动文件夹

```bash
# 当前用户
ls "/mnt/c/Users/陆海天/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/"

# 所有用户
ls "/mnt/c/ProgramData/Microsoft/Windows/Start Menu/Programs/StartUp/"
```

### 第2层：注册表 Run 键

```bash
# HKLM（所有用户）
/mnt/c/.../powershell.exe -NoProfile -Command \
  "Get-ItemProperty \"HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\" | Format-Table -AutoSize -Wrap"

# HKCU（当前用户）
/mnt/c/.../powershell.exe -NoProfile -Command \
  "Get-ItemProperty \"HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\" | Format-Table -AutoSize -Wrap"

# RunOnce（临时的）
/mnt/c/.../powershell.exe -NoProfile -Command \
  "Get-ItemProperty \"HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\RunOnce\" | Format-Table -AutoSize -Wrap"
```

### 第3层：WMI 综合查询（最强）

```powershell
# 比手动查注册表+启动文件夹更全面，合并所有来源
Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location, User
```

### 第4层：任务计划

```powershell
# 模糊匹配任务名
Get-ScheduledTask | Where-Object { $_.TaskName -like "*win*" -or $_.TaskName -like "*tool*" }

# 或全量导出人工筛
Get-ScheduledTask | ForEach-Object { Write-Host $_.TaskName }
```

### 第5层：系统服务

```powershell
Get-Service | Where-Object { $_.DisplayName -like "*工具箱*" -or $_.DisplayName -like "*toolbox*" }
```

### 第6层：已安装程序名排查

如果启动项名称和程序安装名不一致（比如"Win工具箱"可能是 CCleaner / 360 / 腾讯管家 的一个功能组件），查注册表 DisplayName 模糊匹配：

```powershell
Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*" | 
  Where-Object { $_.DisplayName -match "工具箱|优化|大师|管家|win|tool|box" }
```

### 第7层：运行进程 + 窗口标题

```powershell
Get-Process | Where-Object { $_.MainWindowTitle -like "*工具箱*" -or $_.MainWindowTitle -like "*win*" }
```

## 典型结果（Win工具箱 实战）

从排查来看，Lulu 的启动项包括：

| 启动来源 | 程序 | 
|:---------|:-----|
| 启动文件夹 | OpenClaw (Dashboard.url, Gateway.cmd, bat, vbs) |
| HKLM\Run | SecurityHealth (Defender), RtkAudUService (Realtek Audio) |
| HKLM\RunOnce | msedge_cleanup |
| HKCU\Run | OneDrive, Steam, CCleaner Smart Cleaning, Edge auto-launch, Tailscale |
| WMI 总计 | 共 14 个启动项 |

**第5-7层也没找到** — 但进程列表的 SystrayComponent 暴露了真身。

## 实战破案记录（2026-06-13）

### 最终定位路径

```powershell
# 1. 查系统托盘进程发现疑点
Get-Process | Where-Object { $_.ProcessName -match "notify|tray|tool|tip|pop|alert" }
# -> 发现 SystrayComponent 下有 winToolBoxSrv

# 2. 查进程路径
Get-CimInstance Win32_Process -Filter "Name = 'winToolBoxSrv.exe'" |
  Select-Object ProcessId, ExecutablePath
# -> C:\Users\陆海天\AppData\Local\winToolBox\winToolBoxSrv.exe

# 3. 查服务（第5层的正确用法）
Get-CimInstance Win32_Service | Where-Object { $_.PathName -match "winTool" }
# -> 发现 3 个服务：WinToolBoxUpdateSrv, WinInterceptUpdateSrv, pdfReaderUpdateSrv
```

### 流氓软件特征

| 特征 | 本例 |
|:----|:-----|
| 进程名 | winToolBoxSrv.exe + WinTray.exe + cssdk.exe |
| 隐藏方式 | 3 个 Windows Event Notification Services |
| 防护 | icacls 拒绝删除（SoftMgrExt64.dll 等） |
| 位置 | C:\Users\陆海天\AppData\Local\winToolBox\ |
| 子组件 | SoftMgr (360 软件管理), pdfReader, protect/winInterceptSer |
| 是否可卸载 | 无控制面板项，无卸载入口 |

### 清除步骤

```
1. Stop-Service (停3个服务)
2. sc.exe delete (删3个服务)
3. taskkill /F (杀所有进程)
4. rm -rf (删目录，部分DLL权限锁住)
5. takeown + icacls + Remove-Item (处理残留)
```

### 关键教训

1. **服务是最隐蔽的启动方式** — 比注册表 Run 键和启动文件夹更难发现。流氓软件喜欢用 Event Notification Service 伪装。
2. **SystrayComponent 暴露行踪** — 即使显示窗口名不匹配，系统托盘的进程列表仍会暴露。
3. **多个服务抱团** — 一个流氓软件可能注册 3+ 个服务互相保活。
4. **权限锁定是最后防线** — takeown + icacls 才能强删。
5. **重启后验证** — 有些保护在运行时解除不了，需要重启后清理。

### 验证

- `sc query WinToolBoxUpdateSrv` → 服务不存在
- `Test-Path "C:\Users\陆海天\AppData\Local\winToolBox"` → False（重启后）
- 重启后右下角不再弹窗
