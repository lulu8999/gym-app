# 中文文档生成工具包 (doc_tools)

完整的中文PDF/Excel/PPT生成解决方案，解决乱码问题。

## 安装依赖

```bash
python3 -m pip install fpdf2 reportlab openpyxl xlsxwriter python-pptx pymupdf
```

## 目录结构

```
doc_tools/
├── __init__.py
├── fonts.py              # 字体配置中心
├── pdf_generator.py      # PDF生成
├── excel_generator.py    # Excel生成
├── ppt_generator.py      # PPT生成
├── utils.py              # 通用工具
└── examples/
    ├── demo_pdf.py
    ├── demo_excel.py
    └── demo_ppt.py
```

## fonts.py - 字体配置

```python
#!/usr/bin/env python3
"""字体配置中心 - 自动检测和选择中文字体"""

import os

class FontManager:
    """管理中文字体配置"""
    
    # 系统字体路径
    FONT_PATHS = {
        'noto_sans_subset': '/usr/share/fonts/chinese/NotoSans_subset.ttf',
        'noto_sans': '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf',
        'noto_sans_otf': '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf',
    }
    
    # 字体显示名称
    FONT_NAMES = {
        'noto_sans': 'Noto Sans CJK SC',
        'microsoft_yahei': 'Microsoft YaHei',
        'simhei': 'SimHei',
        'simsun': 'SimSun',
    }
    
    def __init__(self):
        self.available_fonts = self._detect_fonts()
    
    def _detect_fonts(self):
        """检测系统中可用的中文字体"""
        available = {}
        for name, path in self.FONT_PATHS.items():
            if os.path.exists(path):
                available[name] = path
        return available
    
    def get_primary_font_path(self):
        """获取主要字体路径（优先使用子集字体）"""
        # 优先使用子集字体（fpdf2兼容性更好）
        if 'noto_sans_subset' in self.available_fonts:
            return self.available_fonts['noto_sans_subset']
        elif 'noto_sans' in self.available_fonts:
            return self.available_fonts['noto_sans']
        elif 'noto_sans_otf' in self.available_fonts:
            return self.available_fonts['noto_sans_otf']
        return None
    
    def get_font_name(self):
        """获取字体显示名称"""
        return self.FONT_NAMES.get('noto_sans', 'Arial Unicode MS')

# 全局字体管理器实例
font_manager = FontManager()

# 测试字符集
TEST_STRINGS = {
    'chinese': '中文测试：生理学考研资料 第四版 细胞的基本功能',
    'punctuation': '，。！？；：（）【】《》「」‘’“”〔〕〈〉～·：——／；【】',
    'math': 'αβγδεζηθικλμνξοπρστυφχψω∑∏√∞≤≥≠≈±×÷°′″℃Ω∫',
    'symbols': '©®™°…——●★☆○◆●•＊▲▼◀▶◐◑♠♣♥♦☐☑☒☎☏☺☻☹',
    'arrows': '←↑→↓↔↕⇐⇑⇒⇓⇔⇕↖↗↘↙',
    'currency': '￥¥$€£¢₽₩元角分毫',
    'mixed': '生理学αβγ标点，。符号©®™箭头→金额￥100.50元',
}

if __name__ == "__main__":
    print("已检测到的字体:")
    for name, path in font_manager.available_fonts.items():
        print(f"  - {name}: {path}")
    print(f"\n主要字体: {font_manager.get_primary_font_path()}")
```

## pdf_generator.py - PDF生成

```python
#!/usr/bin/env python3
"""PDF 生成工具 - 支持中文、符号、数学符号"""

import os
from typing import List, Optional

try:
    from fpdf import FPDF
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from fonts import font_manager, TEST_STRINGS
except ImportError:
    from doc_tools.fonts import font_manager, TEST_STRINGS


class PDFGenerator:
    """PDF 生成器"""
    
    def __init__(self, engine='reportlab'):
        self.engine = engine
        self.font_path = font_manager.get_primary_font_path()
        self.font_name = font_manager.get_font_name()
        
        if engine == 'fpdf' and not FPDF_AVAILABLE:
            raise ImportError("fpdf2 未安装")
        if engine == 'reportlab' and not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 未安装")
    
    def create_document(self, output_path: str, content: dict) -> str:
        """
        创建文档
        参数:
            output_path: 输出路径
            content: {'title': '标题', 'sections': [{'heading': '', 'body': ''}]}
        """
        if self.engine == 'fpdf':
            return self._create_with_fpdf(output_path, content)
        else:
            return self._create_with_reportlab(output_path, content)
    
    def _create_with_reportlab(self, output_path: str, content: dict) -> str:
        """使用reportlab创建（推荐）"""
        font_name = 'ChineseFont'
        if self.font_path:
            try:
                pdfmetrics.registerFont(TTFont(font_name, self.font_path))
            except:
                font_name = 'Helvetica'
        else:
            font_name = 'Helvetica'
        
        c = canvas.Canvas(output_path, pagesize=A4)
        width, height = A4
        y = height - 2*cm
        
        # 标题
        title = content.get('title', '')
        if title:
            c.setFont(font_name, 18)
            c.drawCentredString(width/2, y, title)
            y -= 25
        
        # 内容
        for section in content.get('sections', []):
            heading = section.get('heading', '')
            body = section.get('body', '')
            
            if heading:
                if y < 3*cm:
                    c.showPage()
                    y = height - 2*cm
                c.setFont(font_name, 14)
                c.drawString(2*cm, y, heading)
                y -= 20
            
            if body:
                c.setFont(font_name, 12)
                text_obj = c.beginText(2*cm, y)
                text_obj.setFont(font_name, 12)
                
                max_width = width - 4*cm
                for char in body:
                    test_width = c.stringWidth(text_obj.getText() + char, font_name, 12)
                    if test_width < max_width:
                        text_obj.textOut(char)
                    else:
                        c.drawText(text_obj)
                        y -= 15
                        if y < 2*cm:
                            c.showPage()
                            y = height - 2*cm
                        text_obj = c.beginText(2*cm, y)
                        text_obj.setFont(font_name, 12)
                        text_obj.textOut(char)
                
                c.drawText(text_obj)
                y -= 15
        
        c.save()
        return output_path


def create_simple_pdf(output_path: str, title: str, body: str, engine='reportlab') -> str:
    """快速创建简单PDF"""
    generator = PDFGenerator(engine=engine)
    content = {'title': title, 'sections': [{'body': body}]}
    return generator.create_document(output_path, content)


def create_test_pdf(output_path: str, engine='reportlab') -> str:
    """创建测试PDF，验证所有字符类型"""
    generator = PDFGenerator(engine=engine)
    content = {
        'title': '中文PDF测试文档',
        'sections': [
            {'heading': '1. 中文内容测试', 'body': TEST_STRINGS['chinese']},
            {'heading': '2. 标点符号测试', 'body': TEST_STRINGS['punctuation']},
            {'heading': '3. 数学符号测试', 'body': TEST_STRINGS['math']},
            {'heading': '4. 特殊符号测试', 'body': TEST_STRINGS['symbols']},
            {'heading': '5. 箭头符号测试', 'body': TEST_STRINGS['arrows']},
            {'heading': '6. 货币符号测试', 'body': TEST_STRINGS['currency']},
        ]
    }
    return generator.create_document(output_path, content)
```

## 快速使用

```python
from doc_tools import create_simple_pdf, create_test_pdf

# 快速生成
create_simple_pdf('output.pdf', '成绩单', '张三: 85分\n李四: 92分')

# 测试所有字符
create_test_pdf('test.pdf')
```

## 字符覆盖范围

| 类型 | 内容 |
|------|-------|
| 中文 | 简体/繁体、生偏字 |
| 标点 | ，。！？；：（）【】《》「」""'' |
| 数学 | αβγδ∑√∞≤≥≠≈±×÷°′″℃Ω |
| 符号 | ©®™°…——●★☆○◆• |
| 箭头 | ←↑→↓↔↕⇐⇑⇒⇓ |
| 货币 | ￥¥$€£¢ |

## 常见问题解决

### 1. fpdf2 报错 "Unsupported font file extension"

**原因**: fpdf2 v2.5.1+ 对字体文件大小有限制，完整的NotoSansCJK字体(16MB)过大。

**解决**: 使用子集字体(200KB)或切换到reportlab引擎。

```python
# 使用子集字体
subset_font = '/usr/share/fonts/chinese/NotoSans_subset.ttf'
pdf.add_font('Chinese', '', subset_font)

# 或切换引擎
generator = PDFGenerator(engine='reportlab')  # 更稳定
```

### 2. 中文显示方框或乱码

**原因**: 字体未正确加载或编码问题。

**解决**: 
1. 确保系统已安装中文字体
2. 使用`doc_tools`工具包（已处理好字体回退）
3. 验证字体路径是否存在

```python
from doc_tools.fonts import font_manager
print(font_manager.get_primary_font_path())  # 应返回有效路径
```

### 3. 特殊符号显示不正常

**原因**: 字体不支持该符号。

**解决**: Noto Sans CJK SC 字体支持大部分常用符号，如需更多符号可考虑使用更完整的字体文件。
