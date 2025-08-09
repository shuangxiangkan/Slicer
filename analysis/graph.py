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
    
    def __init__(self, target_id: int = None, label: str = '', edge_type: EdgeType = EdgeType.CFG, 
                 source_node: Node = None, target_node: Node = None):
        """
        创建边
        Args:
            target_id: 目标节点ID (向后兼容，当target_node为None时使用)
            label: 边的标签
            edge_type: 边的类型
            source_node: 源节点对象 (推荐使用)
            target_node: 目标节点对象 (推荐使用)
        """
        self.source_node = source_node
        self.target_node = target_node
        self.label = label
        self.type = edge_type
        
        # 向后兼容：当没有提供target_node但有target_id时，保存target_id用于后续查找
        self._legacy_target_id = target_id if target_node is None and target_id is not None else None
    
    @property
    def source_id(self):
        """获取源节点ID"""
        return self.source_node.id if self.source_node else None
    
    @property
    def target_id(self):
        """获取目标节点ID"""
        return self.target_node.id if self.target_node else self._legacy_target_id
    
    @property
    def id(self):
        """向后兼容属性"""
        return self.target_id
    
    def __str__(self):
        """提供调试友好的字符串表示"""
        if self.source_node and self.target_node:
            source_text = self.source_node.text[:50] + "..." if len(self.source_node.text) > 50 else self.source_node.text
            target_text = self.target_node.text[:50] + "..." if len(self.target_node.text) > 50 else self.target_node.text
            return f"Edge({self.type.value}): [{source_text}] -> [{target_text}]"
        else:
            return f"Edge({self.type.value}): {self.source_id} -> {self.target_id}"
    
    def __repr__(self):
        return self.__str__()


class DDGEdge(Edge):
    """数据依赖图边，包含变量信息"""
    
    def __init__(self, target_id: int = None, label: str = '', variables: List[str] = None,
                 source_node: Node = None, target_node: Node = None):
        """
        创建DDG边
        Args:
            target_id: 目标节点ID (向后兼容，当target_node为None时使用)
            label: 边的标签
            variables: 依赖的变量列表
            source_node: 源节点对象 (推荐使用)
            target_node: 目标节点对象 (推荐使用)
        """
        super().__init__(target_id, label, EdgeType.DDG, source_node, target_node)
        self.variables = variables or []  # 依赖的变量列表
        
        # 为了保持向后兼容性，保留token属性
        self.token = self.variables
    
    def __str__(self):
        """提供调试友好的字符串表示"""
        base_str = super().__str__()
        if self.variables:
            return f"{base_str} [vars: {', '.join(self.variables)}]"
        return base_str


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
                
                # 处理边列表或单个边
                edges_to_add = target_edge if isinstance(target_edge, list) else [target_edge]
                
                for edge in edges_to_add:
                    # 如果边还没有设置source_node，自动设置
                    if edge.source_node is None:
                        edge.source_node = source_node
                    
                    # 如果边有_legacy_target_id但没有target_node，尝试从图中查找
                    if (edge.target_node is None and 
                        hasattr(edge, '_legacy_target_id') and edge._legacy_target_id is not None):
                        for node in self.nodes:
                            if node.id == edge._legacy_target_id:
                                edge.target_node = node
                                edge._legacy_target_id = None  # 清除legacy ID
                                break
                
                self.edges[source_node.id].extend(edges_to_add)
    
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
                # 根据边的类型创建相应的反向边，交换source和target
                if isinstance(edge, DDGEdge):
                    reversed_edge = DDGEdge(
                        target_id=source_id, 
                        label=edge.label, 
                        variables=edge.variables,
                        source_node=edge.target_node,  # 交换
                        target_node=edge.source_node   # 交换
                    )
                else:
                    reversed_edge = Edge(
                        target_id=source_id, 
                        label=edge.label, 
                        edge_type=edge.type,
                        source_node=edge.target_node,  # 交换
                        target_node=edge.source_node   # 交换
                    )
                    # 为了向后兼容，如果原边有token属性，也复制过来
                    if hasattr(edge, 'token'):
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
