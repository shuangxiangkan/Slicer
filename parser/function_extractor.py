#!/usr/bin/env python3
"""
函数提取器 - 使用tree-sitter解析C/C++文件并提取函数定义
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Node
from pathlib import Path
from typing import List, Optional, Dict
import logging
from .function_info import FunctionInfo
from .type_registry import TypeRegistry

# 配置logging
logger = logging.getLogger(__name__)


class FunctionExtractor:
    """C/C++函数提取器"""
    
    def __init__(self, type_registry: TypeRegistry = None):
        self.type_registry = type_registry
        
        # 初始化C和C++解析器
        try:
            self.c_language = Language(tsc.language(), "c")
            self.c_parser = Parser()
            self.c_parser.set_language(self.c_language)
            
            self.cpp_language = Language(tscpp.language(), "cpp")
            self.cpp_parser = Parser()
            self.cpp_parser.set_language(self.cpp_language)
        except Exception as e:
            logger.error(f"初始化解析器失败: {e}")
            raise
    
    def extract_from_file(self, file_path: str) -> List[FunctionInfo]:
        """从文件中提取函数"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return self.extract_from_content(content, file_path)
        except Exception as e:
            logger.warning(f"无法读取文件 {file_path}: {e}")
            return []
    
    def extract_from_content(self, content: str, file_path: str = "") -> List[FunctionInfo]:
        """从内容中提取函数"""
        functions = []
        
        # 判断是否为C++文件
        is_cpp = any(file_path.endswith(ext) for ext in ['.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'])
        
        # 选择合适的解析器
        parser = self.cpp_parser if is_cpp else self.c_parser
        
        try:
            # 解析代码
            tree = parser.parse(content.encode('utf-8'))
            root_node = tree.root_node
            
            # 递归提取函数
            self._extract_functions_recursive(root_node, content, file_path, functions, is_cpp)
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {e}")
        
        return functions
    
    def _extract_functions_recursive(self, node: Node, content: str, file_path: str, 
                                   functions: List[FunctionInfo], is_cpp: bool, 
                                   current_scope: str = ""):
        """递归提取函数定义"""
        
        # 检查当前节点是否为函数定义
        if node.type == 'function_definition':
            func_info = self._parse_function_definition(node, content, file_path, current_scope, is_cpp)
            if func_info:
                functions.append(func_info)
            return
        
        # 检查当前节点是否为函数声明
        if node.type == 'declaration':
            func_info = self._parse_function_declaration(node, content, file_path, current_scope, is_cpp)
            if func_info:
                functions.append(func_info)
            return
        
        # 处理C++特有的结构
        if is_cpp:
            # 处理类定义
            if node.type in ['class_specifier', 'struct_specifier']:
                class_name = self._get_class_name(node, content)
                new_scope = f"{current_scope}::{class_name}" if current_scope else class_name
                
                # 递归处理类内的函数
                for child in node.children:
                    self._extract_functions_recursive(child, content, file_path, 
                                                     functions, is_cpp, new_scope)
                return
            
            # 处理命名空间
            if node.type == 'namespace_definition':
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
            # 递归查找函数声明器
            def find_function_declarator(node):
                if node.type == 'function_declarator':
                    return node
                for child in node.children:
                    result = find_function_declarator(child)
                    if result:
                        return result
                return None
            
            declarator = find_function_declarator(node)
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
            
            # 获取返回类型 - 改进的解析逻辑
            return_type = self._parse_return_type(node, content)
            
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
                scope=scope,
                type_registry=self.type_registry
            )
        
        except Exception as e:
            logger.warning(f"解析函数定义时出错: {e}")
            return None
    
    def _parse_function_declaration(self, node: Node, content: str, file_path: str, 
                                   scope: str, is_cpp: bool) -> Optional[FunctionInfo]:
        """解析函数声明"""
        try:
            # 递归查找函数声明器
            def find_function_declarator(node):
                if node.type == 'function_declarator':
                    return node
                for child in node.children:
                    result = find_function_declarator(child)
                    if result:
                        return result
                return None
            
            declarator = find_function_declarator(node)
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
            
            # 获取返回类型 - 改进的解析逻辑
            return_type = self._parse_return_type(node, content)
            
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
                scope=scope,
                type_registry=self.type_registry
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
    
    def _parse_return_type(self, function_node: Node, content: str) -> str:
        """解析函数返回类型"""
        try:
            # 查找函数声明器的位置
            declarator_start = None
            for child in function_node.children:
                if child.type == 'function_declarator':
                    declarator_start = child.start_byte
                    break
            
            if declarator_start is None:
                return "void"
            
            # 返回类型是从函数开始到函数声明器之间的文本
            return_type_text = content[function_node.start_byte:declarator_start].strip()
            
            # 清理返回类型文本
            # 移除可能的存储类说明符和其他修饰符
            return_type_text = return_type_text.replace('static', '').replace('inline', '').replace('extern', '')
            return_type_text = return_type_text.replace('CJSON_PUBLIC(', '').replace(')', '')
            return_type_text = ' '.join(return_type_text.split())  # 标准化空格
            
            return return_type_text if return_type_text else "void"
            
        except Exception as e:
            logger.warning(f"解析返回类型时出错: {e}")
            return "void"
    
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
    
    def get_functions_info(self, functions: List[FunctionInfo], show_details: bool = True) -> dict:
        """获取函数信息（用于日志或返回）"""
        if not functions:
            return {"message": "未找到任何函数", "functions": [], "stats": {}}
        
        info = {
            "message": f"找到 {len(functions)} 个函数",
            "functions": []
        }
        
        # 按文件分组
        files_functions = {}
        for func in functions:
            file_name = Path(func.file_path).name if func.file_path else "Unknown"
            if file_name not in files_functions:
                files_functions[file_name] = []
            files_functions[file_name].append(func)
        
        for file_name, file_functions in files_functions.items():
            file_info = {
                "file": file_name,
                "functions": []
            }
            
            for func in file_functions:
                func_info = {
                    "name": func.name,
                    "signature": func.get_signature(),
                    "is_declaration": func.is_declaration,
                    "start_line": func.start_line,
                    "end_line": func.end_line
                }
                
                if show_details:
                    func_info.update({
                        "file_path": func.file_path,
                        "scope": func.scope
                    })
                
                file_info["functions"].append(func_info)
            
            info["functions"].append(file_info)
        
        # 统计信息
        definitions = [f for f in functions if not f.is_declaration]
        declarations = [f for f in functions if f.is_declaration]
        
        info["stats"] = {
            "total_functions": len(functions),
            "function_definitions": len(definitions),
            "function_declarations": len(declarations)
        }
        
        return info 