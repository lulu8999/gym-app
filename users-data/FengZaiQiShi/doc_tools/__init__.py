#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中文文档生成工具包
支持 PDF、Excel、PPT 生成，确保中文、符号、数学符号不乱码
"""

from .fonts import FontManager, CHINESE_FONTS
from .pdf_generator import PDFGenerator, create_simple_pdf
from .excel_generator import ExcelGenerator, create_simple_excel
from .ppt_generator import PPTGenerator, create_simple_ppt
from .utils import (
    normalize_text,
    check_symbol_support,
    get_test_characters
)

__version__ = "1.0.0"
__all__ = [
    "FontManager",
    "CHINESE_FONTS",
    "PDFGenerator",
    "create_simple_pdf",
    "ExcelGenerator",
    "create_simple_excel",
    "PPTGenerator",
    "create_simple_ppt",
    "normalize_text",
    "check_symbol_support",
    "get_test_characters",
]
