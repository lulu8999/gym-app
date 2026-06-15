# OpenSCAD Windows 远程导出流程

## 安装（通过 winget）
```bash
ssh -p 2222 陆海天@100.80.251.96 'powershell -Command "winget install OpenSCAD.OpenSCAD --accept-package-agreements"'
```
安装路径：`C:\Program Files\OpenSCAD\openscad.com`

## 导出 STL
```bash
# 传文件到 Windows 桌面
scp -P 2222 file.scad 陆海天@100.80.251.96:"C:/Users/陆海天/Desktop/"

# 导出 STL（用 openscad.com 不是 openscad.exe）
ssh -p 2222 陆海天@100.80.251.96 '"C:\Program Files\OpenSCAD\openscad.com" -o "C:\Users\陆海天\Desktop\output.stl" "C:\Users\陆海天\Desktop\input.scad"'
```

## 分别导出不同部件
写包装 .scad 文件用 `use <主文件.scad>` + 调用指定模块：
```scad
// export_front.scad
use <esp32_case.scad>
front_case();
```

## 注意
- 用 `openscad.com`（命令行版），不是 `openscad.exe`（GUI版）
- 渲染时间通常 1-5 秒
- 输出会显示 Vertices/Facets 数量，可用于验证复杂度
