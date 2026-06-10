#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字体配置中心 - 统一管理中文字体
"""

import os
from pathlib import Path

# 中文字体配置
CHINESE_FONTS = {
    # 系统已安装的字体
    'noto_sans_sc': {
        'name': 'NotoSansCJKsc-Regular',
        'display_name': 'Noto Sans CJK SC',
        'path': '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.ttf',
        'otf_path': '/usr/share/fonts/chinese/NotoSansCJKsc-Regular.otf',
        'supports': ['简体', '繁体', '日文', '韩文', '基本符号', '数学符号'],
    },
    # 常用后备字体（用于兼容性）
    'microsoft_yahei': {
        'name': 'MicrosoftYaHei',
        'display_name': 'Microsoft YaHei',
        'path': '/usr/share/fonts/truetype/msyhl.ttc',
        'supports': ['简体', '繁体', '基本符号'],
    },
    'simhei': {
        'name': 'SimHei',
        'display_name': 'SimHei',
        'path': '/usr/share/fonts/truetype/simhei.ttf',
        'supports': ['简体', '繁体'],
    },
    'simsun': {
        'name': 'SimSun',
        'display_name': 'SimSun',
        'path': '/usr/share/fonts/truetype/simsun.ttc',
        'supports': ['简体', '繁体'],
    },
    'arial_unicode': {
        'name': 'ArialUnicodeMS',
        'display_name': 'Arial Unicode MS',
        'path': '/usr/share/fonts/truetype/arialuni.ttf',
        'supports': ['多国语言', '符号', '数学符号'],
    },
}

# 字符集定义
CHARACTER_SETS = {
    'chinese_common': '一二三四五六七八九十个人大小天地上下左右前后中外内外正反长短高低小多少好坏轻重急缓卷快慢新旧真假对错',
    'chinese_full': '',  # 动态加载
    'punctuation': '，。！？；：（）【】《》「」『』‘’“”〔〕〖〗〈〉［］｛｝｜～·：——／；【】',
    'math': 'αβγδεζηθικλμνξοπρστυφχψω∑∏√∞≤≥≠≈±×÷°′″℃Ω∫∂∇∈∉∋∝∝∥∧∨¬∩∪⊂⊃⊆⊇±×÷',
    'symbols': '©®™°…——●★☆○◆●•＊▲▼◀▶◐◑♠♣♥♦☐☑☒☎☏☺☻☹',
    'arrows': '←↑→↓↔↕⇐⇑⇒⇓⇔⇕⇦⇧⇨⇩⇄⇅⇆⇇⇈⇉↖↗↘↙',
    'currency': '￥¥$€£¢₽₩元角分毫里厘拾',
    'numbers': '0123456789①②③④⑤⑥⑦⑧⑨⑩⑴⑵⑶⑷⑸⑹㉑㉒㉓㉔㉕㉖㉗㉘㉙㉚㉛㉜㉝㉞㉟',
    'english': 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
    'special': '¡¿§¶·¸¹º¼½¾¿×÷¤¦¨¯´¸¹º¼½¾¿ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖ×ØÙÚÛÜÝÞß',
}

# 完整测试字符串
TEST_STRINGS = {
    'chinese': '中文测试：生理学考研资料 第四版 细胞的基本功能',
    'punctuation': '标点测试：，。！？；：（）【】《》「」‘’“”〔〕〈〉～·：——／',
    'math': '数学符号：αβγδ∑∏√∞≤≥≠≈±×÷°′″℃Ω∫',
    'symbols': '特殊符号：©®™°…●★☆○◆•＊▲▼▶◀',
    'arrows': '箭头符号：←↑→↓↔↕⇐⇑⇒⇓⇔⇕↖↗↘↙',
    'currency': '货币符号：￥¥$€£¢元角分毫',
    'mixed': '混合内容：生理学αβγ标点，。符号©®™箭头→金额￥100.50元',
}


class FontManager:
    """字体管理器 - 自动检测并选择最佳字体"""
    
    def __init__(self):
        self.available_fonts = self._detect_fonts()
        self.primary_font = self._select_primary_font()
        
    def _detect_fonts(self):
        """检测系统中可用的字体"""
        available = {}
        for font_key, font_info in CHINESE_FONTS.items():
            # 检查TTF路径
            if 'path' in font_info and os.path.exists(font_info['path']):
                available[font_key] = font_info
            # 检查OTF路径
            elif 'otf_path' in font_info and os.path.exists(font_info['otf_path']):
                available[font_key] = font_info
        return available
    
    def _select_primary_font(self):
        """选择主要字体（优先顺序）"""
        priority = ['noto_sans_sc', 'microsoft_yahei', 'simhei', 'simsun', 'arial_unicode']
        for font_name in priority:
            if font_name in self.available_fonts:
                return self.available_fonts[font_name]
        return None
    
    def get_font_path(self, font_name=None):
        """获取字体路径"""
        if font_name is None:
            font_name = 'noto_sans_sc'
        
        if font_name in self.available_fonts:
            info = self.available_fonts[font_name]
            if 'path' in info and os.path.exists(info['path']):
                return info['path']
            if 'otf_path' in info and os.path.exists(info['otf_path']):
                return info['otf_path']
        return None
    
    def get_primary_font_path(self):
        """获取主要字体路径"""
        if self.primary_font:
            return self.get_font_path(self.primary_font['name'].replace('CJKsc-Regular', '').lower())
        return None
    
    def get_font_name(self, font_key='noto_sans_sc'):
        """获取字体显示名称"""
        if font_key in self.available_fonts:
            return self.available_fonts[font_key]['display_name']
        return 'Arial'
    
    def list_available_fonts(self):
        """列出所有可用字体"""
        return list(self.available_fonts.keys())
    
    def check_font_available(self, font_key):
        """检查字体是否可用"""
        return font_key in self.available_fonts


# 全局字体管理器实例
font_manager = FontManager()


if __name__ == "__main__":
    # 测试字体检测
    print("已检测到的字体:")
    for name in font_manager.list_available_fonts():
        print(f"  - {name}: {font_manager.get_font_path(name)}")
    print(f"\n主要字体: {font_manager.primary_font}")
