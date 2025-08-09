#!/usr/bin/env python3
"""
控制依赖图(CDG)构建器

基于CFG构建控制依赖图，使用后支配树和支配边界算法
"""

from typing import Optional
from .cfg import CFG
from .graph import Graph, Edge, EdgeType
from .visualization import visualize_cdg


class Tree:
    """支配树数据结构"""
    
    def __init__(self, V, children, root):
        """
        初始化树
        Args:
            V: 节点集合
            children: 字典，key为节点，value为子节点列表
            root: 根节点
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
                
        # 计算节点深度
        self.depth = self.get_nodes_depth(root, {root: 0})
    
    def get_nodes_depth(self, root, depth):
        """递归计算每个节点的深度"""
        for child in self.children[root]:
            depth[child] = depth[root] + 1
            depth = self.get_nodes_depth(child, depth)
        return depth
    
    def get_lca(self, a, b):
        """计算a,b的最近公共祖先"""
        # 检查节点是否存在
        if a not in self.depth or b not in self.depth:
            return self.root
        if a not in self.parent or b not in self.parent:
            return self.root
            
        if self.depth[a] > self.depth[b]:
            diff = self.depth[a] - self.depth[b]
            while diff > 0 and a in self.parent:
                a = self.parent[a]
                diff -= 1
        elif self.depth[a] < self.depth[b]:
            diff = self.depth[b] - self.depth[a]
            while diff > 0 and b in self.parent:
                b = self.parent[b]
                diff -= 1
        
        # 防止无限循环
        max_iterations = len(self.vertex)
        iterations = 0
        while a != b and iterations < max_iterations:
            if a not in self.parent or b not in self.parent:
                break
            a = self.parent[a]
            b = self.parent[b]
            iterations += 1
        
        return a if a == b else self.root
    
    def reset_by_parent(self):
        """根据parent字典重置children字典"""
        self.children = {v: [] for v in self.vertex}
        for node in self.parent:
            if node != self.parent[node]:
                self.children[self.parent[node]].append(node)


class CDG(CFG):
    """控制依赖图构建器 - 单函数版本"""
    
    def __init__(self, language: str = "c"):
        """初始化CDG构建器"""
        super().__init__(language)
        self.cdg: Optional[Graph] = None
    
    def get_subTree(self, cfg):
        """按照广度优先遍历，找出一个子树"""
        V, E = cfg.nodes, cfg.edges
        # 找到出口节点（没有出边的节点）
        outgoing = cfg.get_outgoing_edges()
        Exit = None
        for node in V:
            if node.id not in outgoing or len(outgoing[node.id]) == 0:
                Exit = node.id
                break
        
        if Exit is None:
            # 如果没有找到出口节点，使用最后一个节点
            Exit = V[-1].id if V else None
        
        if Exit is None:
            return {}
        
        visited = {v.id: False for v in V}
        queue = [Exit]
        visited[Exit] = True
        subTree = {}
        
        while queue:
            node = queue.pop(0)
            if node not in outgoing:
                continue
            for target_id in outgoing[node]:
                if not visited[target_id]:
                    queue.append(target_id)
                    visited[target_id] = True
                    subTree.setdefault(node, [])
                    subTree[node].append(target_id)
        return subTree
    
    def get_prev(self, cfg):
        """计算每个节点的前驱节点"""
        prev = {}
        for node in cfg.nodes:
            prev.setdefault(node.id, [])
        
        # 使用边列表计算前驱
        for edge in cfg.edges:
            if edge.source_node and edge.target_node:
                source_id = edge.source_node.id
                target_id = edge.target_node.id
                prev.setdefault(target_id, [])
                prev[target_id].append(source_id)
        return prev
    
    def post_dominator_tree(self, cfg, prev):
        """生成后支配树"""
        subTree = self.get_subTree(cfg)
        V = [node.id for node in cfg.nodes]
        
        # 找到根节点（出口节点）- 使用出边结构
        outgoing = cfg.get_outgoing_edges()
        root = None
        for node_id in V:
            if node_id not in outgoing or len(outgoing[node_id]) == 0:
                root = node_id
                break
        
        if root is None:
            root = V[-1] if V else None
        
        if root is None:
            return None
        
        tree = Tree(V, subTree, root)
        changed = True
        
        while changed:
            changed = False
            for v in V:
                if v != root and v in prev:
                    for u in prev[v]:
                        if u in tree.vertex:
                            parent_v = tree.parent[v]
                            if u != parent_v and parent_v != tree.get_lca(u, parent_v):
                                tree.parent[v] = tree.get_lca(u, parent_v)
                                changed = True
        
        tree.reset_by_parent()
        return tree
    
    def dominance_frontier(self, cfg):
        """计算支配边界"""
        # 计算逆向CFG
        reverse_cfg = cfg.reverse()
        prev = self.get_prev(reverse_cfg)
        PDT = self.post_dominator_tree(reverse_cfg, prev)
        
        if PDT is None:
            return {}
        
        V = [node.id for node in reverse_cfg.nodes]
        DF = {v: [] for v in V}
        
        for v in V:
            if len(prev[v]) > 1:
                for p in prev[v]:
                    runner = p
                    while runner != PDT.parent[v]:
                        DF[runner].append(v)
                        runner = PDT.parent[runner]
        
        return DF
    
    def construct_cdg(self, code: str) -> Optional[Graph]:
        """构建控制依赖图 - 单函数版本（简化版本）"""
        if self.check_syntax(code):
            print('⚠️  CDG构建警告: 检测到语法错误，但将继续尝试构建CDG')
        
        try:
            # 首先构建CFG
            cfg = self.construct_cfg(code)
            if not cfg:
                print('⚠️  CDG构建警告: 未找到任何函数')
                self.cdg = None
                return None
            
            try:
                # 创建CDG
                cdg = Graph()
                
                # 复制CFG的节点到CDG
                for node in cfg.nodes:
                    cdg.add_node(node)
                
                # 简化的控制依赖分析：基于分支节点
                for node in cfg.nodes:
                    if node.is_branch:  # 如果是分支节点
                        # 找到所有可能被这个分支控制的节点
                        controlled_nodes = self._find_controlled_nodes(cfg, node)
                        for controlled_node in controlled_nodes:
                            if controlled_node.id != node.id:
                                cdg_edge = Edge(label='', edge_type=EdgeType.CDG, source_node=node, target_node=controlled_node)
                                cdg.edges.append(cdg_edge)
                
                self.cdg = cdg
                return cdg
            except Exception as e:
                print(f'⚠️  CDG构建警告: 控制依赖分析失败: {e}')
                self.cdg = None
                return None
        except Exception as e:
            print(f'⚠️  CDG构建警告: 代码解析失败: {e}')
            self.cdg = None
            return None
    
    def _find_controlled_nodes(self, cfg, branch_node):
        """找到被分支节点控制的所有节点（简化版本）"""
        controlled = []
        outgoing = cfg.get_outgoing_edges()
        
        # 简单的启发式：分支节点后面的所有节点都可能被控制
        visited = set()
        queue = [branch_node.id]
        
        while queue:
            current_id = queue.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            
            if current_id in outgoing:
                for next_id in outgoing[current_id]:
                    if next_id not in visited:
                        queue.append(next_id)
                        # 找到对应的节点
                        for node in cfg.nodes:
                            if node.id == next_id:
                                controlled.append(node)
                                break
        
        return controlled
    
    def see_cdg(self, code: str, filename: str = 'CDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化控制依赖图"""
        cdg = self.construct_cdg(code)
        if cdg:
            visualize_cdg([cdg], filename, pdf, dot_format, view)
        return cdg
    
    def get_control_dependencies(self, code: str) -> Optional[dict]:
        """获取控制依赖关系"""
        cdg = self.construct_cdg(code)
        if not cdg:
            return None
        
        dependencies = []
        for edge in cdg.edges:
            if edge.type == 'CDG' and edge.source_node and edge.target_node:
                dependencies.append({
                    'controller': edge.source_node.id,
                    'controlled': edge.target_node.id,
                    'type': 'control_dependency'
                })
        
        return {
            'dependencies': dependencies,
            'total_count': len(dependencies)
        }