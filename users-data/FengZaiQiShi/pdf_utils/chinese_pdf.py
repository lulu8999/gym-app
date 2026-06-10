#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文PDF生成工具 - 已配置好字体，直接使用不会乱码
"""

import os
from fpdf import FPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm

# ============== 字体配置 ==============
# 系统中已安装的中文字体路径
FONT_PATHS = {
    'noto_sans': '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf',
    'noto_sans_otf': '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf',
}

# 注册reportlab字体
def register_chinese_fonts():
    """注册中文字体到reportlab"""
    try:
        if os.path.exists(FONT_PATHS['noto_sans']):
            pdfmetrics.registerFont(TTFont('NotoSansSC', FONT_PATHS['noto_sans']))
        elif os.path.exists(FONT_PATHS['noto_sans_otf']):
            pdfmetrics.registerFont(TTFont('NotoSansSC', FONT_PATHS['noto_sans_otf']))
    except Exception as e:
        print(f"字体注册警告: {e}")

# ============== FPDF2 类 (推荐用于简单PDF) ==============
class ChinesePDF(FPDF):
    """自带中文字体支持的FPDF类"""
    
    def __init__(self):
        super().__init__()
        # 添加中文字体
        if os.path.exists(FONT_PATHS['noto_sans']):
            self.add_font('NotoSansSC', '', FONT_PATHS['noto_sans'], uni=True)
            self.add_font('NotoSansSC', 'B', FONT_PATHS['noto_sans'], uni=True)
        elif os.path.exists(FONT_PATHS['noto_sans_otf']):
            self.add_font('NotoSansSC', '', FONT_PATHS['noto_sans_otf'], uni=True)
            self.add_font('NotoSansSC', 'B', FONT_PATHS['noto_sans_otf'], uni=True)
    
    def header(self):
        """页眉"""
        self.set_font('NotoSansSC', '', 10)
        self.cell(0, 10, '', 0, 1, 'C')
    
    def footer(self):
        """页脚"""
        self.set_y(-15)
        self.set_font('NotoSansSC', '', 10)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')
    
    def chapter_title(self, title):
        """章节标题"""
        self.set_font('NotoSansSC', 'B', 16)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)
    
    def chapter_body(self, body):
        """正文内容"""
        self.set_font('NotoSansSC', '', 12)
        self.multi_cell(0, 8, body)
        self.ln()


# ============== 便捷函数 ==============

def create_simple_pdf(output_path, title="文档标题", content="", font_size=12):
    """
    快速创建简单PDF - 不会乱码
    
    参数:
        output_path: 输出文件路径
        title: 文档标题
        content: 正文内容
        font_size: 正文字号
    """
    pdf = ChinesePDF()
    pdf.add_page()
    
    # 标题
    pdf.set_font('NotoSansSC', 'B', 18)
    pdf.cell(0, 15, title, 0, 1, 'C')
    pdf.ln(5)
    
    # 内容
    pdf.set_font('NotoSansSC', '', font_size)
    pdf.multi_cell(0, 8, content)
    
    pdf.output(output_path)
    print(f"PDF已生成: {output_path}")
    return output_path


def create_reportlab_pdf(output_path, title="文档标题", paragraphs=None):
    """
    使用ReportLab创建PDF - 适合复杂排版
    
    参数:
        output_path: 输出文件路径
        title: 文档标题
        paragraphs: 段落列表，每个元素是(文本, 字号, 是否加粗)
    """
    register_chinese_fonts()
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    y = height - 2*cm
    
    # 标题
    c.setFont('NotoSansSC', 18)
    c.drawCentredString(width/2, y, title)
    y -= 30
    
    # 段落
    if paragraphs:
        for text, size, bold in paragraphs:
            font_name = 'NotoSansSC'
            c.setFont(font_name, size)
            
            # 简单的文本换行处理
            lines = []
            current_line = ""
            for char in text:
                test_line = current_line + char
                if c.stringWidth(test_line, font_name, size) < width - 4*cm:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = char
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                if y < 2*cm:  # 需要新页
                    c.showPage()
                    y = height - 2*cm
                    c.setFont(font_name, size)
                c.drawString(2*cm, y, line)
                y -= size + 4
            y -= 10  # 段落间距
    
    c.save()
    print(f"PDF已生成: {output_path}")
    return output_path


# ============== 示例/测试 ==============
if __name__ == "__main__":
    # 测试生成PDF
    test_content = """
这是一段测试内容，包含中文字符。

生理学考研资料 - 第4版

细胞的基本功能
神经调节、体液调节和自身调节是机体对各种功能活动进行调节的三种基本方式。

测试各种字符：
- 英文: Hello World
- 数字: 1234567890
- 符号: !@#$%^&*()
- 中文标点：，。！？；：""''（）【】《》

如果这段文字显示正常，说明字体配置成功！
    """
    
    # 测试FPDF
    create_simple_pdf(
        "/tmp/test_chinese_fpdf.pdf",
        title="中文PDF测试",
        content=test_content
    )
    
    # 测试ReportLab
    create_reportlab_pdf(
        "/tmp/test_chinese_rl.pdf",
        title="中文PDF测试 (ReportLab)",
        paragraphs=[
            ("生理学考研资料 - 第4版", 16, True),
            ("", 12, False),
            ("细胞的基本功能：神经调节、体液调节和自身调节是机体对各种功能活动进行调节的三种基本方式。", 12, False),
            ("", 12, False),
            ("测试完成！字体配置正常。", 12, False),
        ]
    )
    
    print("\n测试PDF已生成:")
    print("  - /tmp/test_chinese_fpdf.pdf (FPDF版本)")
    print("  - /tmp/test_chinese_rl.pdf (ReportLab版本)")
