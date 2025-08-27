#!/usr/bin/env python3
"""
函数使用查找器 - 在代码仓库中查找函数的使用情况
"""

import os
import logging
from typing import Dict, List, Optional

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser

from .file_finder import FileFinder
from .config_parser import ConfigParser
from .file_extensions import is_cpp_file

class FunctionUsageFinder:
    """
    函数使用查找器
    
    提供4种函数使用查找功能
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
        
        # 初始化tree-sitter解析器
        self._init_tree_sitter()
    
    def _init_tree_sitter(self):
        """
        初始化tree-sitter解析器
        """
        try:
            self.c_language = Language(tsc.language(), "c")
            self.c_parser = Parser()
            self.c_parser.set_language(self.c_language)
            
            self.cpp_language = Language(tscpp.language(), "cpp")
            self.cpp_parser = Parser()
            self.cpp_parser.set_language(self.cpp_language)
            
            self.parser_available = True
        except Exception as e:
            self.logger.warning(f"无法初始化tree-sitter解析器: {e}")
            self.parser_available = False
    
    def find_usage_in_include_files(self, function_name: str, analyzed_functions: List = None) -> Dict[str, List[str]]:
        """
        在include_files中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            analyzed_functions: 已分析的函数信息列表
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        if not analyzed_functions:
            return {}
        
        callers_by_file = {}
        for function_info in analyzed_functions:
            if hasattr(function_info, 'callees') and function_name in function_info.callees:
                file_path = function_info.file_path
                caller_name = function_info.name
                
                if file_path not in callers_by_file:
                    callers_by_file[file_path] = []
                
                if caller_name not in callers_by_file[file_path]:
                    callers_by_file[file_path].append(caller_name)
        
        return callers_by_file
    
    def find_usage_in_non_include_files(self, function_name: str, repo_root: str) -> Dict[str, List[str]]:
        """
        在非include_files中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            repo_root: 仓库根目录
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        if not self.parser_available:
            self.logger.warning("tree-sitter解析器未初始化，无法解析文件")
            return {}
        
        # 获取所有C/C++文件
        all_files = self.file_finder.find_files(repo_root, recursive=True)
        
        # 获取include_files列表
        include_files = self._get_include_files()
        
        # 过滤出非include_files
        non_include_files = []
        for file_path in all_files:
            abs_file_path = os.path.abspath(file_path)
            is_include_file = any(
                os.path.abspath(inc_file) == abs_file_path 
                for inc_file in include_files
            )
            if not is_include_file:
                non_include_files.append(file_path)
        
        return self._find_usage_in_files(function_name, non_include_files)
    
    def find_usage_in_all_files(self, function_name: str, repo_root: str, analyzed_functions: List = None) -> Dict[str, List[str]]:
        """
        在include_files和非include_files中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            repo_root: 仓库根目录
            analyzed_functions: 已分析的函数信息列表
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        # 合并include_files和非include_files的结果
        include_usage = self.find_usage_in_include_files(function_name, analyzed_functions)
        non_include_usage = self.find_usage_in_non_include_files(function_name, repo_root)
        
        # 合并结果
        all_usage = include_usage.copy()
        for file_path, callers in non_include_usage.items():
            if file_path in all_usage:
                # 合并调用者列表，去重
                existing_callers = set(all_usage[file_path])
                new_callers = set(callers)
                all_usage[file_path] = list(existing_callers | new_callers)
            else:
                all_usage[file_path] = callers
        
        return all_usage
    
    def find_usage_in_test_files(self, function_name: str, repo_root: str) -> Dict[str, List[str]]:
        """
        在文件路径名中包含test的文件中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            repo_root: 仓库根目录
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
        """
        if not self.parser_available:
            self.logger.warning("tree-sitter解析器未初始化，无法解析文件")
            return {}
        
        # 获取所有C/C++文件
        all_files = self.file_finder.find_files(repo_root, recursive=True)
        
        # 过滤出路径中包含test的文件
        test_files = []
        for file_path in all_files:
            if 'test' in file_path.lower():
                test_files.append(file_path)
        
        return self._find_usage_in_files(function_name, test_files)
    
    def _get_include_files(self) -> List[str]:
        """
        获取include_files列表
        
        Returns:
            List[str]: include_files路径列表
        """
        include_files = []
        if self.config_parser:
            try:
                library_path = self.config_parser.get_library_path()
                if self.config_parser.is_include_mode():
                    include_file_names = self.config_parser.get_target_files()
                    for file_name in include_file_names:
                        include_files.append(os.path.join(library_path, file_name))
            except Exception as e:
                self.logger.warning(f"获取include_files失败: {e}")
        return include_files
    
    def _find_usage_in_files(self, function_name: str, file_paths: List[str]) -> Dict[str, List[str]]:
        """
        在指定文件列表中查找函数使用
        
        Args:
            function_name: 要查找的函数名
            file_paths: 文件路径列表
        
        Returns:
            Dict[str, List[str]]: 文件路径 -> 调用者函数名列表的映射
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
    
    def _find_callers_in_file(self, file_path: str, function_name: str) -> List[str]:
        """
        在单个文件中查找函数调用者
        
        Args:
            file_path: 文件路径
            function_name: 要查找的函数名
        
        Returns:
            List[str]: 调用者函数名列表
        """
        callers = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source_code = f.read()
            
            # 选择合适的解析器
            is_cpp = is_cpp_file(file_path)
            parser = self.cpp_parser if is_cpp else self.c_parser
            
            # 解析源代码
            tree = parser.parse(bytes(source_code, 'utf-8'))
            
            # 查找函数定义和函数调用
            function_definitions = self._find_function_definitions(tree.root_node, source_code)
            function_calls = self._find_function_calls(tree.root_node, source_code, function_name)
            
            # 确定每个函数调用属于哪个函数定义
            for call_line in function_calls:
                containing_function = self._find_containing_function(call_line, function_definitions)
                if containing_function and containing_function not in callers:
                    callers.append(containing_function)
        
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
    
    def _find_containing_function(self, call_line: int, function_definitions: List[tuple]) -> Optional[str]:
        """
        查找包含指定行的函数定义
        
        Args:
            call_line: 函数调用所在行号
            function_definitions: 函数定义列表
        
        Returns:
            Optional[str]: 包含该行的函数名，如果没有找到则返回None
        """
        for func_name, start_line, end_line in function_definitions:
            if start_line <= call_line <= end_line:
                return func_name
        
        return None