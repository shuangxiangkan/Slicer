#!/usr/bin/env python3
"""
图数据结构模块

提供图的基础数据结构和操作
"""

from typing import List, Dict, Set
from .node import Node


class Edge:
    """图的边"""
    
    def __init__(self, target_id: int, label: str = '', edge_type: str = 'CFG'):
        """
        创建边
        Args:
            target_id: 目标节点ID
            label: 边的标签
            edge_type: 边的类型 ('CFG', 'DDG', 'CDG')
        """
        self.id = target_id
        self.label = label
        self.type = edge_type
        self.token = []  # 用于DDG边的变量信息


class Graph:
    """程序分析图"""
    
    def __init__(self):
        """初始化图"""
        self.nodes: List[Node] = []
        self.edges: Dict[int, List[Edge]] = {}
        self.id_to_nodes: Dict[int, Node] = {}
        self.defs: Dict[int, Set[str]] = {}  # 节点ID -> 定义的变量集合
        self.uses: Dict[int, Set[str]] = {}  # 节点ID -> 使用的变量集合
    
    def add_node(self, node: Node):
        """添加节点"""
        if node.id not in self.id_to_nodes:
            self.nodes.append(node)
            self.id_to_nodes[node.id] = node
            self.edges[node.id] = []
            self.defs[node.id] = node.defs
            self.uses[node.id] = node.uses
    
    def add_edge(self, edge_info):
        """添加边"""
        if isinstance(edge_info, tuple) and len(edge_info) == 2:
            # (source_node, target_edge)格式
            source_node, target_edge = edge_info
            if isinstance(source_node, Node):
                self.add_node(source_node)
                if isinstance(target_edge, list):
                    self.edges[source_node.id].extend(target_edge)
                else:
                    self.edges[source_node.id].append(target_edge)
    
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
        for source_id, edges in self.edges.items():
            for edge in edges:
                target_id = edge.id
                # 创建反向边
                reversed_edge = Edge(source_id, edge.label, edge.type)
                reversed_edge.token = edge.token
                
                # 添加到反向图中
                if target_id not in reversed_graph.edges:
                    reversed_graph.edges[target_id] = []
                reversed_graph.edges[target_id].append(reversed_edge)
        
        return reversed_graph
    
    def get_outgoing_edges(self):
        """获取出边结构：node_id -> [target_node_ids]"""
        outgoing = {}
        for target_id, incoming_edges in self.edges.items():
            for edge in incoming_edges:
                source_id = edge.id
                if source_id not in outgoing:
                    outgoing[source_id] = []
                outgoing[source_id].append(target_id)
        return outgoing
    
    def findAllPath(self, start, end):
        """
        找到从start到end的所有路径
        算法参考：https://zhuanlan.zhihu.com/p/84437102
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
