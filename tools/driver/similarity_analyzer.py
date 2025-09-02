#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API Similarity Analysis utilities for computing similarity between API functions.

This module provides a comprehensive API similarity analysis class that can
compute similarity scores between different API function signatures.
"""

import re
from typing import List, Tuple
from difflib import SequenceMatcher
import math

# 添加项目根目录到Python路径
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from parser.function_info import FunctionInfo


class APISimilarityAnalyzer:
    """
    API相似性分析器类
    
    提供API函数之间相似度计算的完整功能，包括名称相似度、
    类型相似度、参数相似度等多维度分析。
    """
    
    def __init__(self, similarity_threshold: float = 0.2):
        """
        初始化API相似性分析器
        
        Args:
            similarity_threshold: 默认的最小相似度阈值
        """
        self.similarity_threshold = similarity_threshold
        self.weights = {
            'name': 0.35,
            'return_type': 0.25,
            'param_types': 0.25,
            'param_count': 0.15
        }
    
    def find_most_similar_apis(self, target_function: FunctionInfo, 
                              all_functions: List[FunctionInfo],
                              similarity_threshold: float = None,
                              max_results: int = 5) -> List[Tuple[FunctionInfo, float]]:
        """
        找到与目标函数最相似的API函数
        
        Args:
            target_function: 目标函数的FunctionInfo对象
            all_functions: 所有函数的FunctionInfo对象列表
            similarity_threshold: 最小相似度阈值，如果为None则使用默认值
            max_results: 返回的最大结果数量
            
        Returns:
            List of (FunctionInfo, similarity_score) tuples, 按相似度降序排列
        """
        if similarity_threshold is None:
            similarity_threshold = self.similarity_threshold
            
        similarities = []
        
        for func in all_functions:
            # 跳过目标函数本身
            if func.name == target_function.name:
                continue
                
            similarity = self.compute_function_similarity(target_function, func)
            
            if similarity >= similarity_threshold:
                similarities.append((func, similarity))
        
        # 按相似度降序排序并限制结果数量
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:max_results]


    def compute_function_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """
        计算两个函数的整体相似度
        
        Args:
            func1: 第一个函数
            func2: 第二个函数
            
        Returns:
            相似度分数 (0.0 到 1.0)
        """
        similarities = {
            'name': self._compute_name_similarity(func1.name, func2.name),
            'return_type': self._compute_type_similarity(func1.return_type, func2.return_type),
            'param_types': self._compute_param_types_similarity(func1, func2),
            'param_count': self._compute_param_count_similarity(func1, func2)
        }
        
        # 加权平均
        total_similarity = sum(similarities[key] * self.weights[key] for key in similarities)
        
        return total_similarity


    def _compute_name_similarity(self, name1: str, name2: str) -> float:
        """
        计算函数名相似度
        """
        # 分词处理
        tokens1 = set(self._tokenize_name(name1))
        tokens2 = set(self._tokenize_name(name2))
    
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
            
        # Jaccard相似度
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # 字符串相似度作为补充
        string_similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        
        # 组合两种度量
        return 0.7 * jaccard_similarity + 0.3 * string_similarity


    def _tokenize_name(self, name: str) -> List[str]:
        """
        将函数名分解为语义组件
        """
        # 分割camelCase和snake_case
        tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+', name)
        return [token.lower() for token in tokens if token]


    def _compute_type_similarity(self, type1: str, type2: str) -> float:
        """
        计算类型相似度
        """
        # 标准化类型
        norm_type1 = self._normalize_type(type1)
        norm_type2 = self._normalize_type(type2)
        
        if norm_type1 == norm_type2:
            return 1.0
        elif self._are_compatible_types(norm_type1, norm_type2):
            return 0.8
        elif self._are_similar_types(norm_type1, norm_type2):
            return 0.6
        else:
            # 字符串相似度用于未知类型
            return SequenceMatcher(None, norm_type1, norm_type2).ratio()


    def _normalize_type(self, type_str: str) -> str:
        """
        标准化类型字符串用于比较
        """
        # 移除空白和常见修饰符
        normalized = re.sub(r'\s+', '', type_str.lower())
        normalized = re.sub(r'\b(const|static|extern|inline)\b', '', normalized)
        normalized = re.sub(r'\*+', '*', normalized)  # 标准化指针级别
        return normalized.strip()


    def _are_compatible_types(self, type1: str, type2: str) -> bool:
        """
        检查两个类型是否兼容 (例如 int 和 long)
        """
        integer_types = {'int', 'long', 'short', 'char', 'int32_t', 'int64_t', 'size_t'}
        float_types = {'float', 'double', 'long double'}
        pointer_types = {'void*', 'char*', 'const char*'}
        
        # 移除指针标识符进行基础类型比较
        base_type1 = re.sub(r'\*+', '', type1)
        base_type2 = re.sub(r'\*+', '', type2)
        
        return ((base_type1 in integer_types and base_type2 in integer_types) or
                (base_type1 in float_types and base_type2 in float_types) or
                (type1 in pointer_types and type2 in pointer_types))


    def _are_similar_types(self, type1: str, type2: str) -> bool:
        """
        检查两个类型是否语义相似
        """
        # 都是指针
        if '*' in type1 and '*' in type2:
            return True
        # 都是数组
        if '[' in type1 and '[' in type2:
            return True
        # 都是函数指针
        if '(' in type1 and ')' in type1 and '(' in type2 and ')' in type2:
            return True
        return False


    def _compute_param_types_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """
        计算参数类型列表的相似度
        """
        types1 = func1.parameters
        types2 = func2.parameters
        
        if not types1 and not types2:
            return 1.0
        if not types1 or not types2:
            return 0.0
            
        max_len = max(len(types1), len(types2))
        min_len = min(len(types1), len(types2))
        
        # 计算成对相似度
        similarities = []
        for i in range(min_len):
            sim = self._compute_type_similarity(types1[i], types2[i])
            similarities.append(sim)
            
        # 平均相似度，带长度差异惩罚
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        length_penalty = min_len / max_len
        
        return avg_similarity * length_penalty


    def _compute_param_count_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """
        基于参数数量计算相似度
        """
        count1 = len(func1.parameters)
        count2 = len(func2.parameters)
        
        if count1 == count2:
            return 1.0
        elif abs(count1 - count2) == 1:
            return 0.8
        elif abs(count1 - count2) == 2:
            return 0.6
        else:
            # 对于更大的差异使用指数衰减
            return math.exp(-0.5 * abs(count1 - count2))


# 为了向后兼容，提供函数式接口
def find_most_similar_apis(target_function: FunctionInfo, 
                          all_functions: List[FunctionInfo],
                          similarity_threshold: float = 0.2,
                          max_results: int = 5) -> List[Tuple[FunctionInfo, float]]:
    """
    向后兼容的函数式接口
    
    Args:
        target_function: 目标函数的FunctionInfo对象
        all_functions: 所有函数的FunctionInfo对象列表
        similarity_threshold: 最小相似度阈值
        max_results: 返回的最大结果数量
        
    Returns:
        List of (FunctionInfo, similarity_score) tuples, 按相似度降序排列
    """
    analyzer = APISimilarityAnalyzer(similarity_threshold)
    return analyzer.find_most_similar_apis(target_function, all_functions, 
                                         similarity_threshold, max_results)