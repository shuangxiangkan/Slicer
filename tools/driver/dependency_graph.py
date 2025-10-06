#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的API依赖图生成器

基于简单节点结构的依赖图，每个节点只包含：
1. API名字
2. category类型  
3. 和哪个已有harness的API的相似度最高，以及具体的相似度
"""

import json
import os
import re
import math
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from difflib import SequenceMatcher
import networkx as nx
import graphviz
from log import log_info, log_success, log_warning, log_error

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


class APINode:
    """简化的API节点，只包含核心信息"""
    
    def __init__(self, name: str, category: str):
        self.name = name                    # API名字
        self.category = category            # category类型 (fuzz/test_demo/other_usage/no_usage)
        self.best_reference = None          # 最相似的已有harness API名字
        self.similarity_score = 0.0         # 与最相似API的相似度分数
    
    def set_reference(self, reference_api: str, similarity: float):
        """设置最相似的参考API"""
        self.best_reference = reference_api
        self.similarity_score = similarity
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'name': self.name,
            'category': self.category,
            'best_reference': self.best_reference,
            'similarity_score': self.similarity_score
        }

class APISimilarityDependencyGraph:
    """简化的API依赖图，基于简单节点结构"""
    
    def __init__(self):
        """初始化简化的API依赖图"""
        self.nodes: Dict[str, APINode] = {}     # API节点字典
        self.generation_order: List[str] = []   # API生成顺序
        self.api_functions = []                 # API函数列表，用于按需计算相似度
        self.similarity_analyzer = APISimilarityAnalyzer(similarity_threshold=0.1)  # 相似度分析器
        
    def build_generation_order(self, 
                             api_functions: List[Any],
                             api_categories: Dict[str, Any],
                             usage_results: Dict[str, Any]) -> bool:
        """
        构建API生成顺序
        
        Args:
            api_functions: API函数列表
            api_categories: API分类信息
            usage_results: API使用情况结果
            
        Returns:
            bool: 构建是否成功
        """
        try:
            log_info("开始构建简化的API依赖图...")
            
            # 保存API函数列表，用于按需计算相似度
            self.api_functions = api_functions
            
            # 1. 创建API节点
            self._create_api_nodes(api_functions, api_categories, usage_results)
            
            # 2. 构建生成顺序（按需计算相似度）
            self._build_generation_order()
            
            log_success(f"API依赖图构建完成，总共 {len(self.generation_order)} 个API")
            return True
            
        except Exception as e:
            log_error(f"构建API依赖图时发生错误: {str(e)}")
            return False
    
    def _create_api_nodes(self, api_functions: List[Any], 
                         api_categories: Dict[str, Any], 
                         usage_results: Dict[str, Any]):
        """创建API节点"""
        log_info("创建API节点...")
        
        # 为每个API创建节点
        for api_func in api_functions:
            api_name = api_func.name
            
            # 确定API的category
            category = self._get_api_category(api_name, api_categories)
            
            # 创建节点
            node = APINode(api_name, category)
            self.nodes[api_name] = node
            
            log_info(f"创建节点: {api_name} (category: {category})")
    
    def _get_api_category(self, api_name: str, api_categories: Dict[str, Any]) -> str:
        """获取API的category类型"""
        for category, api_list in api_categories.items():
            if api_name in api_list:
                if category == 'with_fuzz':
                    return 'fuzz'
                elif category == 'with_test_demo':
                    return 'test_demo'
                elif category == 'with_other_usage':
                    return 'other_usage'
                else:
                    return 'no_usage'
        return 'no_usage'
    
    def _build_generation_order(self):
        """构建API harness生成顺序
        算法：A=[基础APIs], B=[非基础API], 从B中找到与A中相似度最高的API，加入A，直到所有API都在A中
        """
        log_info("构建API生成顺序...")
        
        # 1. 首先添加基础API，按优先级顺序：fuzz > test_demo
        base_apis = []
        
        # 先添加fuzz类别的API
        fuzz_apis = []
        for node in self.nodes.values():
            if node.category == 'fuzz':
                fuzz_apis.append(node.name)
        base_apis.extend(fuzz_apis)
        
        # 再添加test_demo类别的API
        test_demo_apis = []
        for node in self.nodes.values():
            if node.category == 'test_demo':
                test_demo_apis.append(node.name)
        base_apis.extend(test_demo_apis)
        
        # 基础API已有足够信息生成harness，无需设置相似度参考
        self.generation_order.extend(base_apis)
        log_info(f"添加 {len(fuzz_apis)} 个fuzz API，{len(test_demo_apis)} 个test_demo API，总共 {len(base_apis)} 个基础API")
        
        # 2. 然后按相似度逐步添加其他API
        remaining_apis = [name for name in self.nodes.keys() if name not in base_apis]
        
        while remaining_apis:
            # 找到与已有API最相似的API
            best_api = self._find_most_similar_api_on_demand(remaining_apis)
            
            if best_api:
                self.generation_order.append(best_api)
                remaining_apis.remove(best_api)
                log_info(f"添加API: {best_api} (相似度: {self.nodes[best_api].similarity_score:.3f}, 参考: {self.nodes[best_api].best_reference})")
            else:
                # 没有找到相似的API，按优先级顺序添加剩余API
                log_info("没有找到相似API，按优先级顺序添加剩余API...")
                
                # 按优先级排序剩余API：other_usage > no_usage
                other_usage_apis = []
                no_usage_apis = []
                
                for api_name in remaining_apis:
                    node = self.nodes[api_name]
                    if node.category == 'other_usage':
                        other_usage_apis.append(api_name)
                    elif node.category == 'no_usage':
                        no_usage_apis.append(api_name)
                
                # 按优先级顺序添加
                prioritized_remaining = other_usage_apis + no_usage_apis
                self.generation_order.extend(prioritized_remaining)
                log_info(f"按优先级添加: {len(other_usage_apis)} 个other_usage API, {len(no_usage_apis)} 个no_usage API")
                break
    
    def _find_most_similar_api_on_demand(self, candidate_apis: List[str]) -> Optional[str]:
        """在候选API中找到与已有API最相似的一个（按需计算相似度）"""
        best_api = None
        max_similarity = 0.0
        best_reference = None
        
        # 遍历每个候选API，计算与generation_order中所有API的相似度
        for candidate_api in candidate_apis:
            # 获取候选API的函数信息
            candidate_func = None
            for func in self.api_functions:
                if func.name == candidate_api:
                    candidate_func = func
                    break
                    
            if not candidate_func:
                continue
                
            # 计算与generation_order中每个API的相似度
            for existing_api in self.generation_order:
                # 获取已有API的函数信息
                existing_func = None
                for func in self.api_functions:
                    if func.name == existing_api:
                        existing_func = func
                        break
                        
                if not existing_func:
                    continue
                    
                try:
                    # 计算相似度
                    similarity_score = self.similarity_analyzer.compute_function_similarity(candidate_func, existing_func)
                    
                    # 更新最佳匹配
                    if similarity_score > max_similarity:
                        max_similarity = similarity_score
                        best_api = candidate_api
                        best_reference = existing_api
                        
                except Exception as e:
                    log_warning(f"计算 {candidate_api} 与 {existing_api} 相似度时出错: {str(e)}")
                    continue
        
        # 设置最佳参考（只有当相似度大于阈值时才设置）
        if best_api and best_reference and max_similarity > 0.1:  # 使用相似度阈值
            self.nodes[best_api].set_reference(best_reference, max_similarity)
            return best_api
        
        return None
    
    def get_generation_order(self) -> List[str]:
        """获取API生成顺序"""
        return self.generation_order.copy()
    
    def get_node(self, api_name: str) -> Optional[APINode]:
        """获取API节点"""
        return self.nodes.get(api_name)
    
    def save_generation_order(self, output_file: str):
        """保存生成顺序到文件"""
        try:
            # 构建完整的输出数据
            nodes_data = {}
            edges_data = []
            
            for name, node in self.nodes.items():
                nodes_data[name] = node.to_dict()
                
                # 如果有参考API，添加边信息
                if node.best_reference:
                    edges_data.append({
                        'from': node.best_reference,
                        'to': name,
                        'similarity': node.similarity_score,
                        'type': 'similarity_reference'
                    })
            
            # 构建依赖关系边（基于生成顺序）
            dependency_edges = []
            for i in range(len(self.generation_order) - 1):
                current_api = self.generation_order[i]
                next_api = self.generation_order[i + 1]
                dependency_edges.append({
                    'from': current_api,
                    'to': next_api,
                    'type': 'generation_dependency',
                    'order': i
                })
            
            data = {
                'metadata': {
                    'generated_at': datetime.now().isoformat(),
                    'total_apis': len(self.generation_order),
                    'total_nodes': len(self.nodes),
                    'total_similarity_edges': len(edges_data),
                    'total_dependency_edges': len(dependency_edges)
                },
                'generation_order': self.generation_order,
                'nodes': nodes_data,
                'similarity_edges': edges_data,
                'dependency_edges': dependency_edges,
                'summary': self._get_summary()
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            log_success(f"API依赖图已保存到: {output_file}")
            
        except Exception as e:
            log_error(f"保存依赖图时发生错误: {str(e)}")
    
    def save_dependency_graph_pdf(self, output_file: str):
        """生成并保存依赖图的PDF可视化"""
        try:
            log_info("开始生成依赖图PDF...")
            
            # 创建有向图
            G = nx.DiGraph()
            
            # 添加节点
            for name, node in self.nodes.items():
                # 根据category设置节点颜色
                color_map = {
                    'fuzz': '#FF6B6B',      # 红色 - 高优先级
                    'test_demo': '#4ECDC4', # 青色 - 中高优先级
                    'other_usage': '#45B7D1', # 蓝色 - 中优先级
                    'no_usage': '#96CEB4'   # 绿色 - 低优先级
                }
                
                G.add_node(name, 
                          category=node.category,
                          color=color_map.get(node.category, '#CCCCCC'),
                          similarity_score=node.similarity_score,
                          best_reference=node.best_reference or '')
            
            # 添加相似度参考边
            for name, node in self.nodes.items():
                if node.best_reference and node.best_reference in self.nodes:
                    G.add_edge(node.best_reference, name, 
                             edge_type='similarity',
                             weight=node.similarity_score,
                             color='blue')
            
            # 添加生成顺序边
            for i in range(len(self.generation_order) - 1):
                current_api = self.generation_order[i]
                next_api = self.generation_order[i + 1]
                if current_api in G.nodes and next_api in G.nodes:
                    G.add_edge(current_api, next_api,
                             edge_type='generation',
                             order=i,
                             color='red')
            
            # 使用Graphviz生成PDF
            self._generate_graphviz_pdf(G, output_file)
            
            log_success(f"依赖图PDF已保存到: {output_file}")
            
        except Exception as e:
            log_error(f"生成依赖图PDF时发生错误: {str(e)}")
    
    def _generate_graphviz_pdf(self, graph: nx.DiGraph, output_file: str):
        """使用Graphviz生成PDF"""
        # 创建Graphviz图
        dot = graphviz.Digraph(comment='API Dependency Graph')
        dot.attr(rankdir='TB', size='11,8', dpi='300')
        dot.attr('node', shape='box', style='rounded,filled', fontname='Arial')
        dot.attr('edge', fontname='Arial', fontsize='10')
        
        # 添加图例
        with dot.subgraph(name='cluster_legend') as legend:
            legend.attr(label='图例', style='filled', color='lightgrey')
            legend.node('legend_fuzz', 'Fuzz APIs', fillcolor='#FF6B6B')
            legend.node('legend_test', 'Test Demo APIs', fillcolor='#4ECDC4')
            legend.node('legend_other', 'Other Usage APIs', fillcolor='#45B7D1')
            legend.node('legend_no', 'No Usage APIs', fillcolor='#96CEB4')
        
        # 按category分组添加节点
        categories = {}
        for node_name in graph.nodes():
            node_data = graph.nodes[node_name]
            category = node_data['category']
            if category not in categories:
                categories[category] = []
            categories[category].append(node_name)
        
        # 为每个category创建子图
        for category, nodes in categories.items():
            with dot.subgraph(name=f'cluster_{category}') as subgraph:
                subgraph.attr(label=f'{category.upper()} APIs', 
                            style='filled', 
                            color='lightblue')
                
                for node_name in nodes:
                    node_data = graph.nodes[node_name]
                    
                    # 创建节点标签
                    label = f"{node_name}"
                    if node_data['best_reference']:
                        label += f"\\n→ {node_data['best_reference']}"
                        label += f"\\n相似度: {node_data['similarity_score']:.3f}"
                    
                    subgraph.node(node_name, 
                                label=label,
                                fillcolor=node_data['color'],
                                fontsize='10')
        
        # 添加边
        for edge in graph.edges(data=True):
            source, target, data = edge
            
            if data['edge_type'] == 'similarity':
                # 相似度边 - 蓝色虚线
                dot.edge(source, target,
                        label=f"相似度: {data['weight']:.3f}",
                        color='blue',
                        style='dashed',
                        fontcolor='blue')
            elif data['edge_type'] == 'generation':
                # 生成顺序边 - 红色实线
                dot.edge(source, target,
                        label=f"顺序: {data['order']}",
                        color='red',
                        style='solid',
                        fontcolor='red')
        
        # 保存PDF
        output_path = output_file.replace('.pdf', '')
        try:
            dot.render(output_path, format='pdf', cleanup=True)
            # 手动清理可能残留的中间文件
            intermediate_file = output_path
            if os.path.exists(intermediate_file):
                os.remove(intermediate_file)
                log_info(f"已清理中间文件: {intermediate_file}")
        except Exception as e:
            log_warning(f"清理中间文件时出现警告: {str(e)}")
            # 即使清理失败，也不影响主要功能
    
    def save_complete_output(self, output_dir: str):
        """保存完整的输出：JSON文件和PDF图形"""
        try:
            # 确保输出目录存在
            os.makedirs(output_dir, exist_ok=True)
            
            # 使用固定文件名（不带时间戳）
            json_file = os.path.join(output_dir, "dependency_graph.json")
            pdf_file = os.path.join(output_dir, "dependency_graph.pdf")
            
            # 保存JSON文件
            self.save_generation_order(json_file)
            
            # 保存PDF图形
            self.save_dependency_graph_pdf(pdf_file)
            
            # 打印摘要
            self.print_generation_summary()
            
            log_success(f"完整输出已保存到目录: {output_dir}")
            log_info(f"JSON文件: {json_file}")
            log_info(f"PDF文件: {pdf_file}")
            
            return {
                'json_file': json_file,
                'pdf_file': pdf_file,
                'output_dir': output_dir
            }
            
        except Exception as e:
            log_error(f"保存完整输出时发生错误: {str(e)}")
            return None
    
    def _get_summary(self) -> Dict[str, Any]:
        """获取依赖图摘要"""
        category_counts = {}
        reference_counts = {'with_reference': 0, 'without_reference': 0}
        
        for node in self.nodes.values():
            # 统计category
            category_counts[node.category] = category_counts.get(node.category, 0) + 1
            
            # 统计参考情况
            if node.best_reference:
                reference_counts['with_reference'] += 1
            else:
                reference_counts['without_reference'] += 1
        
        return {
            'category_distribution': category_counts,
            'reference_distribution': reference_counts
        }
    
    def print_generation_summary(self):
        """打印生成顺序摘要"""
        log_info("=== 简化API依赖图摘要 ===")
        log_info(f"总API数量: {len(self.generation_order)}")
        
        # 统计各类别API数量
        summary = self._get_summary()
        log_info(f"API分类统计: {summary['category_distribution']}")
        log_info(f"参考情况统计: {summary['reference_distribution']}")
        
        # 显示前10个API的详细信息
        log_info("前10个API详细信息:")
        for i, api_name in enumerate(self.generation_order[:10]):
            node = self.nodes[api_name]
            ref_str = f" -> {node.best_reference} (相似度: {node.similarity_score:.3f})" if node.best_reference else " (基础API)"
            log_info(f"  {i}: {api_name} [{node.category}]{ref_str}")
        
        if len(self.generation_order) > 10:
            log_info(f"  ... 还有 {len(self.generation_order) - 10} 个API")
    
    def save_and_print_summary(self, output_dir: str):
        """保存依赖图并打印摘要"""
        # 使用新的完整输出功能
        result = self.save_complete_output(output_dir)
        
        if result:
            log_info("=== 依赖图输出完成 ===")
            log_info(f"JSON文件: {result['json_file']}")
            log_info(f"PDF文件: {result['pdf_file']}")
        else:
            # 如果完整输出失败，回退到原来的方法
            log_warning("完整输出失败，使用基础保存方法...")
            dependency_graph_file = os.path.join(output_dir, "dependency_graph.json")
            self.save_generation_order(dependency_graph_file)
            self.print_generation_summary()


# 向后兼容性：为 library_handler.py 提供原有的接口
def create_similarity_analyzer(similarity_threshold: float = 0.2) -> APISimilarityAnalyzer:
    """创建相似性分析器实例（向后兼容）"""
    return APISimilarityAnalyzer(similarity_threshold)