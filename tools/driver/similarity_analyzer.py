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

# Add project root to Python path
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from parser.function_info import FunctionInfo


class APISimilarityAnalyzer:
    """
    API similarity analyzer class
    
    Provides complete functionality for computing similarity scores between API functions, including name similarity,
    type similarity, parameter similarity, and multi-dimensional analysis.
    Multi-dimensional analysis of parameter similarity.
    """
    
    def __init__(self, similarity_threshold: float = 0.2):
        """
        Initialize API similarity analyzer
        
        Args:
            similarity_threshold: Default minimum similarity threshold
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
        Find the most similar API function to the target function
        
        Args:
            target_function: FunctionInfo object of the target function
            all_functions: List of FunctionInfo objects of all functions
            similarity_threshold: Minimum similarity threshold, if None then use default value
            max_results: Maximum number of results to return
            
        Returns:
            List of (FunctionInfo, similarity_score) tuples, sorted by similarity score in descending order
        """
        if similarity_threshold is None:
            similarity_threshold = self.similarity_threshold
            
        similarities = []
        
        for func in all_functions:
            # Skip the target function itself
            if func.name == target_function.name:
                continue
                
            similarity = self.compute_function_similarity(target_function, func)
            
            if similarity >= similarity_threshold:
                similarities.append((func, similarity))
        
        # Sort by similarity score in descending order and limit the number of results
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:max_results]


    def compute_function_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """
        Compute the overall similarity of two functions
        
        Args:
            func1: The first function
            func2: The second function
            
        Returns:
            Similarity score (0.0 to 1.0)
        """
        similarities = {
            'name': self._compute_name_similarity(func1.name, func2.name),
            'return_type': self._compute_type_similarity(func1.return_type, func2.return_type),
            'param_types': self._compute_param_types_similarity(func1, func2),
            'param_count': self._compute_param_count_similarity(func1, func2)
        }
        
        # Weighted average
        total_similarity = sum(similarities[key] * self.weights[key] for key in similarities)
        
        return total_similarity


    def _compute_name_similarity(self, name1: str, name2: str) -> float:
        """
        Compute the similarity of function names
        """
        # Tokenization
        tokens1 = set(self._tokenize_name(name1))
        tokens2 = set(self._tokenize_name(name2))
    
        if not tokens1 and not tokens2:
            return 1.0
        if not tokens1 or not tokens2:
            return 0.0
            
        # Jaccard similarity
        intersection = len(tokens1.intersection(tokens2))
        union = len(tokens1.union(tokens2))
        jaccard_similarity = intersection / union if union > 0 else 0.0
        
        # String similarity as a supplement
        string_similarity = SequenceMatcher(None, name1.lower(), name2.lower()).ratio()
        
        # Combine two measures
        return 0.7 * jaccard_similarity + 0.3 * string_similarity


    def _tokenize_name(self, name: str) -> List[str]:
        """
        Decompose the function name into semantic components
        """
        # Split camelCase and snake_case
        tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+', name)
        return [token.lower() for token in tokens if token]


    def _compute_type_similarity(self, type1: str, type2: str) -> float:
        """
        Compute the similarity of types
        """
        # Normalize types
        norm_type1 = self._normalize_type(type1)
        norm_type2 = self._normalize_type(type2)
        
        if norm_type1 == norm_type2:
            return 1.0
        elif self._are_compatible_types(norm_type1, norm_type2):
            return 0.8
        elif self._are_similar_types(norm_type1, norm_type2):
            return 0.6
        else:
            # String similarity for unknown types
            return SequenceMatcher(None, norm_type1, norm_type2).ratio()


    def _normalize_type(self, type_str: str) -> str:
        """
        Normalize the type string for comparison
        """
        # Remove whitespace and common modifiers
        normalized = re.sub(r'\s+', '', type_str.lower())
        normalized = re.sub(r'\b(const|static|extern|inline)\b', '', normalized)
        normalized = re.sub(r'\*+', '*', normalized)  # Normalize pointer levels
        return normalized.strip()


    def _are_compatible_types(self, type1: str, type2: str) -> bool:
        """
        Check if two types are compatible (e.g. int and long)
        """
        integer_types = {'int', 'long', 'short', 'char', 'int32_t', 'int64_t', 'size_t'}
        float_types = {'float', 'double', 'long double'}
        pointer_types = {'void*', 'char*', 'const char*'}
        
        # Remove pointer identifiers for basic type comparison
        base_type1 = re.sub(r'\*+', '', type1)
        base_type2 = re.sub(r'\*+', '', type2)
        
        return ((base_type1 in integer_types and base_type2 in integer_types) or
                (base_type1 in float_types and base_type2 in float_types) or
                (type1 in pointer_types and type2 in pointer_types))


    def _are_similar_types(self, type1: str, type2: str) -> bool:
        """
        Check if two types are semantically similar
        """
        # Both are pointers
        if '*' in type1 and '*' in type2:
            return True
        # Both are arrays
        if '[' in type1 and '[' in type2:
            return True
        # Both are function pointers
        if '(' in type1 and ')' in type1 and '(' in type2 and ')' in type2:
            return True
        return False


    def _compute_param_types_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """
        Compute the similarity of parameter type lists
        """
        types1 = func1.parameters
        types2 = func2.parameters
        
        if not types1 and not types2:
            return 1.0
        if not types1 or not types2:
            return 0.0
            
        max_len = max(len(types1), len(types2))
        min_len = min(len(types1), len(types2))
        
        # Compute pairwise similarity
        similarities = []
        for i in range(min_len):
            sim = self._compute_type_similarity(types1[i], types2[i])
            similarities.append(sim)
            
        # Average similarity, with length difference penalty
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.0
        length_penalty = min_len / max_len
        
        return avg_similarity * length_penalty


    def _compute_param_count_similarity(self, func1: FunctionInfo, func2: FunctionInfo) -> float:
        """
        Compute the similarity based on the number of parameters
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
            # For larger differences, use exponential decay
            return math.exp(-0.5 * abs(count1 - count2))


# For backward compatibility, provide a functional interface
def find_most_similar_apis(target_function: FunctionInfo, 
                          all_functions: List[FunctionInfo],
                          similarity_threshold: float = 0.2,
                          max_results: int = 5) -> List[Tuple[FunctionInfo, float]]:
    """
    Functional interface for backward compatibility
    
    Args:
        target_function: FunctionInfo object of the target function
        all_functions: List of FunctionInfo objects of all functions
        similarity_threshold: Minimum similarity threshold
        max_results: Maximum number of results to return
        
    Returns:
        List of (FunctionInfo, similarity_score) tuples, sorted by similarity score in descending order
    """
    analyzer = APISimilarityAnalyzer(similarity_threshold)
    return analyzer.find_most_similar_apis(target_function, all_functions, 
                                         similarity_threshold, max_results)