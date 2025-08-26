#!/usr/bin/env python3
"""
函数提取器 - 使用tree-sitter解析C/C++文件并提取函数定义
重构版本：完全使用node.text API，不依赖content参数
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser, Node
from typing import List, Optional
import logging
from .function_info import FunctionInfo
from .type_registry import TypeRegistry
from .file_extensions import is_cpp_file

# 配置logging
logger = logging.getLogger(__name__)


class FunctionExtractor:
    """C/C++函数提取器 - 重构版本"""
    
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
        is_cpp = is_cpp_file(file_path)
        
        # 选择合适的解析器
        parser = self.cpp_parser if is_cpp else self.c_parser
        
        try:
            # 解析代码
            tree = parser.parse(content.encode('utf-8'))
            root_node = tree.root_node
            
            # 递归提取函数 - 只传递node，不传递content
            self._extract_functions_recursive(root_node, file_path, functions, is_cpp)
            
        except Exception as e:
            logger.error(f"解析文件 {file_path} 时出错: {e}")
        
        return functions
    
    def _extract_functions_recursive(self, node: Node, file_path: str, 
                                   functions: List[FunctionInfo], is_cpp: bool, 
                                   current_scope: str = ""):
        """递归提取函数定义"""
        
        # 检查当前节点是否为函数定义
        if node.type == 'function_definition':
            func_info = self._parse_function_definition(node, file_path, current_scope, is_cpp)
            if func_info:
                functions.append(func_info)
            return
        
        # 检查当前节点是否为函数声明
        if node.type == 'declaration':
            func_info = self._parse_function_declaration(node, file_path, current_scope, is_cpp)
            if func_info:
                functions.append(func_info)
            return
        
        # 处理C++特有的结构
        if is_cpp:
            # 处理类定义
            if node.type in ['class_specifier', 'struct_specifier']:
                class_name = self._get_class_name(node)
                new_scope = f"{current_scope}::{class_name}" if current_scope else class_name
                # 递归处理类内部的函数
                for child in node.children:
                    self._extract_functions_recursive(child, file_path, functions, 
                                                    is_cpp, new_scope)
                return
            
            # 处理命名空间
            if node.type == 'namespace_definition':
                namespace_name = self._get_namespace_name(node)
                new_scope = f"{current_scope}::{namespace_name}" if current_scope else namespace_name
                # 递归处理命名空间内部的函数
                for child in node.children:
                    self._extract_functions_recursive(child, file_path, functions, 
                                                    is_cpp, new_scope)
                return
        
        # 递归处理子节点
        for child in node.children:
            self._extract_functions_recursive(child, file_path, functions, 
                                            is_cpp, current_scope)
    
    def _parse_function_definition(self, node: Node, file_path: str, 
                                  scope: str, is_cpp: bool) -> Optional[FunctionInfo]:
        """解析函数定义"""
        try:
            # 直接从function_definition节点的结构中提取信息
            # function_definition的结构：[返回类型, function_declarator, compound_statement]
            
            func_name = None
            parameters = []
            return_type = "unknown"
            
            # 遍历function_definition的直接子节点
            function_declarator = None
            for child in node.children:
                if child.type == 'function_declarator':
                    function_declarator = child
                    break
                elif child.type in ['primitive_type', 'type_identifier', 'sized_type_specifier']:
                    # 这是返回类型，直接使用node.text
                    return_type = child.text.decode('utf-8').strip()
            
            if not function_declarator:
                logger.debug(f"在function_definition中找不到function_declarator (行 {node.start_point[0] + 1})")
                return None
            
            # 从function_declarator中提取函数名和参数
            # function_declarator的结构：[identifier, parameter_list]
            for child in function_declarator.children:
                if child.type == 'identifier':
                    # 直接使用node.text获取函数名
                    func_name = child.text.decode('utf-8').strip()
                    logger.debug(f"找到函数名: '{func_name}' (行 {node.start_point[0] + 1})")
                elif child.type == 'parameter_list':
                    # 这是参数列表
                    parameters = self._parse_parameters(child)
            
            if not func_name:
                logger.warning(f"无法从function_declarator中提取函数名 (行 {node.start_point[0] + 1})")
                return None
            
            # 如果没有找到返回类型，尝试重新解析
            if return_type == "unknown":
                return_type = self._parse_return_type(node)
            
            # 获取行号
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            logger.debug(f"成功解析函数: {func_name} (行 {start_line}-{end_line})")
            
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
    
    def _parse_function_declaration(self, node: Node, file_path: str, 
                                   scope: str, is_cpp: bool) -> Optional[FunctionInfo]:
        """解析函数声明"""
        try:
            # 简化的声明解析
            # 在declaration节点中查找function_declarator
            function_declarator = None
            return_type = "unknown"
            
            for child in node.children:
                if child.type == 'function_declarator':
                    function_declarator = child
                elif child.type in ['primitive_type', 'type_identifier', 'sized_type_specifier']:
                    return_type = child.text.decode('utf-8').strip()
            
            if not function_declarator:
                return None
            
            func_name = None
            parameters = []
            
            for child in function_declarator.children:
                if child.type == 'identifier':
                    func_name = child.text.decode('utf-8').strip()
                elif child.type == 'parameter_list':
                    parameters = self._parse_parameters(child)
            
            if not func_name:
                return None
            
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
            logger.warning(f"解析函数声明时出错: {e}")
            return None
    
    def _parse_parameters(self, param_list_node: Node) -> List[str]:
        """解析函数参数列表"""
        parameters = []
        
        try:
            for child in param_list_node.children:
                if child.type == 'parameter_declaration':
                    # 直接使用node.text获取参数文本
                    param_text = child.text.decode('utf-8').strip()
                    if param_text and param_text != ',' and param_text != 'void':
                        parameters.append(param_text)
        except Exception as e:
            logger.warning(f"解析参数列表失败: {e}")
        
        return parameters
    
    def _parse_return_type(self, function_node: Node) -> str:
        """解析函数返回类型"""
        try:
            # 在function_definition的子节点中查找返回类型
            for child in function_node.children:
                if child.type in ['primitive_type', 'type_identifier', 'sized_type_specifier']:
                    return_type_text = child.text.decode('utf-8').strip()
                    return return_type_text if return_type_text else "void"
            
            return "void"
            
        except Exception as e:
            logger.warning(f"解析返回类型时出错: {e}")
            return "void"
    
    def _get_class_name(self, class_node: Node) -> str:
        """获取类名"""
        try:
            for child in class_node.children:
                if child.type == 'type_identifier':
                    return child.text.decode('utf-8').strip()
            return "unknown_class"
        except:
            return "unknown_class"
    
    def _get_namespace_name(self, namespace_node: Node) -> str:
        """获取命名空间名"""
        try:
            for child in namespace_node.children:
                if child.type == 'identifier':
                    return child.text.decode('utf-8').strip()
            return "unknown_namespace"
        except:
            return "unknown_namespace"
