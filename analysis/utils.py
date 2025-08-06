#!/usr/bin/env python3
"""
工具函数模块

提供程序分析所需的基础工具函数
"""

import re
from typing import Optional


def text(node) -> str:
    """获取tree-sitter节点的文本内容"""
    return node.text.decode('utf-8')


def normalize_whitespace(code: str) -> str:
    """标准化代码中的空白字符"""
    # 移除多余的空白字符，但保持基本的代码结构
    code = re.sub(r'\s+', ' ', code.strip())
    return code


def extract_function_name(function_text: str) -> Optional[str]:
    """从函数文本中提取函数名"""
    # 简单的函数名提取，支持基本的C/C++函数定义
    pattern = r'\b(\w+)\s*\('
    match = re.search(pattern, function_text)
    if match:
        return match.group(1)
    return None


def is_control_statement(node_type: str) -> bool:
    """判断节点类型是否为控制语句"""
    control_types = {
        'if_statement', 'while_statement', 'for_statement', 
        'switch_statement', 'do_statement', 'case_statement'
    }
    return node_type in control_types


def is_declaration_statement(node_type: str) -> bool:
    """判断节点类型是否为声明语句"""
    declaration_types = {
        'declaration', 'function_definition', 'parameter_declaration',
        'init_declarator'
    }
    return node_type in declaration_types


def format_line_info(line_number: int) -> str:
    """格式化行号信息"""
    return f"L{line_number}"


def clean_code_text(text: str) -> str:
    """清理代码文本，移除不必要的字符"""
    # 移除多余的分号和空白
    text = text.strip()
    if text.endswith(';'):
        text = text[:-1]
    return text
