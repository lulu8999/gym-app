# Windows 软件清单扫描

从 WSL 扫描 Windows 安装程序 + 游戏库 + 便携应用。

## 数据源策略（三层互补）

| 来源 | 覆盖 | 命令 |
|:----|:----|:----|
| 注册表 HKLM\Uninstall | Add/Remove Programs（64位） | `Get-ItemProperty "HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*"` |
| 注册表 WOW6432Node | 32位程序 | `HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*` |
| 文件系统扫描 D:/E: | Steam/Epic/WeGame 游戏 + 便携应用 | `ls /mnt/d/*/` + 特定库路径 |

## PowerShell 命令构造（关键 — 避免引号地狱）

### ✅ 成功模式：stdin 管道（推荐）

```bash
sshpass -p '密码' ssh lulu@100.80.251.96 \
  "echo 'Get-ItemProperty \"HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\*\" | Where-Object { \$_.DisplayName } | Select-Object DisplayName, Publisher | Format-Table -AutoSize -Wrap' | /mnt/c/.../powershell.exe -NoProfile -Command -"
```

**要点：**
- 外层 `"` 给 bash
- PS 命令包裹在 `'` 单引号内
- `$_` 转义为 `\$_.DisplayName` — bash 传 `$_` 到 PS
- 管道通过 stdin 输入 PS，彻底避免转义嵌套

### ⚠️ 失败陷阱

| 错误写法 | 原因 |
|:---------|:-----|
| `"$_"` 不加转义 | bash 替换 `$_` 为空 |
| `'xxx' Where-Object {$_.DisplayName}'` | 引号不配对 |
| 一行两个 `\Uninstall` 路径用逗号 | PS 语法不兼容 |
| 单引号嵌套在双引号内 | bash 解释混乱 |

## GBK 编码处理

中文 Windows PowerShell 输出 GBK 编码，Python 用：

```python
raw = result.stdout.decode("gbk", errors="replace")
```

JSON 输出（ConvertTo-Json -Compress）后用 `json.loads()` 解析，中文乱码可接受。

## 游戏库路径扫描

```bash
# Steam
ls /mnt/d/SteamLibrary/steamapps/common/
ls /mnt/e/SteamLibrary/steamapps/common/

# Epic
ls /mnt/d/epic/

# WeGame
ls /mnt/d/WeGameApps/rail_apps/
ls /mnt/e/WeGameApps/rail_apps/

# EA App
ls /mnt/e/ea/
```

## 便携应用目录扫描

从常见安装目录反查应用名：

```bash
for dir in /mnt/d/*/; do
  basename "$dir"
done
```

重点留意：`Program Files (x86)`、`Program Files`、`ProgramData`、`Users/*/AppData/Local/Programs`

## 分批执行（避免 SSH 超时）

WSL SSH 连接慢（10s+），复杂命令容易超时。策略：

1. 先 `ls -d /mnt/d/*/` 看盘根目录（快速）
2. 再 `ls` 具体游戏库子目录
3. 注册表查询用 stdin 管道单次执行

## 验证清单

| 检查项 | 命令 |
|:------|:-----|
| 64位程序总数 | `ConvertTo-Json` + Python `len()` |
| 32位额外程序 | 比对两注册表结果去重 |
| 最大占用程序 | `Sort-Object EstimatedSize -Descending -Select 10` |
