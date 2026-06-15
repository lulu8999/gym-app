# Windows Cleanup Session — 2026-06-13

## Scope
Full cleanup of Lulu's gaming PC (机械革命 laptop, Windows 11). Three drives: C: 80GB (system), D: 356GB (apps/games), E: 954GB (games/data).

## Removed

| Item | Size | Method |
|:---|:---:|:---:|
| 完美世界竞技平台 | 583MB | EXE uninstaller /S |
| 腾讯会议 | 699MB | WeMeetUninstall.exe /S |
| Octopus/八爪鱼 | 289MB | Uninstall.exe /S |
| 天翼校宽认证 | small | Uninstall.exe /S |
| Delta Force caches | ~1.3GB | rm -rf on 4 cache dirs |
| D: Recycle Bin | 397MB | rm -rf |
| D: Driver (driver backup) | 4.0GB | rm -rf |
| E: 360MoveData | 6.2GB | PowerShell Remove-Item (needed WeChat killed first) |
| E: 迅雷云盘 (macOS 16GB ISO) | 16GB | rm -rf |
| E: 5E对战平台 | 455MB | rm -rf |
| Temp files (C:\Windows\Temp + User Temp) | ~1.3GB | rm -rf |
| E: 新建文件夹(2)/NoteExpress | 602MB | rm -rf |
| **Total** | **~31.8GB** | |

## winToolBox Malware Removal

- **Location**: `C:\Users\陆海天\AppData\Local\winToolBox\`
- **3 services registered** (stopped + `sc delete`):
  - `WinToolBoxUpdateSrv` (main, `winToolBoxSrv.exe`)
  - `WinInterceptUpdateSrv` (interceptor, `winInterceptSer.exe`)
  - `pdfReaderUpdateSrv` (pdf reader, `pdfReaderSrv.exe`)
- **Found via**: `Get-Process` query for system tray processes (`-match 'notify|tray|tool|tip|pop|alert'`)
- **Remaining locked files**: `Tools\SoftMgrbcff1feb\SoftMgr\SoftMgrExt64.dll` — permission-locked, required reboot or manual deletion
- **Key insight**: Also had some 360-related components (`SoftMgr` = 软件管理), likely bundled install

## Disk Layout After Cleanup

| Drive | Total | Used | Free |
|:---|:---:|:---:|:---:|
| C: (system) | 80GB | — | — |
| D: (apps/games) | 356GB | ~287GB | 69GB |
| E: (games/data) | 954GB | ~560GB | 356GB |

## Biggest Space Consumers (E: drive)

- God of War Ragnarok — 176GB
- Split Fiction — 88GB
- The Outlast Trials — 57GB
- SteamLibrary other games — ~46GB

## Tools Used

- WSL SSH: `sshpass -p '111111' ssh lulu@100.80.251.96`
- PowerShell via WSL: `/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe -NoProfile -Command "..."`

## Connection Notes

- SSH to WSL can be slow (10-120s per command on large NTFS directories)
- `timeout N` is essential for `du` commands on large folders
- Some commands need 120s+ timeout (MSI uninstall, full `du -sh` scans)
