# OpenSCAD Windows 远程导出 STL 流程

## 前提
- Win 笔记本 SSH：端口 2222，用户陆海天
- OpenSCAD 已通过 winget 安装：`C:\Program Files\OpenSCAD\openscad.com`

## 步骤

### 1. 安装 OpenSCAD（如未安装）
```bash
sshpass -p '密码' ssh -p 2222 陆海天@100.80.251.96 'powershell -Command "winget install OpenSCAD.OpenSCAD --accept-package-agreements --accept-source-agreements"'
```

### 2. 传输 .scad 文件到 Win 桌面
```bash
sshpass -p '密码' scp -P 2222 /path/to/file.scad 陆海天@100.80.251.96:"C:/Users/陆海天/Desktop/"
```

### 3. 创建分部件导出文件
外壳有多个模块（front_case、back_cover），需要分别导出：
- `export_front.scad`：`use <主文件.scad>` + `front_case();`
- `export_back.scad`：`use <主文件.scad>` + `back_cover();`

### 4. 命令行导出 STL
```bash
sshpass -p '密码' ssh -p 2222 陆海天@100.80.251.96 '"C:\Program Files\OpenSCAD\openscad.com" -o "C:\Users\陆海天\Desktop\output.stl" "C:\Users\陆海天\Desktop\export_xxx.scad"'
```

### 5. 确认文件
```bash
sshpass -p '密码' ssh -p 2222 陆海天@100.80.251.96 'powershell -Command "Get-ChildItem \"C:\Users\陆海天\Desktop\*.stl\" | Select Name, Length"'
```

## 注意事项
- winget 安装后 PATH 不会立即更新，需用完整路径 `C:\Program Files\OpenSCAD\openscad.com`
- 导出时间取决于模型复杂度，简单模型几秒，复杂模型可能需要几分钟
- STL 文件可直接发给 3D 打印商家
- 源码 .scad 也要保留，方便后续改参数重新导出
