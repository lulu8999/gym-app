# 通过 SSH 在 Windows 上导出 OpenSCAD STL 文件

## 前提条件
- Windows 已安装 OpenSCAD（`winget install OpenSCAD.OpenSCAD`）
- VPS 可通过 SSH 连接 Windows（端口 2222）
- .scad 文件已传到 Windows 桌面

## 步骤

### 1. 传文件到 Windows
```bash
sshpass -p '密码' scp -P 2222 -o StrictHostKeyChecking=no \
  /path/to/model.scad 用户@IP:"C:/Users/用户/Desktop/"
```

### 2. 写包装文件（分别导出各模块）
```scad
// export_front.scad
use <model.scad>
front_case();
```
```scad
// export_back.scad
use <model.scad>
back_cover();
```

### 3. 命令行导出
```bash
sshpass -p '密码' ssh -p 2222 用户@IP \
  '"C:\Program Files\OpenSCAD\openscad.com" -o "C:\Users\用户\Desktop\output.stl" "C:\Users\用户\Desktop\export_front.scad"'
```

### 4. 验证文件
```bash
sshpass -p '密码' ssh -p 2222 用户@IP \
  'powershell -Command "Get-ChildItem Desktop\*.stl | Select Name, Length"'
```

## 注意事项
- 用 `openscad.com` 而不是 `openscad.exe`（com 版支持命令行输出）
- `use <file.scad>` 只导入模块定义，不执行渲染
- 包装文件和主文件在同一目录时直接引用，否则用相对路径
- 渲染时间一般 1-5 秒，复杂模型可能更长
