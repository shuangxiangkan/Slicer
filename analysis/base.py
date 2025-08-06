#!/usr/bin/env python3
"""
基础分析器模块

提供程序分析的基础类和接口
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser
from typing import List


class BaseAnalyzer:
    """基础分析器"""
    
    def __init__(self, language: str = "c"):
        """
        初始化分析器
        Args:
            language: 编程语言 ("c" 或 "cpp")
        """
        if language == "c":
            self.language = Language(tsc.language(), "c")
        elif language == "cpp":
            self.language = Language(tscpp.language(), "cpp")
        else:
            raise ValueError(f"Unsupported language: {language}")
        
        self.parser = Parser()
        self.parser.set_language(self.language)
        self.language_name = language
    
    def parse_code(self, code: str):
        """解析代码"""
        tree = self.parser.parse(bytes(code, 'utf-8'))
        return tree.root_node
    
    def check_syntax(self, code: str) -> bool:
        """检查语法错误"""
        try:
            tree = self.parser.parse(bytes(code, 'utf-8'))
            return tree.root_node.has_error
        except:
            return True
    
    def find_functions(self, root_node):
        """查找所有函数定义"""
        functions = []
        
        def traverse(node):
            if node.type == 'function_definition':
                functions.append(node)
            for child in node.children:
                traverse(child)
        
        traverse(root_node)
        return functions
