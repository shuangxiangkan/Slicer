#!/usr/bin/env python3
"""
Parser包 - C/C++代码解析和分析工具
"""

import logging
import sys

from .file_finder import FileFinder
from .function_extractor import FunctionExtractor, FunctionInfo
from .repo_analyzer import RepoAnalyzer
from .header_analyzer import HeaderAnalyzer


# 版本信息
__version__ = "1.0.0"
__author__ = "Parser Team"

# 公开的API
__all__ = [
    'FileFinder',
    'FunctionExtractor', 
    'FunctionInfo',
    'RepoAnalyzer',
    'HeaderAnalyzer',
    'setup_logging'
]

# 包的简介
__doc__ = """
Parser包提供了强大的C/C++代码分析功能：

主要功能：
- 基于tree-sitter的语法分析
- 函数提取与分析（定义/声明）
- 类型系统分析（typedef/struct/union/enum）
- 调用图构建与分析
- 头文件include关系分析
- 复杂度和依赖关系分析
- API函数提取（基于关键字识别）
- 函数调用关系分析

主要类：
- RepoAnalyzer: 完整的代码仓库分析器
- HeaderAnalyzer: 专门的头文件include分析器

支持的文件类型：
- C文件: .c, .h
- C++文件: .cpp, .cxx, .cc, .hpp, .hxx, .hh
- 其他: .h++, .inc

使用示例：

1. 分析单个文件：
   analyzer = RepoAnalyzer("example.c")
   result = analyzer.analyze()

2. 基于配置文件分析：
   analyzer = RepoAnalyzer("config.json")
   result = analyzer.analyze()

3. 分析头文件include关系：
   header_analyzer = HeaderAnalyzer()
   result = header_analyzer.analyze_file("example.h")
   
   # 或通过RepoAnalyzer：
   analyzer = RepoAnalyzer("example.h")
   header_result = analyzer.analyze_headers()

4. 提取API函数（基于关键字）：
   analyzer = RepoAnalyzer("cjson_library")
   analyzer.analyze()
   
   # 提取包含特定关键字的API函数
   api_functions = analyzer.get_api_functions("CJSON_PUBLIC", ["cJSON"], header_files=["cJSON.h"])
   
   # 显示API函数信息
   print(f"找到 {len(api_functions)} 个API函数")
   for func in api_functions:
       print(f"- {func.name} ({'声明' if func.is_declaration else '定义'})")

5. 函数调用关系分析：
   analyzer = RepoAnalyzer("config.json")
   analyzer.analyze()
   
   # 获取函数的调用者
   callers_info = analyzer.get_function_callers("malloc")
   print(f"函数 {callers_info['function_name']} 被 {callers_info['caller_count']} 个函数调用")
   
   # 获取函数的依赖关系
   dependencies = analyzer.get_function_dependencies("main", max_depth=3)
   dependents = analyzer.get_function_dependents("malloc", max_depth=2)

更多详细信息请参考各个类的文档。
"""

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