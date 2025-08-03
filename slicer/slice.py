#!/usr/bin/env python3
"""
变量切片工具 - 对C/C++函数体进行变量相关代码切片
输入：函数体源码字符串、变量名
输出：与该变量相关的所有代码段（尽量保证语法正确）
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Node
from typing import List, Optional, Set
import logging
import re

logger = logging.getLogger(__name__)


class VariableSlicer:
    """变量切片器"""
    
    def __init__(self, language: str = "c"):
        """初始化切片器"""
        self.language = language
        if language == "cpp":
            self.lang = Language(tscpp.language(), "cpp")
        else:
            self.lang = Language(tsc.language(), "c")
        
        self.parser = Parser()
        self.parser.set_language(self.lang)
    
    def slice_function_by_variable(self, function_code: str, variable: str) -> str:
        """
        对函数体进行变量相关切片
        Args:
            function_code: 函数体源码字符串
            variable: 变量名
        Returns:
            与变量相关的代码片段字符串
        """
        tree = self.parser.parse(function_code.encode("utf-8"))
        root = tree.root_node
        
        # 收集相关节点的行号
        related_lines = set()
        
        # 递归查找变量相关的节点
        self._find_variable_related_nodes(root, variable, related_lines, function_code)
        
        # 还原相关代码片段
        code_lines = function_code.splitlines()
        output_lines = []
        
        for i, line in enumerate(code_lines):
            if i in related_lines:
                output_lines.append(line)
        
        return "\n".join(output_lines)
    
    def _find_variable_related_nodes(self, node: Node, variable: str, related_lines: Set[int], source_code: str):
        """递归查找与变量相关的AST节点"""
        
        # 检查当前节点是否包含目标变量
        if self._node_contains_variable(node, variable, source_code):
            # 添加当前节点的所有行
            related_lines.update(range(node.start_point[0], node.end_point[0] + 1))
        
        # 递归处理子节点
        for child in node.children:
            self._find_variable_related_nodes(child, variable, related_lines, source_code)
    
    def _node_contains_variable(self, node: Node, variable: str, source_code: str) -> bool:
        """检查节点是否包含目标变量"""
        
        # 变量声明节点
        if node.type == "declaration":
            return self._check_declaration_for_variable(node, variable, source_code)
        
        # 赋值表达式
        if node.type == "assignment_expression":
            return self._check_assignment_for_variable(node, variable, source_code)
        
        # 更新表达式 (++, --)
        if node.type == "update_expression":
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 返回语句
        if node.type == "return_statement":
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 控制流语句
        if node.type in ["if_statement", "while_statement", "for_statement", "switch_statement", "do_statement"]:
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 函数调用表达式
        if node.type == "call_expression":
            return self._check_identifier_in_node(node, variable, source_code)
        
        # 表达式语句
        if node.type == "expression_statement":
            return self._check_identifier_in_node(node, variable, source_code)
        
        return False
    
    def _check_declaration_for_variable(self, node: Node, variable: str, source_code: str) -> bool:
        """检查声明节点是否包含目标变量"""
        # 查找声明器中的标识符
        for child in node.children:
            if child.type == "init_declarator":
                declarator = child.child_by_field_name("declarator")
                if declarator and declarator.type == "identifier":
                    name = source_code[declarator.start_byte:declarator.end_byte]
                    if name == variable:
                        return True
            elif child.type == "identifier":
                name = source_code[child.start_byte:child.end_byte]
                if name == variable:
                    return True
        return False
    
    def _check_assignment_for_variable(self, node: Node, variable: str, source_code: str) -> bool:
        """检查赋值表达式是否包含目标变量"""
        # 检查左值和右值
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")
        
        # 检查左值
        if left and self._contains_identifier(left, variable, source_code):
            return True
        
        # 检查右值
        if right and self._contains_identifier(right, variable, source_code):
            return True
        
        return False
    
    def _check_identifier_in_node(self, node: Node, variable: str, source_code: str) -> bool:
        """检查节点中是否包含目标标识符"""
        return self._contains_identifier(node, variable, source_code)
    
    def _contains_identifier(self, node: Node, variable: str, source_code: str) -> bool:
        """递归检查节点及其子节点是否包含目标标识符"""
        if node.type == "identifier":
            name = source_code[node.start_byte:node.end_byte]
            if name == variable:
                return True
        
        # 递归检查子节点
        for child in node.children:
            if self._contains_identifier(child, variable, source_code):
                return True
        
        return False


def slice_function_by_variable(function_code: str, variable: str, language: str = "c") -> str:
    """
    对函数体进行变量相关切片（便捷函数）
    Args:
        function_code: 函数体源码字符串
        variable: 变量名
        language: "c" 或 "cpp"
    Returns:
        与变量相关的代码片段字符串
    """
    slicer = VariableSlicer(language)
    return slicer.slice_function_by_variable(function_code, variable)