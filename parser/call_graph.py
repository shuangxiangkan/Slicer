#!/usr/bin/env python3
"""
Call Graph分析器 - 分析函数调用关系和依赖
"""

from typing import Dict, List, Set
from collections import defaultdict, deque
import logging

logger = logging.getLogger(__name__)


class CallGraph:
    """Call Graph分析器"""
    
    def __init__(self):
        # 函数名到FunctionInfo的映射
        self.functions = {}  # Dict[str, FunctionInfo]
        
        # 调用关系图：caller -> set of callees
        self.call_graph = defaultdict(set)
        
        # 反向调用关系图：callee -> set of callers
        self.reverse_call_graph = defaultdict(set)
        
        # 是否已构建图
        self._graph_built = False
    
    def add_function(self, func_info):
        """添加函数信息"""
        # 如果已有同名函数，优先保留函数定义而非声明
        if func_info.name in self.functions:
            existing_func = self.functions[func_info.name]
            # 如果新函数是定义，或者已有函数是声明，则替换
            if not func_info.is_declaration or existing_func.is_declaration:
                self.functions[func_info.name] = func_info
        else:
            self.functions[func_info.name] = func_info
        self._graph_built = False
    
    def build_graph(self):
        """构建call graph"""
        if self._graph_built:
            return
        
        logger.info(f"开始构建Call Graph，包含 {len(self.functions)} 个函数")
        
        # 清空现有图
        self.call_graph.clear()
        self.reverse_call_graph.clear()
        
        # 为每个函数解析调用关系
        for func_name, func_info in self.functions.items():
            if not func_info.is_declaration:  # 只处理函数定义
                # 强制重新解析函数调用
                func_info.clear_call_cache()
                func_info.parse_function_calls()
                
                # 构建调用关系
                callees = func_info.get_callees()
                logger.debug(f"函数 {func_name} 调用: {callees}")
                
                for callee in callees:
                    self.call_graph[func_name].add(callee)
                    self.reverse_call_graph[callee].add(func_name)
        
        self._graph_built = True
        logger.info(f"Call Graph构建完成")
    
    def get_direct_callees(self, func_name: str) -> Set[str]:
        """获取直接调用的函数"""
        if not self._graph_built:
            self.build_graph()
        return self.call_graph.get(func_name, set()).copy()
    
    def get_direct_callers(self, func_name: str) -> Set[str]:
        """获取直接调用该函数的函数"""
        if not self._graph_built:
            self.build_graph()
        return self.reverse_call_graph.get(func_name, set()).copy()
    
    def get_all_dependencies(self, func_name: str, max_depth: int = None) -> Dict[str, int]:
        """
        获取函数的所有依赖（递归）
        
        Args:
            func_name: 函数名
            max_depth: 最大递归深度，None表示无限制
            
        Returns:
            依赖函数名到深度的映射
        """
        if not self._graph_built:
            self.build_graph()
        
        if func_name not in self.functions:
            return {}
        
        dependencies = {}  # func_name -> depth
        visited = set()
        queue = deque([(func_name, 0)])  # (func_name, depth)
        
        while queue:
            current_func, depth = queue.popleft()
            
            if current_func in visited:
                continue
            
            visited.add(current_func)
            
            # 获取直接调用的函数
            callees = self.get_direct_callees(current_func)
            
            for callee in callees:
                if callee not in visited:
                    new_depth = depth + 1
                    
                    # 检查深度限制
                    if max_depth is None or new_depth <= max_depth:
                        # 只记录真实存在的函数
                        if callee in self.functions:
                            if callee not in dependencies or dependencies[callee] > new_depth:
                                dependencies[callee] = new_depth
                            queue.append((callee, new_depth))
                        else:
                            # 记录外部函数（不在当前分析范围内的函数）
                            if callee not in dependencies or dependencies[callee] > new_depth:
                                dependencies[callee] = new_depth
        
        # 移除起始函数自己
        dependencies.pop(func_name, None)
        
        return dependencies
    
    def get_all_dependents(self, func_name: str, max_depth: int = None) -> Dict[str, int]:
        """
        获取依赖该函数的所有函数（递归）
        
        Args:
            func_name: 函数名
            max_depth: 最大递归深度，None表示无限制
            
        Returns:
            依赖该函数的函数名到深度的映射
        """
        if not self._graph_built:
            self.build_graph()
        
        if func_name not in self.functions:
            return {}
        
        dependents = {}  # func_name -> depth
        visited = set()
        queue = deque([(func_name, 0)])  # (func_name, depth)
        
        while queue:
            current_func, depth = queue.popleft()
            
            if current_func in visited:
                continue
            
            visited.add(current_func)
            
            # 获取直接调用该函数的函数
            callers = self.get_direct_callers(current_func)
            
            for caller in callers:
                if caller not in visited:
                    new_depth = depth + 1
                    
                    # 检查深度限制
                    if max_depth is None or new_depth <= max_depth:
                        if caller in self.functions:
                            if caller not in dependents or dependents[caller] > new_depth:
                                dependents[caller] = new_depth
                            queue.append((caller, new_depth))
        
        # 移除起始函数自己
        dependents.pop(func_name, None)
        
        return dependents
    
    def find_cycles(self) -> List[List[str]]:
        """查找循环依赖"""
        if not self._graph_built:
            self.build_graph()
        
        cycles = []
        visited = set()
        path = []
        path_set = set()
        
        def dfs(node):
            if node in path_set:
                # 找到循环
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return
            
            if node in visited:
                return
            
            visited.add(node)
            path.append(node)
            path_set.add(node)
            
            for neighbor in self.call_graph.get(node, []):
                if neighbor in self.functions:  # 只处理存在的函数
                    dfs(neighbor)
            
            path.pop()
            path_set.remove(node)
        
        # 对所有函数进行DFS
        for func_name in self.functions:
            if func_name not in visited:
                dfs(func_name)
        
        return cycles
    
    def get_function_complexity_stats(self) -> Dict[str, Dict]:
        """获取函数复杂度统计"""
        if not self._graph_built:
            self.build_graph()
        
        stats = {}
        
        for func_name in self.functions:
            direct_callees = len(self.get_direct_callees(func_name))
            direct_callers = len(self.get_direct_callers(func_name))
            all_dependencies = len(self.get_all_dependencies(func_name))
            all_dependents = len(self.get_all_dependents(func_name))
            
            stats[func_name] = {
                'direct_callees': direct_callees,
                'direct_callers': direct_callers,
                'all_dependencies': all_dependencies,
                'all_dependents': all_dependents,
                'complexity_score': direct_callees + direct_callers + all_dependencies * 0.1 + all_dependents * 0.1
            }
        
        return stats
    
    def get_call_chain(self, from_func: str, to_func: str, max_depth: int = 10) -> List[List[str]]:
        """
        查找从一个函数到另一个函数的调用链
        
        Args:
            from_func: 起始函数
            to_func: 目标函数
            max_depth: 最大搜索深度
            
        Returns:
            调用链列表，每个调用链是函数名的列表
        """
        if not self._graph_built:
            self.build_graph()
        
        if from_func not in self.functions or to_func not in self.functions:
            return []
        
        chains = []
        
        def dfs(current_path, visited, depth):
            if depth > max_depth:
                return
            
            current_func = current_path[-1]
            
            if current_func == to_func and len(current_path) > 1:
                chains.append(current_path.copy())
                return
            
            if current_func in visited:
                return
            
            visited.add(current_func)
            
            for callee in self.get_direct_callees(current_func):
                if callee in self.functions:
                    current_path.append(callee)
                    dfs(current_path, visited.copy(), depth + 1)
                    current_path.pop()
        
        dfs([from_func], set(), 0)
        return chains
    
    def get_external_dependencies(self) -> Set[str]:
        """获取外部依赖（不在当前分析范围内的函数）"""
        if not self._graph_built:
            self.build_graph()
        
        external_deps = set()
        
        for func_callees in self.call_graph.values():
            for callee in func_callees:
                if callee not in self.functions:
                    external_deps.add(callee)
        
        return external_deps
    
    def get_graph_summary(self) -> Dict:
        """获取Call Graph摘要信息"""
        if not self._graph_built:
            self.build_graph()
        
        total_functions = len(self.functions)
        total_edges = sum(len(callees) for callees in self.call_graph.values())
        external_deps = len(self.get_external_dependencies())
        cycles = self.find_cycles()
        
        # 统计函数类型
        leaf_functions = []  # 叶子函数（不调用其他函数）
        root_functions = []  # 根函数（不被其他函数调用）
        
        for func_name in self.functions:
            if not self.get_direct_callees(func_name):
                leaf_functions.append(func_name)
            if not self.get_direct_callers(func_name):
                root_functions.append(func_name)
        
        return {
            'total_functions': total_functions,
            'total_call_edges': total_edges,
            'external_dependencies': external_deps,
            'cycles_count': len(cycles),
            'cycles': cycles,
            'leaf_functions_count': len(leaf_functions),
            'root_functions_count': len(root_functions),
            'leaf_functions': leaf_functions,
            'root_functions': root_functions,
            'avg_callees_per_function': total_edges / total_functions if total_functions > 0 else 0
        } 