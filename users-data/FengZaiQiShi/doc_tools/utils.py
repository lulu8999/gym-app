#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数
"""

import re
from typing import Dict, List


def normalize_text(text: str) -> str:
    """
    标准化文本，处理可能的编码问题
    
    参数:
        text: 输入文本
    返回:
        标准化后的文本
    """
    if text is None:
        return ""
    
    # 确保是字符串类型
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='ignore')
    
    # 移除控制字符（保留换行）
    text = ''.join(char for char in text if char == '\n' or ord(char) >= 32)
    
    # 统一换行符
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # 移除多余空白
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()


def check_symbol_support(text: str) -> Dict[str, List[str]]:
    """
    检查文本中各类字符的支持情况
    
    参数:
        text: 要检查的文本
    返回:
        字典，分类列出各类字符
    """
    result = {
        'chinese': [],
        'english': [],
        'numbers': [],
        'punctuation': [],
        'math': [],
        'symbols': [],
        'arrows': [],
        'currency': [],
        'other': []
    }
    
    # 字符集定义
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    english_pattern = re.compile(r'[a-zA-Z]')
    number_pattern = re.compile(r'[0-9]')
    punctuation_pattern = re.compile(r'[\uff0c。！？；：（）【】《》「」『』‘’“”〔〕〈〉\uff3b\uff3d\uff5b\uff5d\uff5c\uff5e\u00b7\uff1a\u2014\u2014\uff0f\uff1b\u3010\u3011]')
    math_pattern = re.compile(r'[\u03b1-\u03c9\u2211\u220f\u221a\u221e\u2264\u2265\u2260\u2248\u00b1\u00d7\u00f7\u00b0\u2032\u2033\u2103\u2126\u222b\u2202\u2207\u2208\u2209\u220b\u221d\u2225\u2227\u2228\u00ac\u2229\u222a\u2282\u2283\u2286\u2287]')
    symbol_pattern = re.compile(r'[\u00a9\u00ae\u2122\u00b0\u2026\u2014\u2014\u25cf\u2605\u2606\u25cb\u25c6\u25cf\u2022\uff0a\u25b2\u25bc\u25c0\u25b6\u25d0\u25d1\u2660\u2663\u2665\u2666\u2610\u2611\u2612\u260e\u260f\u263a\u263b\u2639]')
    arrow_pattern = re.compile(r'[\u2190-\u2199\u21d0-\u21d5\u21e6-\u21e9\u21c4-\u21c9]')
    currency_pattern = re.compile(r'[\uffe5\u00a5\$\u20ac\u00a3\u00a2\u20bd\u20a9]')
    
    for char in text:
        if chinese_pattern.match(char):
            if char not in result['chinese']:
                result['chinese'].append(char)
        elif english_pattern.match(char):
            if char not in result['english']:
                result['english'].append(char)
        elif number_pattern.match(char):
            if char not in result['numbers']:
                result['numbers'].append(char)
        elif punctuation_pattern.match(char):
            if char not in result['punctuation']:
                result['punctuation'].append(char)
        elif math_pattern.match(char):
            if char not in result['math']:
                result['math'].append(char)
        elif symbol_pattern.match(char):
            if char not in result['symbols']:
                result['symbols'].append(char)
        elif arrow_pattern.match(char):
            if char not in result['arrows']:
                result['arrows'].append(char)
        elif currency_pattern.match(char):
            if char not in result['currency']:
                result['currency'].append(char)
        else:
            if char not in result['other']:
                result['other'].append(char)
    
    return result


def get_test_characters() -> Dict[str, str]:
    """
    获取完整的测试字符集
    
    返回:
        包含各类测试字符的字典
    """
    return {
        'chinese': '中文测试：生理学考研资料 第四版 细胞的基本功能',
        'punctuation': '，。！？；：（）【】《》「」‘’“”〔〕〈〉～·：——／；【】',
        'math': 'αβγδεζηθικλμνξοπρστυφχψω∑∏√∞≤≥≠≈±×÷°′″℃Ω∫',
        'symbols': '©®™°…——●★☆○◆●•＊▲▼◀▶◐◑♠♣♥♦☐☑☒☎☏☺☻☹',
        'arrows': '←↑→↓↔↕⇐⇑⇒⇓⇔⇕↖↗↘↙',
        'currency': '￥¥$€£¢₽₩元角分毫',
        'english': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
        'numbers': '0123456789①②③④⑤⑥⑦⑧⑨⑩',
        'mixed': '生理学αβγ标点，。符号©®™箭头→金额￥100.50元',
    }


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """
    截断文本到指定长度
    
    参数:
        text: 原始文本
        max_length: 最大长度
        suffix: 截断后缀
    返回:
        截断后的文本
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def count_chars(text: str) -> Dict[str, int]:
    """
    统计文本中各类字符数量
    
    参数:
        text: 要统计的文本
    返回:
        各类字符数量字典
    """
    result = check_symbol_support(text)
    return {k: len(v) for k, v in result.items()}


if __name__ == "__main__":
    # 测试
    test_text = "生理学αβγ标点，。符号©®™箭头→金额￥100.50元ABC"
    
    print("测试文本:", test_text)
    print("\n字符分类:")
    result = check_symbol_support(test_text)
    for category, chars in result.items():
        if chars:
            print(f"  {category}: {''.join(chars[:20])}{'...' if len(chars) > 20 else ''}")
    
    print("\n字符统计:")
    counts = count_chars(test_text)
    for category, count in counts.items():
        if count > 0:
            print(f"  {category}: {count}")
