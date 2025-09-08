#!/usr/bin/env python3
"""
函数使用查找器 - 在代码仓库中查找函数的使用情况
"""

import logging
from typing import Dict, List, Optional
from .file_finder import FileFinder
from .config_parser import ConfigParser
from .utils import get_tree_sitter_manager

class FunctionUsageFinder:
    """
    函数使用查找器
    
    提供函数使用查找功能
    """
    
    def __init__(self, config_parser: ConfigParser = None):
        """
        初始化函数使用查找器
        
        Args:
            config_parser: 配置解析器实例
        """
        self.config_parser = config_parser
        self.file_finder = FileFinder()
        self.logger = logging.getLogger(__name__)
        
        # 使用统一的tree-sitter管理器
        self.tree_sitter_manager = get_tree_sitter_manager()
    
    def find_usage_in_repo(self, function_name: str, repo_root: str, analyzed_functions: List = None) -> Dict[str, List[Dict]]:
        """
        在仓库中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            repo_root: 仓库根目录
            analyzed_functions: 已分析的函数信息列表
        
        Returns:
            Dict[str, List[Dict]]: 文件路径 -> 调用者信息列表的映射
            调用者信息格式: {'name': str, 'start_line': int, 'end_line': int, 'code': str}
        """
        if not self.tree_sitter_manager.parser_available:
            self.logger.warning("tree-sitter解析器未初始化，无法解析文件")
            return {}
        
        # 获取所有C/C++文件
        all_files = self.file_finder.find_files(repo_root, recursive=True)
        
        # 在所有文件中查找函数使用
        return self._find_usage_in_files(function_name, all_files)
    
    def _find_usage_in_files(self, function_name: str, file_paths: List[str]) -> Dict[str, List[Dict]]:
        """
        在指定文件列表中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            file_paths: 文件路径列表
        
        Returns:
            Dict[str, List[Dict]]: 文件路径 -> 调用者信息列表的映射
            调用者信息格式: {'name': str, 'start_line': int, 'end_line': int, 'code': str}
        """
        callers_by_file = {}
        
        for file_path in file_paths:
            try:
                callers = self._find_callers_in_file(file_path, function_name)
                if callers:
                    callers_by_file[file_path] = callers
            except Exception as e:
                self.logger.warning(f"解析文件 {file_path} 时出错: {e}")
        
        return callers_by_file
    
    def _find_callers_in_file(self, file_path: str, function_name: str) -> List[Dict]:
        """
        在单个文件中查找函数调用者
        
        Args:
            file_path: 文件路径
            function_name: 要查找的函数名
        
        Returns:
            List[Dict]: 调用者信息列表
            调用者信息格式: {'name': str, 'start_line': int, 'end_line': int, 'code': str}
        """
        callers = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            # 使用tree-sitter管理器解析源代码
            tree = self.tree_sitter_manager.parse_content(source_code, file_path)
            if not tree:
                self.logger.warning(f"无法解析文件: {file_path}")
                return callers
            
            # 查找函数定义和函数调用
            function_definitions = self._find_function_definitions(tree.root_node, source_code)
            function_calls = self._find_function_calls(tree.root_node, source_code, function_name)
            
            # 确定每个函数调用属于哪个函数定义
            source_lines = source_code.split('\n')
            for call_line in function_calls:
                containing_function_info = self._find_containing_function(call_line, function_definitions)
                if containing_function_info:
                    # 检查是否已存在相同的调用者
                    existing_names = [caller['name'] for caller in callers]
                    if containing_function_info['name'] not in existing_names:
                        # 添加函数完整代码
                        start_line = containing_function_info['start_line']
                        end_line = containing_function_info['end_line']
                        function_code = '\n'.join(source_lines[start_line-1:end_line])
                        containing_function_info['code'] = function_code
                        callers.append(containing_function_info)
        
        except Exception as e:
            self.logger.warning(f"解析文件 {file_path} 时出错: {e}")
        
        return callers
    
    def _find_function_definitions(self, node, source_code: str) -> List[tuple]:
        """
        查找函数定义
        
        Args:
            node: tree-sitter节点
            source_code: 源代码
        
        Returns:
            List[tuple]: (函数名, 开始行, 结束行) 的列表
        """
        function_definitions = []
        
        def traverse(node):
            if node.type == 'function_definition':
                # 查找函数名
                declarator = None
                for child in node.children:
                    if child.type == 'function_declarator':
                        declarator = child
                        break
                
                if declarator:
                    # 获取函数名
                    identifier = None
                    for child in declarator.children:
                        if child.type == 'identifier':
                            identifier = child
                            break
                    
                    if identifier:
                        func_name = source_code[identifier.start_byte:identifier.end_byte]
                        start_line = node.start_point[0] + 1
                        end_line = node.end_point[0] + 1
                        function_definitions.append((func_name, start_line, end_line))
            
            # 递归遍历子节点
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return function_definitions
    
    def _find_function_calls(self, node, source_code: str, function_name: str) -> List[int]:
        """
        查找函数调用
        
        Args:
            node: tree-sitter节点
            source_code: 源代码
            function_name: 要查找的函数名
        
        Returns:
            List[int]: 函数调用所在的行号列表
        """
        function_calls = []
        
        def traverse(node):
            if node.type == 'call_expression':
                # 检查是否是目标函数的调用
                function_node = node.children[0] if node.children else None
                if function_node and function_node.type == 'identifier':
                    called_func_name = source_code[function_node.start_byte:function_node.end_byte]
                    if called_func_name == function_name:
                        call_line = node.start_point[0] + 1
                        function_calls.append(call_line)
            
            # 递归遍历子节点
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return function_calls
    
    def _find_containing_function(self, call_line: int, function_definitions: List[tuple]) -> Optional[Dict]:
        """
        查找包含指定行的函数定义
        
        Args:
            call_line: 函数调用所在行号
            function_definitions: 函数定义列表
        
        Returns:
            Optional[Dict]: 包含该行的函数信息，格式: {'name': str, 'start_line': int, 'end_line': int}
        """
        for func_name, start_line, end_line in function_definitions:
            if start_line <= call_line <= end_line:
                return {
                    'name': func_name,
                    'start_line': start_line,
                    'end_line': end_line
                }
        
        return None