#!/usr/bin/env python3
"""
函数提取器 - 使用tree-sitter提取C/C++函数定义
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Node
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import re


class FunctionInfo:
    """函数信息类"""
    
    def __init__(self, name: str, return_type: str, parameters: List[str], 
                 start_line: int, end_line: int, file_path: str, 
                 is_declaration: bool = False, scope: str = ""):
        self.name = name
        self.return_type = return_type
        self.parameters = parameters
        self.start_line = start_line
        self.end_line = end_line
        self.file_path = file_path
        self.is_declaration = is_declaration
        self.scope = scope  # 对于C++，可能是类或命名空间
    
    def __str__(self):
        param_str = ", ".join(self.parameters)
        decl_type = "声明" if self.is_declaration else "定义"
        scope_str = f"{self.scope}::" if self.scope else ""
        return f"{self.return_type} {scope_str}{self.name}({param_str}) [{decl_type}]"
    
    def get_signature(self):
        """获取函数签名"""
        param_str = ", ".join(self.parameters)
        scope_str = f"{self.scope}::" if self.scope else ""
        return f"{self.return_type} {scope_str}{self.name}({param_str})"


class FunctionExtractor:
    """C/C++函数提取器"""
    
    def __init__(self):
        # 初始化C和C++解析器
        self.c_language = Language(tsc.language(), "c")
        self.cpp_language = Language(tscpp.language(), "cpp")
        
        self.c_parser = Parser()
        self.cpp_parser = Parser()
        
        self.c_parser.set_language(self.c_language)
        self.cpp_parser.set_language(self.cpp_language)
        
        self.functions = []
    
    def extract_from_file(self, file_path: str) -> List[FunctionInfo]:
        """从文件中提取函数定义"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            return self.extract_from_content(content, file_path)
        
        except Exception as e:
            print(f"警告: 无法读取文件 {file_path}: {e}")
            return []
    
    def extract_from_content(self, content: str, file_path: str = "") -> List[FunctionInfo]:
        """从代码内容中提取函数定义"""
        # 根据文件扩展名选择解析器
        file_ext = Path(file_path).suffix.lower() if file_path else ".c"
        
        if file_ext in {'.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'}:
            parser = self.cpp_parser
            is_cpp = True
        else:
            parser = self.c_parser
            is_cpp = False
        
        # 解析代码
        tree = parser.parse(bytes(content, 'utf8'))
        root_node = tree.root_node
        
        # 提取函数
        functions = []
        self._extract_functions_recursive(root_node, content, file_path, functions, is_cpp)
        
        return functions
    
    def _extract_functions_recursive(self, node: Node, content: str, file_path: str, 
                                   functions: List[FunctionInfo], is_cpp: bool, 
                                   current_scope: str = ""):
        """递归提取函数定义"""
        
        # 处理函数定义
        if node.type == 'function_definition':
            func_info = self._parse_function_definition(node, content, file_path, 
                                                       current_scope, is_cpp)
            if func_info:
                functions.append(func_info)
        
        # 处理函数声明
        elif node.type == 'declaration':
            func_info = self._parse_function_declaration(node, content, file_path, 
                                                        current_scope, is_cpp)
            if func_info:
                functions.append(func_info)
        
        # 对于C++，处理类和命名空间
        elif is_cpp:
            if node.type == 'class_specifier':
                class_name = self._get_class_name(node, content)
                new_scope = f"{current_scope}::{class_name}" if current_scope else class_name
                
                # 递归处理类内的方法
                for child in node.children:
                    self._extract_functions_recursive(child, content, file_path, 
                                                     functions, is_cpp, new_scope)
                return
            
            elif node.type == 'namespace_definition':
                namespace_name = self._get_namespace_name(node, content)
                new_scope = f"{current_scope}::{namespace_name}" if current_scope else namespace_name
                
                # 递归处理命名空间内的函数
                for child in node.children:
                    self._extract_functions_recursive(child, content, file_path, 
                                                     functions, is_cpp, new_scope)
                return
        
        # 递归处理子节点
        for child in node.children:
            self._extract_functions_recursive(child, content, file_path, functions, 
                                            is_cpp, current_scope)
    
    def _parse_function_definition(self, node: Node, content: str, file_path: str, 
                                  scope: str, is_cpp: bool) -> Optional[FunctionInfo]:
        """解析函数定义"""
        try:
            # 获取函数信息
            declarator = None
            type_specifier = None
            
            for child in node.children:
                if child.type == 'function_declarator':
                    declarator = child
                elif child.type in ['type_identifier', 'primitive_type', 'sized_type_specifier']:
                    type_specifier = child
            
            if not declarator:
                return None
            
            # 获取函数名和参数
            func_name = None
            parameters = []
            
            for child in declarator.children:
                if child.type == 'identifier':
                    func_name = content[child.start_byte:child.end_byte]
                elif child.type == 'parameter_list':
                    parameters = self._parse_parameters(child, content)
            
            if not func_name:
                return None
            
            # 获取返回类型
            return_type = "void"  # 默认
            if type_specifier:
                return_type = content[type_specifier.start_byte:type_specifier.end_byte]
            
            # 获取行号
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            return FunctionInfo(
                name=func_name,
                return_type=return_type,
                parameters=parameters,
                start_line=start_line,
                end_line=end_line,
                file_path=file_path,
                is_declaration=False,
                scope=scope
            )
        
        except Exception as e:
            print(f"警告: 解析函数定义时出错: {e}")
            return None
    
    def _parse_function_declaration(self, node: Node, content: str, file_path: str, 
                                   scope: str, is_cpp: bool) -> Optional[FunctionInfo]:
        """解析函数声明"""
        try:
            # 检查是否包含函数声明
            declarator = None
            type_specifier = None
            
            for child in node.children:
                if child.type == 'function_declarator':
                    declarator = child
                elif child.type in ['type_identifier', 'primitive_type', 'sized_type_specifier']:
                    type_specifier = child
            
            if not declarator:
                return None
            
            # 获取函数名和参数
            func_name = None
            parameters = []
            
            for child in declarator.children:
                if child.type == 'identifier':
                    func_name = content[child.start_byte:child.end_byte]
                elif child.type == 'parameter_list':
                    parameters = self._parse_parameters(child, content)
            
            if not func_name:
                return None
            
            # 获取返回类型
            return_type = "void"  # 默认
            if type_specifier:
                return_type = content[type_specifier.start_byte:type_specifier.end_byte]
            
            # 获取行号
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            return FunctionInfo(
                name=func_name,
                return_type=return_type,
                parameters=parameters,
                start_line=start_line,
                end_line=end_line,
                file_path=file_path,
                is_declaration=True,
                scope=scope
            )
        
        except Exception as e:
            return None
    
    def _parse_parameters(self, param_list_node: Node, content: str) -> List[str]:
        """解析函数参数列表"""
        parameters = []
        
        for child in param_list_node.children:
            if child.type == 'parameter_declaration':
                param_text = content[child.start_byte:child.end_byte].strip()
                if param_text and param_text != ',':
                    parameters.append(param_text)
        
        return parameters
    
    def _get_class_name(self, class_node: Node, content: str) -> str:
        """获取类名"""
        for child in class_node.children:
            if child.type == 'type_identifier':
                return content[child.start_byte:child.end_byte]
        return "Unknown"
    
    def _get_namespace_name(self, namespace_node: Node, content: str) -> str:
        """获取命名空间名"""
        for child in namespace_node.children:
            if child.type == 'identifier':
                return content[child.start_byte:child.end_byte]
        return "Unknown"
    
    def print_functions(self, functions: List[FunctionInfo], show_details: bool = True):
        """打印函数列表"""
        if not functions:
            print("未找到任何函数")
            return
        
        print(f"找到 {len(functions)} 个函数:")
        print("=" * 80)
        
        # 按文件分组
        files_functions = {}
        for func in functions:
            file_name = Path(func.file_path).name if func.file_path else "Unknown"
            if file_name not in files_functions:
                files_functions[file_name] = []
            files_functions[file_name].append(func)
        
        for file_name, file_functions in files_functions.items():
            print(f"\n📁 文件: {file_name}")
            print("-" * 60)
            
            for i, func in enumerate(file_functions, 1):
                decl_marker = "🔗" if func.is_declaration else "🔧"
                print(f"{i:2d}. {decl_marker} {func}")
                
                if show_details:
                    print(f"    📍 位置: 第{func.start_line}-{func.end_line}行")
                    if func.file_path:
                        print(f"    📂 文件: {func.file_path}")
                    print()
        
        # 统计信息
        definitions = [f for f in functions if not f.is_declaration]
        declarations = [f for f in functions if f.is_declaration]
        
        print("=" * 80)
        print("统计信息:")
        print(f"  总函数数: {len(functions)}")
        print(f"  函数定义: {len(definitions)}")
        print(f"  函数声明: {len(declarations)}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("使用方法: python function_extractor.py <文件路径>")
        sys.exit(1)
    
    extractor = FunctionExtractor()
    try:
        functions = extractor.extract_from_file(sys.argv[1])
        extractor.print_functions(functions)
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1) 