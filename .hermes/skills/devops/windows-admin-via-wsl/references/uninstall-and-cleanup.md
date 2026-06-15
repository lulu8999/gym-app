# Windows 应用卸载 + 清理实战记录

## 会话背景

从 VPS 远程管理 Lulu 的 Windows (WSL), 批量卸载 C 盘不常用应用 + 清理 Temp。

## 卸载方式对照

| 卸载方式 | 适用场景 | 命令示例 | 成功率 |
|:---------|:---------|:---------|:------:|
| `/S` 参数 | NSIS 安装包（Octopus, 完美世界） | `"Uninstall.exe" /S` | ✅ 高 |
| `/SILENT` | Inno Setup 安装包（龙猫云） | `"unins000.exe" /SILENT` | ✅ 高 |
| `/quiet` | MSI 安装包（Epic） | `msiexec /x {GUID} /quiet` | ❌ 易失败 |
| 裸跑 | 无静默参数（腾讯会议, 天翼校宽） | 直接运行 Uninstall.exe | ✅ 能用 |
| WMIC | MSI 备选 | `wmic product where "name like '%X%'" call uninstall` | ⚠️ |

## 静默卸载实战记录（2026-06-13）

| 应用 | 路径 | 静默参数 | 结果 |
|:----|:----|:--------:|:----:|
| 完美世界竞技平台 | D:\\新建文件夹 (2)\\perfectworldarena | `/S` ✅ | ✅ |
| Octopus 8.7.7 | E:\\bazhuayu\\Octopus | `/S` ✅ | ✅ |
| 腾讯会议 | E:\\txhuiyi\\WeMeet\\3.40.2.407 | 无 | ✅ |
| 天翼校宽 | E:\\新建文件夹\\Chinatelecom_JSPortal | 无 | ✅ |
| 龙猫云机场 | D:\\lm | `/SILENT` ✅ | (未删,保留) |
| Epic Games Launcher | C:\\Program Files (x86)\\Epic Games | MSI /quiet ❌ | 失败(保留) |
| Epic Online Services | C:\\Program Files (x86)\\Epic Games\\Epic Online Services | MSI /quiet ❌ | 失败(保留) |
| 三角洲行动缓存 | 见 WeGame 缓存路径 | N/A | ✅ 释放~1.3GB |

## 游戏缓存清理实战（Delta Force）

| 缓存目录 | 大小 | 
|:---------|:----:|
| `tiny_cache/` (根目录) | 250MB |
| `icreate/tiny_cache/` | 720KB |
| `DeltaForce/Saved/webcache_*` + `pixuicache` | ~1.1GB (含在Saved) |
| `DeltaForce/Content/PipelineCacheData/` | 25MB |
| **合计** | **~1.3GB** |

## 开机启动项实战（Win工具箱 — 破案实录）

### 发现路径

| 排查层 | 发现 |
|:-------|:-----|
| 1-4 (启动文件夹/Run/任务计划) | 未找到 |
| 5 (服务) | 一开始漏了（模糊匹配没命中） |
| 6 (进程) | 找到 SystrayComponent -> winToolBoxSrv.exe |
| 反查服务 | 3 个隐藏服务（WinToolBoxUpdateSrv 等） |

### 流氓信息

| 属性 | 值 |
|:----|:----|
| 可执行路径 | C:\Users\陆海天\AppData\Local\winToolBox\winToolBoxSrv.exe |
| 隐藏服务(3) | WinToolBoxUpdateSrv, WinInterceptUpdateSrv, pdfReaderUpdateSrv |
| 组件 | WinTray.exe, cssdk.exe, SgxHelper64.exe, SoftMgr(360软件管理) |
| 权限防护 | SoftMgrExt64.dll 等用 icacls 锁定 |

### 清除记录

| 步骤 | 结果 |
|:-----|:----:|
| 停服务 + sc.exe delete | 3 个全部删除 |
| taskkill /F | 所有进程杀掉 |
| rm -rf 删目录 | 主程序删了，部分DLL权限锁住 |
| takeown + icacls | 进程还在时失败 |

**建议：** 重启后可彻底清除残留。服务已删 -> 不会自启。

### 关键教训

1. **进程遍历是核武器** — 无论服务名/文件名如何伪装，进程列表会暴露所有运行中的可执行路径。
2. **模糊匹配要兼顾中英文** — 查服务时 -match 工具箱 没命中，但进程名是英文 winToolBoxSrv。
3. **SystrayComponent 暴露行踪** — Get-Process 用 SystrayComponent 过滤能发现隐藏的托盘程序。

## 应用实际安装位置（注册表虚标案例）

注册表显示 QQ 占 1GB, 但 UninstallString 路径在 D:\腾讯qq，实际不占 C 盘：

| 应用 | 注册表显示 | 实际路径 | 占 C 盘? |
|:----|:----------|:---------|:--------:|
| QQ | — | D:\腾讯qq | ❌ |
| 迅雷 | — | D:\迅雷 | ❌ |
| 网易云音乐 | — | D:\CloudMusic | ❌ |
| 小黑盒加速器 | — | D:\Qingfeng | ❌ |
| 龙猫云机场 | — | D:\lm | ❌ |
| 钉钉 | — | E:\dd | ❌ |
| 企业微信 | — | E:\WXWork | ❌ |
| Octopus | — | E:\bazhuayu | ❌ |
| 腾讯会议 | — | E:\txhuiyi | ❌ |
| 完美世界 | — | D:\新建文件夹 (2) | ❌ |
| Epic | — | C:\Program Files (x86) | ✅ |

## 清理验证结果

| 缓存位置 | 清理前 | 清理后 |
|:---------|:------|:------|
| C:\Windows\Temp | 405MB | 0 (清空) |
| C:\Users\陆海天\AppData\Local\Temp | 903MB | 18 个锁文件 |
| C:\Windows\SoftwareDistribution\Download | 896KB | (太小没动) |
