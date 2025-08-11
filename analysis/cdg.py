#!/usr/bin/env python3
"""
控制依赖图(CDG)构建器

基于CFG构建控制依赖图，使用后支配树和支配边界算法
移植自static_program_analysis_by_tree_sitter/CDG.py
"""

from typing import List, Dict, Optional, Set
from .cfg import CFG
from .graph import Graph, Edge, EdgeType
from .node import Node
from .visualization import visualize_cdg


class CDGNode(Node):
    """CDG专用节点，用于虚拟节点"""
    
    def __init__(self, node_id, text, node_type="virtual"):
        """创建虚拟节点"""
        self.id = node_id
        self.text = text
        self.type = node_type
        self.line = -1
        self.is_branch = False
        self.defs = set()
        self.uses = set()


class Tree:
    """支配树结构"""
    
    def __init__(self, V: Set[int], children: Dict[int, List[int]], root: int):
        """
        初始化树
        Args:
            V: 节点集合
            children: 字典 {parent_id: [child_id, ...]}
            root: 根节点ID
        """
        self.vertex = V
        self.children = children
        self.root = root
        self.parent = {}
        
        # 初始化parent字典
        for node in children:
            for each in children[node]:
                self.parent[each] = node
        self.parent[root] = root
        
        # 确保所有节点都在children中
        for v in V:
            if v not in self.children:
                self.children[v] = []
        
        # 计算深度
        self.depth = self.get_nodes_depth(root, {root: 0})
    
    def get_nodes_depth(self, root: int, depth: Dict[int, int]) -> Dict[int, int]:
        """递归计算每个节点的深度"""
        for child in self.children[root]:
            depth[child] = depth[root] + 1
            depth = self.get_nodes_depth(child, depth)
        return depth
    
    def get_lca(self, a: int, b: int) -> int:
        """计算a,b的最近公共祖先"""
        if self.depth[a] > self.depth[b]:
            diff = self.depth[a] - self.depth[b]
            while diff > 0:
                a = self.parent[a]
                diff -= 1
        elif self.depth[a] < self.depth[b]:
            diff = self.depth[b] - self.depth[a]
            while diff > 0:
                b = self.parent[b]
                diff -= 1
        while a != b:
            a = self.parent[a]
            b = self.parent[b]
        return a
    
    def reset_by_parent(self):
        """根据parent字典重置children字典"""
        self.children = {v: [] for v in self.vertex}
        for node in self.parent:
            if node != self.parent[node]:
                self.children[self.parent[node]].append(node)


class CDG(CFG):
    """控制依赖图构建器"""
    
    def __init__(self, language: str = "c"):
        """初始化CDG构建器"""
        super().__init__(language)
        self.cdgs: Optional[List[Graph]] = None
    
    def get_subTree(self, cfg: Graph, exit_id: int) -> Dict[int, List[int]]:
        """
        按照广度优先遍历，找出一个子树
        """
        V = {node.id for node in cfg.nodes}
        
        # 构建出边字典 E: {node_id: [target_id, ...]}
        E = {}
        for edge in cfg.edges:
            if edge.source_node and edge.target_node:
                source_id = edge.source_node.id
                target_id = edge.target_node.id
                if source_id not in E:
                    E[source_id] = []
                E[source_id].append(target_id)
        
        visited = {v: False for v in V}
        if exit_id in visited:
            visited[exit_id] = True
        queue = [exit_id]
        subTree = {}
        
        while queue:
            node = queue.pop(0)
            if node not in E:
                continue
            for v in E[node]:
                if v in visited and not visited[v]:
                    queue.append(v)
                    visited[v] = True
                    subTree.setdefault(node, [])
                    subTree[node].append(v)
        
        return subTree
    
    def get_prev(self, cfgs: List[Graph]) -> Dict[int, List[int]]:
        """
        计算每个节点的前驱节点
        """
        prev = {}
        for cfg in cfgs:
            for edge in cfg.edges:
                if edge.source_node and edge.target_node:
                    source_id = edge.source_node.id
                    target_id = edge.target_node.id
                    prev.setdefault(target_id, [])
                    prev[target_id].append(source_id)
        
        return prev
    
    def post_dominator_tree(self, cfgs: List[Graph], prev: Dict[int, List[int]]) -> List[Tree]:
        """
        生成后支配树
        """
        PDT = []
        for cfg in cfgs:
            exit_id = getattr(cfg, 'Exit', -1)
            subTree = self.get_subTree(cfg, exit_id)
            V = {node.id for node in cfg.nodes}
            tree = Tree(V, subTree, exit_id)
            changed = True
            
            while changed:
                changed = False
                for v in V:
                    if v != exit_id and v in tree.parent:
                        for u in prev.get(v, []):
                            parent_v = tree.parent[v]
                            if u in tree.vertex and u != parent_v and parent_v != tree.get_lca(u, parent_v):
                                tree.parent[v] = tree.get_lca(u, parent_v)
                                changed = True
            
            tree.reset_by_parent()
            PDT.append(tree)
        
        return PDT
    
    def construct_cfg_with_exit(self, code: str) -> Optional[Graph]:
        """
        构建带虚拟出口节点的CFG（用于CDG分析）
        
        Args:
            code: 函数代码
            
        Returns:
            带虚拟出口节点的CFG，如果构建失败返回None
        """
        try:
            # 构建基础CFG
            cfg = self.construct_cfg(code)
            if not cfg:
                return None
            
            # 计算逆向CFG
            reverse_cfg = cfg.reverse()
            
            # 为反向CFG添加虚拟Exit节点
            exit_id = -1
            reverse_cfg.Exit = exit_id
            
            # 创建虚拟Exit节点
            exit_node = CDGNode(exit_id, "EXIT", "virtual_exit")
            reverse_cfg.add_node(exit_node)
            
            # 计算没有入边的节点（在反向图中），即原图中的出口节点
            nodes_with_incoming = set()
            for edge in reverse_cfg.edges:
                if edge.target_node:
                    nodes_with_incoming.add(edge.target_node.id)
            
            # 为没有入边的节点从Exit添加出边：exit_node -> node
            for node in reverse_cfg.nodes:
                if node.id != exit_id and node.id not in nodes_with_incoming:
                    exit_edge = Edge(
                        label='',
                        edge_type=EdgeType.CFG,
                        source_node=exit_node,
                        target_node=node
                    )
                    reverse_cfg.edges.append(exit_edge)
            
            return reverse_cfg
            
        except Exception as e:
            print(f'⚠️  CDG构建警告: construct_cfg_with_exit失败: {e}')
            return None
    
    def dominance_frontier(self, reverse_cfg: Graph) -> Dict[int, List[int]]:
        """
        基于带虚拟出口节点的反向CFG计算支配边界
        
        Args:
            reverse_cfg: 带虚拟出口节点的反向CFG
            
        Returns:
            支配边界字典 {node_id: [dominated_frontier_nodes]}
        """
        try:
            # 计算每个节点的前驱节点
            prev = self.get_prev([reverse_cfg])
            
            # 输入逆向CFG，输出后支配树
            PDT = self.post_dominator_tree([reverse_cfg], prev)
            if not PDT:
                return {}
            tree = PDT[0]
            
            # 计算支配边界
            V = {node.id for node in reverse_cfg.nodes}
            df: Dict[int, List[int]] = {v: [] for v in V}
            for v in V:
                if len(prev.get(v, [])) > 1:
                    for p in prev[v]:
                        runner = p
                        while runner != tree.parent.get(v, v):
                            if runner != v:
                                df[runner].append(v)
                            if runner == tree.parent.get(runner, runner):
                                break
                            runner = tree.parent[runner]
            
            return df
            
        except Exception as e:
            print(f'⚠️  CDG构建警告: dominance_frontier失败: {e}')
            return {}
    
    def construct_cdg(self, code: str) -> Optional[Graph]:
        """
        输入代码，返回CDG（单个函数）
        """
        try:
            reverse_cfg = self.construct_cfg_with_exit(code)
            if not reverse_cfg:
                return None
            df = self.dominance_frontier(reverse_cfg)
            if not df:
                return None
            
            # 从反向CFG恢复原CFG的节点集合（reverse()应保持节点的标识与集合一致）
            # 由于我们只需要节点集，用 reverse_cfg.nodes 即可
            cfg_nodes = reverse_cfg.nodes
            cfg_get_node = reverse_cfg.get_node_by_id
            
            # 构建CDG
            cdg = Graph()
            
            # 复制所有节点
            for node in cfg_nodes:
                cdg.add_node(node)
            
            # 找到函数入口节点（第一个函数定义节点）
            entry_node = None
            for node in cfg_nodes:
                if node.type == 'function_definition':
                    entry_node = node
                    break
            
            # 添加CDG边
            for source_id in df:
                source_node = cfg_get_node(source_id)
                if source_node:
                    for target_id in df[source_id]:
                        if source_id == target_id:
                            continue
                        target_node = cfg_get_node(target_id)
                        if target_node:
                            # 确定边标签
                            edge_label = ''
                            if entry_node and source_node.id == entry_node.id:
                                if target_node.is_branch:
                                    edge_label = 'branch'
                                else:
                                    edge_label = 'entry'
                            
                            cdg_edge = Edge(
                                label=edge_label,
                                edge_type=EdgeType.CDG,
                                source_node=source_node,
                                target_node=target_node
                            )
                            cdg.edges.append(cdg_edge)
            
            cdg.get_def_use_info()
            return cdg
            
        except Exception as e:
            print(f'⚠️  CDG构建警告: 构建失败: {e}')
            return None
    
    def see_cdg(self, code: str, filename: str = 'CDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化CDG"""
        cdg = self.construct_cdg(code)
        if cdg:
            visualize_cdg([cdg], filename, pdf, dot_format, view)
        return cdg