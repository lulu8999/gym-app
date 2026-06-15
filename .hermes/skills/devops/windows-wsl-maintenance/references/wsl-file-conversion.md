# WSL 文件格式转换指南

## 适用场景
用户需要将 Windows 上的文件通过 WSL 转换成其他格式（如 ncm→mp3）。

## 标准流程

### 1. 判断操作路径
- Windows 文件本身有转换工具 → 直接在 Windows 上处理
- Linux 工具有优势（如 ffmpeg） → 通过 WSL 处理
- 需要预编译二进制 → 从 VPS 下载，SCP 传到 Windows Temp，再复制到 WSL

### 2. 连接模式

```bash
# Windows SSH (port 2222) → cmd → wsl 模式
sshpass -p '<密码>' ssh -p 2222 陆海天@<win-ip> \
  "cmd /c \"wsl -u lulu bash -l -c '<command>'\""
```

**为什么用 `cmd /c` 不用 `powershell -Command`**：
当命令中包含 bash 操作符（`&&`, `|`, `<`等）时，PowerShell 会将其解释为自己的操作符导致报错。`cmd /c` 直接透传给 wsl，无此问题。

### 3. 文件传输到 WSL

```bash
# VPS → Windows Temp (SCP)
scp -P 2222 <本地文件> 陆海天@<win-ip>:C:\\Temp\\

# Windows Temp → WSL (通过 cmd)
cmd /c "wsl -u lulu bash -l -c \"cp /mnt/c/Temp/<文件> ~/bin/ && chmod +x ~/bin/<文件>\""
```

### 4. 安装常用转换工具

#### ncmdump（网易云 ncm → mp3/flac）
```bash
# VPS 下载 + SCP 传输（需代理，VPS不可直连GitHub）
curl -sL --proxy http://127.0.0.1:7890 -o ncmdump.zip \
  https://github.com/taurusxin/ncmdump/releases/download/1.5.1/ncmdump-1.5.1-linux-amd64.zip
unzip ncmdump.zip

# SCP 传到 Windows
sshpass -p '<密码>' scp -P 2222 ncmdump 陆海天@<win-ip>:C:\\Temp\\

# WSL 安装
sshpass -p '<密码>' ssh -p 2222 陆海天@<win-ip> \
  "cmd /c \"wsl -u lulu bash -l -c 'mkdir -p ~/bin && cp /mnt/c/Temp/ncmdump ~/bin/ && chmod +x ~/bin/ncmdump'\""

# 批量转换
sshpass -p '<密码>' ssh -p 2222 陆海天@<win-ip> \
  "cmd /c \"wsl -u lulu bash -l -c \\\"cd /mnt/c/Users/陆海天/Desktop/vipmusic && ~/bin/ncmdump *.ncm\\\"\""
```

注意：`*` 通配符在多层引号中会被 bash 正确展开，但需确保 `"` 转义准确。

⚠️ **ncmdump 不支持目录参数** — 只能用 `*.ncm` 通配符或逐个文件传参。`ncmdump /path/to/dir/` 会报 `is not a valid file`。

#### 替代方案：Windows Python ncmdump（无需 WSL）

当直接 SSH 到 Windows（2222 端口）且不需要 WSL 参与时，可用 Python 包：

```bash
# 安装（一次性）
sshpass -p '<密码>' ssh -p 2222 陆海天@<win-ip> "E:\Python\python.exe -m pip install ncmdump"

# 写转换脚本到本地 → SCP 到 Windows → 执行
sshpass -p '<密码>' scp -P 2222 /tmp/convert_ncm.py 陆海天@<win-ip>:'C:\Users\陆海天\Desktop\convert_ncm.py'
sshpass -p '<密码>' ssh -p 2222 陆海天@<win-ip> "E:\Python\python.exe C:\Users\陆海天\Desktop\convert_ncm.py"
```

Python API：`ncmdump.dump(str(ncm_file_path))` — 返回转换后的文件路径（保存在源文件同目录），需 `shutil.move()` 到目标目录。

详见 `references/ncm-conversion.md` 中的完整脚本模板。

### 5. 转换后清理
转换成功后询问用户是否删除原始文件（`.ncm`）以节省空间。⚠️ **未经用户确认，不要擅自转换文件**。用户要求"只装工具，等指令再转"。

## 引用
- ncmdump 下载: https://github.com/taurusxin/ncmdump/releases
- VPS 访问 GitHub 需加代理: `--proxy http://127.0.0.1:7890`
- 密码存储位置：memory（已验证 2026-06-13）
