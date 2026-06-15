# Windows 远程性能监控

从 VPS（Linux）通过 SSH 在 Windows 上部署性能监控脚本，采集游戏/应用运行时的 CPU、GPU、内存数据，用于帧率卡顿诊断。

## 适用场景

- 游戏性能诊断（无畏契约 VALORANT、三角洲行动 Delta Force 等）
- 后台进程排查（哪个进程在偷 CPU/GPU）
- 硬件瓶颈分析（CPU 满载 vs GPU 满载 vs 内存不足）

## 架构

```
VPS (Linux) ──SSH(p:2222)──→ Windows 原生 OpenSSH Server
                                  │
                                  ├─ 部署监控脚本到 C:\tmp\
                                  ├─ 创建桌面快捷方式 .bat 供用户双击启动
                                  └─ 采集 CSV 数据 → SCP 回 VPS 分析
```

## 监控脚本模板

完整的 PowerShell 脚本用于每 N 秒采样一次系统状态：

```powershell
$output = "C:\tmp\valorant_monitor.csv"
"Time,CPU_Total_Pct,GPU_Usage_Pct,GPU_Temp_C,GPU_Mem_Usage_Pct,RAM_Total_GB,RAM_Usage_Pct,VALORANT_CPU,VALORANT_RAM_MB,Top_Process" | Out-File -Encoding utf8 $output

while($true) {
    # CPU 总使用率
    $cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average

    # GPU 数据（NVIDIA 独显）
    $gpuUsage = "N/A"; $gpuTemp = "N/A"; $gpuMem = "N/A"
    try {
        $nvidia = & "nvidia-smi" --query-gpu=utilization.gpu,temperature.gpu,memory.used --format=csv,noheader,nounits 2>$null
        if ($nvidia) { $parts = $nvidia.Trim().Split(","); $gpuUsage = $parts[0].Trim(); $gpuTemp = $parts[1].Trim(); $gpuMem = $parts[2].Trim() }
    } catch {}

    # 内存
    $os = Get-CimInstance Win32_OperatingSystem
    $ramTotal = [math]::Round($os.TotalVisibleMemorySize/1MB, 1)
    $ramPct = [math]::Round((1-$os.FreePhysicalMemory/$os.TotalVisibleMemorySize)*100, 1)

    # 目标进程（VALORANT 示例 — 按需改进程名）
    $proc = Get-Process "VALORANT","VALORANT-Win64-Shipping","RiotClientServices" -ErrorAction SilentlyContinue
    $vCpu = if($proc){ [math]::Round(($proc | Measure-Object -Property CPU -Sum).Sum, 1) }else{ 0 }
    $vRam = if($proc){ [math]::Round(($proc | Measure-Object -Property WorkingSet64 -Sum).Sum/1MB, 1) }else{ 0 }

    # CPU 占用最高的进程
    $top = Get-Process | Sort-Object CPU -Descending | Select -First 1 -ExpandProperty ProcessName

    $time = Get-Date -Format "HH:mm:ss"
    "$time,$cpu,$gpuUsage,$gpuTemp,$gpuMem,$ramTotal,$ramPct,$vCpu,$vRam,$top" | Out-File -Append -Encoding utf8 $output
    Start-Sleep -Seconds 3
}
```

### 修改要点

| 要监控的程序 | 修改 Get-Process 参数 |
|:-------------|:---------------------|
| VALORANT | `"VALORANT","VALORANT-Win64-Shipping","RiotClientServices"` |
| 三角洲行动 | `"DeltaForce","DeltaForce-*"` |
| 任意 exe | 用任务管理器查进程名（不含 .exe） |

## 部署脚本到 Windows

### 用户策略：直接用实际 Windows 用户

SSH 时用**实际 Windows 登录用户**（如 陆海天）而非专用 SSH 用户。详见 SKILL.md「用户策略」章节。

### 1. 通过 SSH 写入脚本

```bash
# SCP 脚本文件到 C:\tmp\（先在 VPS 写好，再 SCP 过去）
sshpass -p '密码' scp -P 2222 /tmp/monitor.ps1 \
  '陆海天@100.80.251.96:C:\tmp\monitor.ps1'
```

### 2. 桌面快捷方式（谁登录谁用）

**.bat 必须写到实际用户的桌面，** 路径取决于 SSH 用哪个用户登录：

```bash
# ✅ SSH 以 陆海天 身份登录 → 写陆海天桌面
sshpass -p '密码' scp -P 2222 /tmp/start_monitor.bat \
  '陆海天@100.80.251.96:C:\Users\陆海天\Desktop\启动监控.bat'
```

**注意：** 桌面路径不是 C:\\Users\\lulu\\Desktop\\ —— 用哪个用户 SSH 就写哪个用户的桌面。如果 SSH 用 lulu 写到了 lulu 的桌面，实际用机的用户（陆海天）在桌面上看不到。

## 工作流步骤

### 诊断阶段（先查现有数据，再部署监控）
**用户偏好：先检查游戏/应用自己的日志，不要一上来就搭自定义监控。** 很多游戏（VALORANT、三角洲行动）自带性能/崩溃日志。

```bash
# 查找游戏日志的典型位置（各游戏不同）
# VALORANT via Riot Games 客户端：
dir C:\Users\%USERNAME%\AppData\Local\Riot Games\VALORANT\Saved\Logs\*.log

# 或检查游戏安装目录下的 Logs/Saved 文件夹
dir D:\WeGameApps\VALORANT\ShooterGame\Saved\Logs\*.log

# Windows 事件查看器（游戏崩溃记录）
Get-WinEvent -FilterHashtable @{LogName='Application'; ProviderName='*Riot*'}
```

如果游戏日志足够诊断（帧率、崩溃原因），就不需要自定义监控脚本。

### 部署阶段（你来做）
1. 写 PowerShell 监控脚本 → SCP 到 `C:\tmp\`
2. 写 .bat 桌面快捷方式 → SCP 到桌面
3. 告诉用户：双击 .bat → 开玩 → Ctrl+C 停 → 发 csv

### 分析阶段（用户发回 csv 后）
1. 用 Python/pandas 读取 CSV
2. 检查时间戳对应的 GPU 使用率和温度
3. 检查 CPU 总占用和 top process 排行
4. 看 VALORANT 进程的 CPU/RAM 占用趋势

```python
import pandas as pd
df = pd.read_csv("valorant_monitor.csv")
print(df.describe())
print("GPU 满载次数:", (df["GPU_Usage_Pct"].astype(float) > 95).sum())
print("CPU 高占用进程 TOP5:", df["Top_Process"].value_counts().head())
```

## 常见陷阱

- **.bat 文件双击一闪而过：** cmd.exe 执行完自动关闭。在 .bat 末尾加 `pause` 让用户看到输出。
- **nvidia-smi 需要 NVIDIA 独显：** 只有 NVIDIA 显卡才有，集显/AMD 需用其他方法
- **PowerShell 执行策略：** 脚本需 `-ExecutionPolicy Bypass` 参数绕过
- **SCP 中文路径：** Windows 中文桌面名（如 `桌面` vs `Desktop`）可能不同，用 PowerShell 的 `[Environment]::GetFolderPath("Desktop")` 获取真实路径
- **文件编码：** `Out-File -Encoding utf8` 确保 CSV 可读；`.bat` 文件用 `-Encoding default`（ANSI）避免中文乱码
- **进程名不含 .exe：** PowerShell 的 `Get-Process` 参数不包含 `.exe` 后缀
- **跨用户桌面不可见：** 用 `lulu` 用户 SSH 写到 `C:\Users\lulu\Desktop\`，但实际用机的用户是 `陆海天`，桌面上看不到。必须直接用目标用户 SSH 写对应桌面。
