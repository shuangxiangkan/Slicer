#!/usr/bin/env python3
"""
类型提取器 - 从C/C++代码中提取类型定义
"""

import logging
import re
from typing import List, Optional
from tree_sitter import Node

from .type_registry import TypeRegistry, TypeKind

logger = logging.getLogger(__name__)


class TypeExtractor:
    """类型定义提取器"""
    
    def __init__(self, type_registry: TypeRegistry):
        self.type_registry = type_registry
    
    def extract_from_content(self, content: str, tree_root: Node, file_path: str = ""):
        """从代码内容中提取类型定义"""
        try:
            self._extract_types_recursive(tree_root, content, file_path)
        except Exception as e:
            logger.warning(f"提取类型定义时出错 ({file_path}): {e}")
    
    def _extract_types_recursive(self, node: Node, content: str, file_path: str):
        """递归提取类型定义"""
        
        # 处理typedef
        if node.type == 'type_definition':
            self._extract_typedef(node, content, file_path)
        
        # 处理struct定义
        elif node.type == 'struct_specifier':
            self._extract_struct(node, content, file_path)
        
        # 处理union定义
        elif node.type == 'union_specifier':
            self._extract_union(node, content, file_path)
        
        # 处理enum定义
        elif node.type == 'enum_specifier':
            self._extract_enum(node, content, file_path)
        
        # 递归处理子节点
        for child in node.children:
            self._extract_types_recursive(child, content, file_path)
    
    def _extract_typedef(self, node: Node, content: str, file_path: str):
        """提取typedef定义"""
        try:
            # 获取完整的typedef文本
            typedef_text = content[node.start_byte:node.end_byte].strip()
            
            # 匹配 typedef 语句: typedef [type] [name];
            typedef_match = re.match(r'typedef\s+(.+?)\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*;', typedef_text, re.DOTALL)
            
            if typedef_match:
                underlying_type = typedef_match.group(1).strip()
                type_name = typedef_match.group(2).strip()
                
                # 清理底层类型（移除多余的空白和换行）
                underlying_type = re.sub(r'\s+', ' ', underlying_type)
                
                self.type_registry.register_typedef(type_name, underlying_type)
                logger.debug(f"注册typedef: {type_name} -> {underlying_type}")
            else:
                # 回退到树遍历方法
                self._extract_typedef_fallback(node, content, file_path)
                
        except Exception as e:
            logger.warning(f"解析typedef时出错: {e}")
    
    def _extract_typedef_fallback(self, node: Node, content: str, file_path: str):
        """typedef解析的回退方法"""
        try:
            # typedef的结构通常是: typedef [type] [name];
            type_declarator = None
            underlying_type_parts = []
            
            # 查找类型声明器和底层类型
            for child in node.children:
                if child.type == 'type_identifier':
                    # 这是新的类型名
                    type_declarator = content[child.start_byte:child.end_byte]
                elif child.type == 'pointer_declarator':
                    # 指针类型的typedef
                    type_declarator, pointer_info = self._parse_pointer_declarator(child, content)
                    underlying_type_parts.append(pointer_info)
                elif child.type in ['primitive_type', 'struct_specifier', 'union_specifier', 'enum_specifier']:
                    # 底层类型
                    underlying_type_parts.append(content[child.start_byte:child.end_byte])
                elif child.type == 'sized_type_specifier':
                    # 如 unsigned int
                    underlying_type_parts.append(content[child.start_byte:child.end_byte])
            
            if type_declarator:
                underlying_type = ' '.join(underlying_type_parts).strip()
                if underlying_type:
                    self.type_registry.register_typedef(type_declarator, underlying_type)
                    logger.debug(f"注册typedef(回退): {type_declarator} -> {underlying_type}")
                
        except Exception as e:
            logger.warning(f"回退解析typedef时出错: {e}")
    
    def _parse_pointer_declarator(self, node: Node, content: str) -> tuple:
        """解析指针声明器"""
        pointer_count = 0
        declarator_name = ""
        
        for child in node.children:
            if child.type == '*':
                pointer_count += 1
            elif child.type == 'type_identifier':
                declarator_name = content[child.start_byte:child.end_byte]
            elif child.type == 'pointer_declarator':
                # 嵌套指针
                sub_name, sub_info = self._parse_pointer_declarator(child, content)
                declarator_name = sub_name
                pointer_count += sub_info.count('*')
        
        pointer_info = '*' * pointer_count
        return declarator_name, pointer_info
    
    def _extract_struct(self, node: Node, content: str, file_path: str):
        """提取struct定义"""
        try:
            struct_name = None
            members = []
            
            # 查找struct名称
            for child in node.children:
                if child.type == 'type_identifier':
                    struct_name = content[child.start_byte:child.end_byte]
                elif child.type == 'field_declaration_list':
                    # 提取成员
                    members = self._extract_struct_members(child, content)
            
            if struct_name:
                self.type_registry.register_struct(struct_name, members)
                logger.debug(f"注册struct: {struct_name} (成员数: {len(members)})")
                
        except Exception as e:
            logger.warning(f"解析struct时出错: {e}")
    
    def _extract_struct_members(self, field_list_node: Node, content: str) -> List[str]:
        """提取结构体成员"""
        members = []
        
        for child in field_list_node.children:
            if child.type == 'field_declaration':
                member_text = content[child.start_byte:child.end_byte].strip()
                if member_text and not member_text.startswith('//'):
                    members.append(member_text)
        
        return members
    
    def _extract_union(self, node: Node, content: str, file_path: str):
        """提取union定义"""
        try:
            union_name = None
            members = []
            
            for child in node.children:
                if child.type == 'type_identifier':
                    union_name = content[child.start_byte:child.end_byte]
                elif child.type == 'field_declaration_list':
                    members = self._extract_struct_members(child, content)  # 复用struct成员提取
            
            if union_name:
                self.type_registry.register_union(union_name, members)
                logger.debug(f"注册union: {union_name} (成员数: {len(members)})")
                
        except Exception as e:
            logger.warning(f"解析union时出错: {e}")
    
    def _extract_enum(self, node: Node, content: str, file_path: str):
        """提取enum定义"""
        try:
            enum_name = None
            enum_values = []
            
            for child in node.children:
                if child.type == 'type_identifier':
                    enum_name = content[child.start_byte:child.end_byte]
                elif child.type == 'enumerator_list':
                    enum_values = self._extract_enum_values(child, content)
            
            if enum_name:
                self.type_registry.register_enum(enum_name, enum_values)
                logger.debug(f"注册enum: {enum_name} (值数: {len(enum_values)})")
                
        except Exception as e:
            logger.warning(f"解析enum时出错: {e}")
    
    def _extract_enum_values(self, enum_list_node: Node, content: str) -> List[str]:
        """提取枚举值"""
        values = []
        
        for child in enum_list_node.children:
            if child.type == 'enumerator':
                value_text = content[child.start_byte:child.end_byte].strip()
                if value_text and value_text != ',':
                    values.append(value_text)
        
        return values
    
    def extract_from_preprocessor(self, content: str) -> None:
        """从预处理器指令中提取类型定义（如简单的#define）"""
        lines = content.split('\n')
        
        for line in lines:
            line = line.strip()
            if line.startswith('#define') and len(line.split()) >= 3:
                parts = line.split()
                if len(parts) >= 3:
                    define_name = parts[1]
                    define_value = ' '.join(parts[2:])
                    
                    # 简单的类型别名检测
                    if self._looks_like_type_alias(define_value):
                        self.type_registry.register_typedef(define_name, define_value)
                        logger.debug(f"注册#define类型别名: {define_name} -> {define_value}")
    
    def _looks_like_type_alias(self, value: str) -> bool:
        """判断#define值是否看起来像类型别名"""
        # 简单的启发式判断
        value = value.strip()
        
        # 包含指针符号
        if '*' in value:
            return True
        
        # 常见的类型关键词
        type_keywords = ['int', 'char', 'float', 'double', 'void', 'long', 'short', 'unsigned', 'signed']
        for keyword in type_keywords:
            if keyword in value.lower():
                return True
        
        # 以大写字母开头，可能是类型名
        if value and value[0].isupper():
            return True
        
        return False 