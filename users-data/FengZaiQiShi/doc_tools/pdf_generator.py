#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF 生成工具 - 支持中文、符号、数学符号
支持 fpdf2 和 reportlab 两种引擎
"""

import os
from io import BytesIO
from typing import List, Tuple, Optional, Union

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
    from reportlab.lib.units import cm, mm
    from reportlab.lib.colors import HexColor
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from .fonts import font_manager, TEST_STRINGS
except ImportError:
    from fonts import font_manager, TEST_STRINGS


class PDFGenerator:
    """PDF 生成器 - 统一封装"""
    
    def __init__(self, engine='fpdf'):
        """
        初始化PDF生成器
        
        参数:
            engine: 'fpdf' 或 'reportlab'
        """
        self.engine = engine
        self.font_path = font_manager.get_primary_font_path()
        self.font_name = font_manager.get_font_name()
        
        if engine == 'fpdf' and not FPDF_AVAILABLE:
            raise ImportError("fpdf2 未安装，请运行: pip install fpdf2")
        if engine == 'reportlab' and not REPORTLAB_AVAILABLE:
            raise ImportError("reportlab 未安装，请运行: pip install reportlab")
    
    def create_document(self, output_path: str, content: dict) -> str:
        """
        创建文档
        
        参数:
            output_path: 输出路径
            content: 文档内容字典
                {
                    'title': '标题',
                    'sections': [
                        {'heading': '章节标题', 'body': '正文内容'},
                    ]
                }
        """
        if self.engine == 'fpdf':
            return self._create_with_fpdf(output_path, content)
        else:
            return self._create_with_reportlab(output_path, content)
    
    def _create_with_fpdf(self, output_path: str, content: dict) -> str:
        """使用fpdf2创建"""
        pdf = FPDF()
        pdf.add_page()
        
        # 添加中文字体
        # 检查是否有子集字体（更小，适合fpdf2）
        subset_font = '/usr/share/fonts/chinese/NotoSans_subset.ttf'
        if os.path.exists(subset_font):
            pdf.add_font('Chinese', '', subset_font)
            pdf.add_font('Chinese', 'B', subset_font)
        elif self.font_path and self.font_path.endswith('.ttf'):
            pdf.add_font('Chinese', '', self.font_path)
            pdf.add_font('Chinese', 'B', self.font_path)
        else:
            # 使用内置字体
            pdf.set_font('Arial', '', 12)
        
        # 标题
        title = content.get('title', '')
        if title:
            pdf.set_font('Chinese', 'B', 18)
            pdf.cell(0, 15, title, ln=True, align='C')
            pdf.ln(5)
        
        # 内容章节
        for section in content.get('sections', []):
            heading = section.get('heading', '')
            body = section.get('body', '')
            
            if heading:
                pdf.set_font('Chinese', 'B', 14)
                pdf.cell(0, 10, heading, ln=True)
            
            if body:
                pdf.set_font('Chinese', '', 12)
                pdf.multi_cell(0, 8, body)
                pdf.ln(3)
        
        pdf.output(output_path)
        return output_path
    
    def _create_with_reportlab(self, output_path: str, content: dict) -> str:
        """使用reportlab创建"""
        # 注册字体
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
                c.setFont(font_name, 14)
                c.drawString(2*cm, y, heading)
                y -= 20
            
            if body:
                c.setFont(font_name, 12)
                # 简单文本换行
                text_obj = c.beginText(2*cm, y)
                text_obj.setFont(font_name, 12)
                
                max_width = width - 4*cm
                words = []
                for char in body:
                    test = ''.join(words) + char
                    if c.stringWidth(test, font_name, 12) < max_width:
                        words.append(char)
                    else:
                        text_obj.textLine(''.join(words))
                        words = [char]
                        y -= 15
                        if y < 2*cm:
                            c.drawText(text_obj)
                            c.showPage()
                            y = height - 2*cm
                            text_obj = c.beginText(2*cm, y)
                            text_obj.setFont(font_name, 12)
                
                if words:
                    text_obj.textLine(''.join(words))
                    y -= 15
                
                c.drawText(text_obj)
                y -= 10
        
        c.save()
        return output_path


def create_simple_pdf(output_path: str, title: str, body: str, 
                      engine: str = 'fpdf') -> str:
    """
    快速创建简单PDF
    
    参数:
        output_path: 输出路径
        title: 标题
        body: 正文
        engine: 'fpdf' 或 'reportlab'
    
    例子:
        create_simple_pdf('test.pdf', '成绩单', '张三: 85分\n李四: 92分')
    """
    generator = PDFGenerator(engine=engine)
    content = {
        'title': title,
        'sections': [{'body': body}]
    }
    return generator.create_document(output_path, content)


def create_test_pdf(output_path: str, engine: str = 'fpdf') -> str:
    """
    创建测试PDF，验证所有字符类型
    
    会生成一个包含所有测试字符的PDF
    """
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
            {'heading': '7. 混合内容测试', 'body': TEST_STRINGS['mixed']},
        ]
    }
    
    return generator.create_document(output_path, content)


if __name__ == "__main__":
    # 测试
    print("测试PDF生成...")
    
    # 测试fpdf
    try:
        path = create_test_pdf('/tmp/test_chinese_fpdf.pdf', engine='fpdf')
        print(f"✓ fpdf测试PDF已生成: {path}")
    except Exception as e:
        print(f"✗ fpdf测试失败: {e}")
    
    # 测试reportlab
    try:
        path = create_test_pdf('/tmp/test_chinese_rl.pdf', engine='reportlab')
        print(f"✓ reportlab测试PDF已生成: {path}")
    except Exception as e:
        print(f"✗ reportlab测试失败: {e}")
