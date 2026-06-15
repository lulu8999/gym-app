#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
通用工具函数
"""

import re
from typing import Dict, List


def normalize_text(text: str) -> str:
    """标准化文本，处理编码问题"""
    if text is None:
        return ""
    
    if isinstance(text, bytes):
        text = text.decode('utf-8', errors='ignore')
    
    # 移除控制字符（保留换行）
    text = ''.join(char for char in text if char == '\n' or ord(char) >= 32)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()


def check_symbol_support(text: str) -> Dict[str, List[str]]:
    """检查文本中各类字符的支持情况"""
    result = {
        'chinese': [], 'english': [], 'numbers': [],
        'punctuation': [], 'math': [], 'symbols': [],
        'arrows': [], 'currency': [], 'other': []
    }
    
    patterns = {
        'chinese': r'[\u4e00-\u9fff]',
        'english': r'[a-zA-Z]',
        'numbers': r'[0-9]',
        'punctuation': r'[\uff0c。！？；：（）【】《》「」‘’“”]',
        'math': r'[\u03b1-\u03c9∑∏√∞≤≥≠≈±×÷°′″℃Ω]',
        'symbols': r'[\u00a9\u00ae™°…●★☆○◆•]',
        'arrows': r'[\u2190-\u2199\u21d0-\u21d5]',
        'currency': r'[\uffe5\u00a5\$\u20ac\u00a3\u00a2]',
    }
    
    for char in text:
        for category, pattern in patterns.items():
            if re.match(pattern, char) and char not in result[category]:
                result[category].append(char)
                break
        else:
            if char not in result['other']:
                result['other'].append(char)
    
    return result


TEST_SYMBOLS = {
    'chinese': '中文测试：生理学考研资料 第四版 细胞的基本功能',
    'punctuation': '，。！？；：（）【】《》「」‘’“”〔〕〈〉～·：——／；【】',
    'math': 'αβγδεζηθικλμνξοπρστυφχψω∑∏√∞≤≥≠≈±×÷°′″℃Ω∫',
    'symbols': '©®™°…——●★☆○◆●•＊▲▼◀▶◐◑♠♣♥♦☐☑☒☎☏☺☻☹',
    'arrows': '←↑→↓↔↕⇐⇑⇒⇓⇔⇕↖↗↘↙',
    'currency': '￥¥$€£¢₽₩元角分毫',
}


def get_test_content() -> str:
    """获取完整测试内容"""
    lines = [f"[{k}] {v}" for k, v in TEST_SYMBOLS.items()]
    return '\n'.join(lines)


def truncate_text(text: str, max_length: int, suffix: str = '...') -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix
