#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF生成器 - 支持中文和特殊符号
复制此文件到你的项目中使用
"""

from fpdf import FPDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os

# 导入字体配置
from fonts import get_available_font_path, get_font_name

class ChinesePDF(FPDF):
    """自带中文字体支持的PDF类
    
    使用示例:
        pdf = ChinesePDF()
        pdf.add_page()
        pdf.chapter_title("章节标题")
        pdf.chapter_body("正文内容...")
        pdf.output("output.pdf")
    """
    
    def __init__(self, font_path=None):
        super().__init__()
        # 自动检测字体路径
        if font_path is None:
            font_path = get_available_font_path()
        
        if font_path and os.path.exists(font_path):
            self.add_font('Chinese', '', font_path, uni=True)
            self.add_font('Chinese', 'B', font_path, uni=True)
        else:
            print("警告: 未找到中文字体，PDF可能显示乱码")
        
        self.set_auto_page_break(auto=True, margin=15)
    
    def header(self):
        """页眉"""
        if self.page_no() == 1:
            return
        self.set_font('Chinese', '', 10)
        self.cell(0, 10, '', 0, 1, 'C')
    
    def footer(self):
        """页脚"""
        self.set_y(-15)
        self.set_font('Chinese', '', 10)
        self.cell(0, 10, f'第 {self.page_no()} 页', 0, 0, 'C')
    
    def chapter_title(self, title):
        """章节标题"""
        self.set_font('Chinese', 'B', 16)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(5)
    
    def chapter_body(self, body):
        """正文内容"""
        self.set_font('Chinese', '', 12)
        self.multi_cell(0, 8, body)
        self.ln()

def create_pdf_simple(output_path, title, content, font_path=None):
    """
    快速创建简单PDF
    
    参数:
        output_path: 输出文件路径
        title: 文档标题
        content: 正文内容
        font_path: 字体路径（可选，默认自动检测）
    
    返回:
        output_path: 输出文件路径
    """
    pdf = ChinesePDF(font_path)
    pdf.add_page()
    
    # 标题
    pdf.set_font('Chinese', 'B', 18)
    pdf.cell(0, 15, title, 0, 1, 'C')
    pdf.ln(5)
    
    # 内容
    pdf.set_font('Chinese', '', 12)
    pdf.multi_cell(0, 8, content)
    
    pdf.output(output_path)
    print(f"PDF已生成: {output_path}")
    return output_path

def create_pdf_reportlab(output_path, title, paragraphs, font_path=None):
    """
    使用ReportLab创建PDF（适合复杂布局）
    
    参数:
        output_path: 输出文件路径
        title: 文档标题
        paragraphs: 段落列表，每个元素是(文本, 字号, 是否加粗)
        font_path: 字体路径
    """
    if font_path is None:
        font_path = get_available_font_path()
    
    # 注册字体
    if font_path and os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Chinese', font_path))
    else:
        print("警告: 未找到中文字体")
    
    c = canvas.Canvas(output_path, pagesize=A4)
    width, height = A4
    
    y = height - 2 * 28.35  # 2cm从顶部开始
    
    # 标题
    c.setFont('Chinese', 18)
    c.drawCentredString(width/2, y, title)
    y -= 30
    
    # 段落
    if paragraphs:
        for text, size, bold in paragraphs:
            font_name = 'Chinese'
            c.setFont(font_name, size)
            
            # 简单的文本换行处理
            max_width = width - 4 * 28.35  # 左右各2cm边距
            lines = []
            current_line = ""
            for char in text:
                test_line = current_line + char
                if c.stringWidth(test_line, font_name, size) < max_width:
                    current_line = test_line
                else:
                    lines.append(current_line)
                    current_line = char
            if current_line:
                lines.append(current_line)
            
            for line in lines:
                if y < 2 * 28.35:  # 底部2cm留白
                    c.showPage()
                    y = height - 2 * 28.35
                    c.setFont(font_name, size)
                c.drawString(2 * 28.35, y, line)
                y -= size + 4
            y -= 10  # 段落间距
    
    c.save()
    print(f"PDF已生成: {output_path}")
    return output_path

if __name__ == "__main__":
    from fonts import get_test_content
    
    # 测试生成PDF
    test_content = get_test_content()
    create_pdf_simple("/tmp/test_chinese.pdf", "中文PDF测试", test_content)
