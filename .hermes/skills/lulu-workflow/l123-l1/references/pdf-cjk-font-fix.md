# PDF CJK 字体兼容方案

## 问题

微信内置 PDF 查看器不支持 CID-keyed 中文字体嵌入。Python PDF 库（fpdf2、reportlab）使用 CID-keyed 方式嵌入 CJK 字体，导致微信打开 PDF 时中文显示为乱码。

## 解决方案：PNG 渲染 → PDF 封装

先生成 PNG 图片（中文已像素渲染），再嵌入到 PDF 中。不依赖字体嵌入，任何平台都能正常显示。

## 实现（fpdf2 + Pillow）

```python
from PIL import Image, ImageDraw, ImageFont
from fpdf import FPDF
import tempfile, os

# 1. 渲染文本到 PNG
def render_text_png(text, font_path, font_size=14, width=800):
    font = ImageFont.truetype(font_path, font_size)
    # 计算所需高度
    dummy = Image.new("RGB", (width, 1))
    draw = ImageDraw.Draw(dummy)
    lines = text.split("\n")
    line_height = font_size + 6
    height = len(lines) * line_height + 20
    
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)
    y = 10
    for line in lines:
        draw.text((10, y), line, fill="black", font=font)
        y += line_height
    path = tempfile.mktemp(suffix=".png")
    img.save(path)
    return path

# 2. 嵌入 PNG 到 PDF
pdf = FPDF()
pdf.add_page()
png_path = render_text_png("中文内容...", font_path)
pdf.image(png_path, x=10, y=10, w=pdf.w - 20)
pdf.output("/tmp/output.pdf")
```

## 字体路径

VPS 可用中文字体：`/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf`

## 工具封装

已创建 `/root/.hermes/hermes-agent/tools/pdf_generator.py` 工具，封装了 PNG→PDF 链路。

```python
pdf_generate(
    title="标题",
    subtitle="副标题",
    content=json.dumps([
        {"type":"h1","text":"一级标题"},
        {"type":"table","headers":["列1","列2"],"rows":[["a","b"]]},
        {"type":"text","text":"正文"},
        {"type":"list","items":["条目1","条目2"]},
    ]),
    output_path="/tmp/xxx.pdf"
)
```

## 教训

- ❌ fpdf2 `add_font()` + `set_font()` → CID 嵌入 → 微信乱码
- ❌ reportlab `registerFont()` + Paragraph → 同样 CID 嵌入乱码
- ✅ PIL 渲染 PNG → fpdf `image()` 嵌入 → 跨平台无乱码
- 图片也可以直接发（PNG 格式），比 PDF 更可靠
