#!/usr/bin/env python3
"""
工具函数模块

提供程序分析所需的基础工具函数
"""


def text(node) -> str:
    """获取tree-sitter节点的文本内容"""
    return node.text.decode('utf-8')
