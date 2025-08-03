#!/usr/bin/env python3
"""
Slicer包 - C/C++代码切片工具
"""

from .function_slice import slice_function_by_variable

# 版本信息
__version__ = "1.0.0"
__author__ = "Slicer Team"

# 公开的API
__all__ = [
    'slice_function_by_variable'
]

# 包的简介
__doc__ = """
Slicer包提供了C/C++代码切片功能：

主要功能：
- 基于tree-sitter的函数级变量切片
- 支持C/C++语法分析
- 提取与指定变量相关的所有代码段

使用示例：

from slicer import slice_function_by_variable

function_code = '''
int foo(int a) {
    int x = 0;
    x = a + 1;
    return x;
}
'''

result = slice_function_by_variable(function_code, "x", language="c")
print(result)
""" 