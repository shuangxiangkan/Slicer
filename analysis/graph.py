#!/usr/bin/env python3
"""
图数据结构模块

提供图的基础数据结构和操作
"""

from typing import List, Dict, Set
from enum import Enum
from .node import Node


class EdgeType(Enum):
    """边类型枚举"""
    CFG = "CFG"  # 控制流图边
    DDG = "DDG"  # 数据依赖图边
    CDG = "CDG"  # 控制依赖图边
    PDG = "PDG"  # 程序依赖图边


class Edge:
    """图的边基类"""
    
    def __init__(self, label: str = '', edge_type: EdgeType = EdgeType.CFG, 
                 source_node: Node = None, target_node: Node = None):
        """
        创建边
        Args:
            label: 边的标签
            edge_type: 边的类型
            source_node: 源节点对象 
            target_node: 目标节点对象
        """
        self.source_node = source_node
        self.target_node = target_node
        self.label = label
        self.type = edge_type
    
    @property
    def source(self):
        """获取源节点对象"""
        return self.source_node
    
    @property
    def target(self):
        """获取目标节点对象"""
        return self.target_node


class DDGEdge(Edge):
    """数据依赖图边，包含变量信息"""
    
    def __init__(self, label: str = '', variables: List[str] = None,
                 source_node: Node = None, target_node: Node = None):
        """
        创建DDG边
        Args:
            label: 边的标签
            variables: 依赖的变量列表
            source_node: 源节点对象
            target_node: 目标节点对象
        """
        super().__init__(label, EdgeType.DDG, source_node, target_node)
        self.variables = variables or []  # 依赖的变量列表
        
        # 为了保持向后兼容性，保留token属性
        self.token = self.variables

class Graph:
    """程序分析图"""
    
    def __init__(self):
        """初始化图"""
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []
        self.id_to_nodes: Dict[int, Node] = {}
        self.defs: Dict[int, Set[str]] = {}  # 节点ID -> 定义的变量集合
        self.uses: Dict[int, Set[str]] = {}  # 节点ID -> 使用的变量集合
    
    def add_node(self, node: Node):
        """添加节点"""
        if node.id not in self.id_to_nodes:
            self.nodes.append(node)
            self.id_to_nodes[node.id] = node
            self.defs[node.id] = node.defs
            self.uses[node.id] = node.uses
    
    def add_edge(self, edge_info):
        """添加边"""
        if isinstance(edge_info, tuple) and len(edge_info) == 2:
            # (source_node, target_edge)格式
            source_node, target_edge = edge_info
            if isinstance(source_node, Node):
                self.add_node(source_node)
                
                # 处理边列表或单个边
                edges_to_add = target_edge if isinstance(target_edge, list) else [target_edge]
                
                for edge in edges_to_add:
                    # 如果边还没有设置source_node，自动设置
                    if edge.source_node is None:
                        edge.source_node = source_node
                    # 添加目标节点
                    if edge.target_node:
                        self.add_node(edge.target_node)
                
                self.edges.extend(edges_to_add)
    
    def get_node_by_id(self, node_id: int) -> Node:
        """通过ID获取节点，调试时使用"""
        return self.id_to_nodes.get(node_id)
    
    def __getitem__(self, node_id: int) -> Node:
        """支持通过graph[id]的方式获取节点，方便调试"""
        node = self.id_to_nodes.get(node_id)
        if node is None:
            raise KeyError(f"Node with id {node_id} not found")
        return node
    
    def get_incoming_edges_for_node(self, node_id: int) -> List[Edge]:
        """获取指定节点的入边"""
        incoming_edges = []
        for edge in self.edges:
            if edge.target_node and edge.target_node.id == node_id:
                incoming_edges.append(edge)
        return incoming_edges
    
    def get_outgoing_edges_for_node(self, node_id: int) -> List[Edge]:
        """获取指定节点的出边"""
        outgoing_edges = []
        for edge in self.edges:
            if edge.source_node and edge.source_node.id == node_id:
                outgoing_edges.append(edge)
        return outgoing_edges
    
    def get_def_use_info(self):
        """更新定义-使用信息"""
        for node in self.nodes:
            self.defs[node.id] = node.defs
            self.uses[node.id] = node.uses
    
    def reverse(self):
        """返回反向图"""
        reversed_graph = Graph()
        
        # 复制所有节点
        for node in self.nodes:
            reversed_graph.add_node(node)
        
        # 反向所有边
        for edge in self.edges:
            if edge.target_node:
                # 根据边的类型创建相应的反向边，交换source和target
                if isinstance(edge, DDGEdge):
                    reversed_edge = DDGEdge(
                        label=edge.label, 
                        variables=edge.variables,
                        source_node=edge.target_node,  # 交换
                        target_node=edge.source_node   # 交换
                    )
                else:
                    reversed_edge = Edge(
                        label=edge.label, 
                        edge_type=edge.type,
                        source_node=edge.target_node,  # 交换
                        target_node=edge.source_node   # 交换
                    )
                    # 为了向后兼容，如果原边有token属性，也复制过来
                    if hasattr(edge, 'token'):
                        reversed_edge.token = edge.token
                
                # 添加到反向图中
                reversed_graph.edges.append(reversed_edge)
        
        return reversed_graph
    
    def get_outgoing_edges(self):
        """获取出边结构：node_id -> [target_node_ids]"""
        outgoing = {}
        for edge in self.edges:
            if edge.source_node and edge.target_node:
                source_id = edge.source_node.id
                target_id = edge.target_node.id
                if source_id not in outgoing:
                    outgoing[source_id] = []
                outgoing[source_id].append(target_id)
        return outgoing
    
    def hasPathAvoidingNodes(self, start, end, avoid_nodes):
        """
        检查从start到end是否存在一条路径，该路径不经过avoid_nodes中的任何节点
        
        使用BFS实现，比DFS更快找到路径（如果存在）
        
        Args:
            start: 起始节点ID
            end: 终止节点ID
            avoid_nodes: 要避开的节点ID集合
            
        Returns:
            bool: 是否存在满足条件的路径
        """
        if start == end:
            return True
        
        if start in avoid_nodes or end in avoid_nodes:
            return False
        
        # 获取出边结构
        outgoing_edges = self.get_outgoing_edges()
        
        # BFS搜索
        from collections import deque
        queue = deque([start])
        visited = set([start])
        
        while queue:
            current = queue.popleft()
            
            # 遍历邻接节点
            for next_node in outgoing_edges.get(current, []):
                if next_node == end:
                    return True  # 找到路径
                
                if next_node not in visited and next_node not in avoid_nodes:
                    visited.add(next_node)
                    queue.append(next_node)
        
        return False
    
    def findAllPath(self, start, end):
        """
        找到从start到end的所有路径
        算法参考：https://zhuanlan.zhihu.com/p/84437102
        
        注意：此方法性能较差（指数级复杂度O(2^n)），仅在需要所有路径时使用
        如果只需要判断是否存在路径，请使用hasPathAvoidingNodes()（BFS实现，性能更好）
        """
        if start == end:
            return []
            
        # 获取出边结构
        outgoing_edges = self.get_outgoing_edges()
        
        def get_adj(node_id):
            """获取节点的邻接节点"""
            return outgoing_edges.get(node_id, [])
        
        paths, s1, s2 = [], [], []  # 存放所有路径，主栈，辅助栈
        s1.append(start)    
        s2.append(get_adj(start))
        
        while s1:   # 主栈不为空
            s2_top = s2[-1]
            if s2_top:  # 邻接节点列表不为空
                s1.append(s2_top[0])    # 将邻接节点列表首个元素添加到主栈
                s2[-1] = s2_top[1:]     # 将辅助栈的邻接节点列表首个元素删除
                temp = []               # 建栈，需要判断邻接节点是否在主栈中
                for each in get_adj(s2_top[0]):
                    if each not in s1:
                        temp.append(each)
                s2.append(temp)
            else:   # 削栈
                s1.pop()
                s2.pop()
                continue
            if s1[-1] == end:   # 找到一条路径
                paths.append(s1.copy())
                s1.pop()    # 回溯
                s2.pop()
        return paths