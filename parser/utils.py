#!/usr/bin/env python3
"""
Parser utils module
"""

import tree_sitter_c as tsc
import tree_sitter_cpp as tscpp
from tree_sitter import Language, Parser
import logging
from typing import Tuple, Optional
from .file_extensions import is_cpp_file

logger = logging.getLogger(__name__)


class TreeSitterManager:
    """
    Tree-sitter解析器管理器
    统一管理C/C++解析器的初始化和获取
    """
    
    def __init__(self):
        self.c_language = None
        self.c_parser = None
        self.cpp_language = None
        self.cpp_parser = None
        self.parser_available = False
        self._init_parsers()
    
    def _init_parsers(self):
        """
        初始化C和C++解析器
        """
        try:
            # 初始化C解析器
            self.c_language = Language(tsc.language(), "c")
            self.c_parser = Parser()
            self.c_parser.set_language(self.c_language)
            
            # 初始化C++解析器
            self.cpp_language = Language(tscpp.language(), "cpp")
            self.cpp_parser = Parser()
            self.cpp_parser.set_language(self.cpp_language)
            
            self.parser_available = True
            logger.debug("Tree-sitter解析器初始化成功")
            
        except Exception as e:
            logger.warning(f"无法初始化tree-sitter解析器: {e}")
            self.parser_available = False
    
    def get_parser_for_file(self, file_path: str) -> Tuple[Optional[Parser], Optional[Language]]:
        """
        根据文件路径获取对应的解析器和语言
        
        Args:
            file_path: 文件路径
            
        Returns:
            Tuple[Parser, Language]: 解析器和语言对象，如果不可用则返回(None, None)
        """
        if not self.parser_available:
            return None, None
            
        if is_cpp_file(file_path):
            return self.cpp_parser, self.cpp_language
        else:
            return self.c_parser, self.c_language
    
    def get_parser_for_content(self, is_cpp: bool) -> Tuple[Optional[Parser], Optional[Language]]:
        """
        根据内容类型获取对应的解析器和语言
        
        Args:
            is_cpp: 是否为C++代码
            
        Returns:
            Tuple[Parser, Language]: 解析器和语言对象，如果不可用则返回(None, None)
        """
        if not self.parser_available:
            return None, None
            
        if is_cpp:
            return self.cpp_parser, self.cpp_language
        else:
            return self.c_parser, self.c_language
    
    def parse_content(self, content: str, file_path: str = ""):
        """
        解析代码内容
        
        Args:
            content: 代码内容
            file_path: 文件路径（用于判断语言类型）
            
        Returns:
            Tree: 解析树，如果解析失败则返回None
        """
        parser, language = self.get_parser_for_file(file_path)
        if not parser:
            return None
            
        try:
            return parser.parse(content.encode('utf-8'))
        except Exception as e:
            logger.warning(f"解析内容失败 ({file_path}): {e}")
            return None


# 全局单例实例
_tree_sitter_manager = None


def get_tree_sitter_manager() -> TreeSitterManager:
    """
    获取全局TreeSitterManager单例实例
    
    Returns:
        TreeSitterManager: 全局单例实例
    """
    global _tree_sitter_manager
    if _tree_sitter_manager is None:
        _tree_sitter_manager = TreeSitterManager()
    return _tree_sitter_manager


def init_tree_sitter_for_class(obj):
    """
    为类实例初始化tree-sitter相关属性
    这是一个便利函数，用于替换重复的初始化代码
    
    Args:
        obj: 需要初始化tree-sitter属性的对象
    """
    manager = get_tree_sitter_manager()
    
    # 设置解析器相关属性
    obj.c_language = manager.c_language
    obj.c_parser = manager.c_parser
    obj.cpp_language = manager.cpp_language
    obj.cpp_parser = manager.cpp_parser
    obj.parser_available = manager.parser_available


def create_parser_for_content(content: str, is_cpp: bool = False):
    """
    为特定内容创建独立的解析器实例
    用于需要独立解析器的场景
    
    Args:
        content: 要解析的内容
        is_cpp: 是否为C++代码
        
    Returns:
        Tuple[Parser, Language, Tree]: 解析器、语言和解析树，如果失败则返回(None, None, None)
    """
    try:
        if is_cpp:
            language = Language(tscpp.language(), "cpp")
        else:
            language = Language(tsc.language(), "c")
            
        parser = Parser()
        parser.set_language(language)
        tree = parser.parse(content.encode('utf-8'))
        
        return parser, language, tree
        
    except Exception as e:
        logger.warning(f"创建独立解析器失败: {e}")
        return None, None, None