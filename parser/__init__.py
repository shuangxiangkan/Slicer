#!/usr/bin/env python3
"""
C/C++ 代码解析器模块

提供文件查找、函数提取和仓库分析功能
"""

import logging
import sys

from .file_finder import FileFinder
from .function_extractor import FunctionExtractor, FunctionInfo
from .repo_analyzer import RepoAnalyzer

# 版本信息
__version__ = "1.0.0"
__author__ = "Parser Team"

# 导出的类
__all__ = [
    'FileFinder',
    'FunctionExtractor', 
    'FunctionInfo',
    'RepoAnalyzer',
    'setup_logging'
]


def setup_logging(level=logging.INFO, format_string=None):
    """
    配置日志记录
    
    Args:
        level: 日志级别 (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR)
        format_string: 自定义日志格式字符串
    """
    if format_string is None:
        format_string = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # 为parser模块设置日志级别
    parser_logger = logging.getLogger(__name__.split('.')[0])
    parser_logger.setLevel(level) 