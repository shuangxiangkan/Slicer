#!/usr/bin/env python3
"""
数据模型定义
"""

import tree_sitter
from enum import Enum
from typing import Set
from dataclasses import dataclass


class SliceType(Enum):
    """切片类型"""
    BACKWARD = "backward"  # 后向切片：影响目标变量的所有语句
    FORWARD = "forward"    # 前向切片：被目标变量影响的所有语句


class ParameterSliceResult:
    """参数切片分析结果"""
    def __init__(self):
        self.function_parameters = []       # 函数参数列表
        self.parameter_slices = {}          # 参数 -> 前向切片行号
        self.return_slice = []              # 返回值后向切片行号
        self.parameter_interactions = {}    # 参数间交互的切片
        self.slice_code_snippets = {}       # 切片代码片段


@dataclass
class Variable:
    """变量信息"""
    name: str
    line: int
    column: int
    node: tree_sitter.Node


@dataclass
class Statement:
    """语句信息"""
    line: int
    code: str
    node: tree_sitter.Node
    variables_defined: Set[str]
    variables_used: Set[str] 