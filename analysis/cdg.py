#!/usr/bin/env python3
"""
控制依赖图(CDG)构建器

基于后支配树和支配边界算法构建控制依赖图
"""

from typing import List, Dict, Set, Optional
from .cfg import CFG
from .graph import Graph, Edge
from .node import Node
from .visualization import visualize_cdg


class Tree:
    """支配树数据结构"""
    
    def __init__(self, vertices: List[int], children: Dict[int, List[int]], root: int):
        """
        初始化树
        Args:
            vertices: 节点集合
            children: 子节点映射，key为节点，value为子节点列表
            root: 根节点
        """
        self.vertex = vertices
        self.children = children
        self.root = root
        self.parent = {}
        
        # 初始化parent字典
        for node in children:
            for child in children[node]:
                self.parent[child] = node
        self.parent[root] = root
        
        # 确保所有节点都在children中
        for v in vertices:
            if v not in self.children:
                self.children[v] = []
                
        # 计算每个节点的深度
        self.depth = self.get_nodes_depth(root, {root: 0})
    
    def get_nodes_depth(self, root: int, depth: Dict[int, int]) -> Dict[int, int]:
        """递归计算每个节点的深度"""
        for child in self.children[root]:
            depth[child] = depth[root] + 1
            depth = self.get_nodes_depth(child, depth)
        return depth
    
    def get_lca(self, a: int, b: int) -> int:
        """计算a,b的最近公共祖先(Lowest Common Ancestor)"""
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
        self.cdgs: List[Graph] = []
    
    def get_sub_tree(self, cfg: Graph) -> Dict[int, List[int]]:
        """
        按照广度优先遍历，找出一个子树
        从Exit节点开始反向遍历构建子树
        """
        vertices = [node.id for node in cfg.nodes]
        edges = cfg.edges
        
        # 找到Exit节点（度为0的节点或最后一个节点）
        exit_node = None
        for node in cfg.nodes:
            if node.id not in edges or len(edges[node.id]) == 0:
                exit_node = node.id
                break
        
        if exit_node is None and cfg.nodes:
            # 如果没有找到Exit节点，使用最后一个节点
            exit_node = cfg.nodes[-1].id
        
        if exit_node is None:
            return {}
        
        visited = {v: False for v in vertices}
        queue = [exit_node]
        visited[exit_node] = True
        sub_tree = {}
        
        while queue:
            node = queue.pop(0)  # BFS
            if node not in edges:
                continue
            
            for edge in edges[node]:
                v = edge.id
                if v in visited and not visited[v]:
                    queue.append(v)
                    visited[v] = True
                    sub_tree.setdefault(node, [])
                    sub_tree[node].append(v)
        
        return sub_tree
    
    def get_predecessors(self, cfgs: List[Graph]) -> Dict[int, List[int]]:
        """计算每个节点的前驱节点"""
        predecessors = {}
        
        for cfg in cfgs:
            # 初始化所有节点的前驱列表
            for node in cfg.nodes:
                predecessors.setdefault(node.id, [])
            
            # 构建前驱关系
            for node_id, edges in cfg.edges.items():
                for edge in edges:
                    target_id = edge.id
                    predecessors.setdefault(target_id, [])
                    predecessors[target_id].append(node_id)
        
        return predecessors
    
    def post_dominator_tree(self, cfgs: List[Graph], predecessors: Dict[int, List[int]]) -> List[Tree]:
        """生成后支配树"""
        post_dom_trees = []
        
        for cfg in cfgs:
            sub_tree = self.get_sub_tree(cfg)
            vertices = [node.id for node in cfg.nodes]
            
            # 找到根节点（Exit节点）
            root = None
            for node in cfg.nodes:
                if node.id not in cfg.edges or len(cfg.edges[node.id]) == 0:
                    root = node.id
                    break
            
            if root is None and cfg.nodes:
                root = cfg.nodes[-1].id
            
            if root is None:
                continue
            
            tree = Tree(vertices, sub_tree, root)
            
            # 后支配树算法
            changed = True
            iterations = 0
            max_iterations = len(vertices) * 2  # 防止无限循环
            
            while changed and iterations < max_iterations:
                changed = False
                iterations += 1
                
                for v in vertices:
                    if v != root and v in predecessors:
                        for u in predecessors[v]:
                            if u in tree.parent:
                                parent_v = tree.parent[v]
                                if u in tree.vertex and u != parent_v:
                                    lca = tree.get_lca(u, parent_v)
                                    if parent_v != lca:
                                        tree.parent[v] = lca
                                        changed = True
            
            tree.reset_by_parent()
            post_dom_trees.append(tree)
        
        return post_dom_trees
    
    def dominance_frontier(self, code: str):
        """计算支配边界"""
        if self.check_syntax(code):
            print('Syntax Error')
            return [], []
        
        # 构建CFG
        cfgs = self.see_cfg(code, pdf=False, dot_format=False)
        
        # 创建反向CFG
        reverse_cfgs = []
        for cfg in cfgs:
            reverse_cfg = cfg.reverse()
            reverse_cfgs.append(reverse_cfg)
        
        # 计算前驱节点
        predecessors = self.get_predecessors(reverse_cfgs)
        
        # 构建后支配树
        post_dom_trees = self.post_dominator_tree(reverse_cfgs, predecessors)
        
        # 计算支配边界
        dominance_frontiers = []
        for cfg, tree in zip(reverse_cfgs, post_dom_trees):
            vertices = [node.id for node in cfg.nodes]
            df = {v: [] for v in vertices}
            
            for v in vertices:
                if v in predecessors and len(predecessors[v]) > 1:
                    for p in predecessors[v]:
                        if p in tree.parent:
                            runner = p
                            parent_v = tree.parent.get(v, v)
                            
                            # 防止无限循环
                            visited = set()
                            while runner != parent_v and runner not in visited:
                                visited.add(runner)
                                df[runner].append(v)
                                runner = tree.parent.get(runner, runner)
                                if runner == tree.parent.get(runner, runner):
                                    break
            
            dominance_frontiers.append(df)
        
        return cfgs, dominance_frontiers
    
    def construct_cdg(self, code: str) -> List[Graph]:
        """构建控制依赖图"""
        if self.check_syntax(code):
            print('⚠️  CDG构建警告: 检测到语法错误，但将继续尝试构建CDG')
            # 不直接返回，继续尝试构建CDG
        
        try:
            # 构建CFG
            cfgs = self.see_cfg(code, pdf=False, dot_format=False)
            
            self.cdgs = []
            for cfg in cfgs:
                try:
                    cdg = Graph()
                    
                    # 复制CFG的节点到CDG
                    for node in cfg.nodes:
                        cdg.add_node(node)
                    
                    # 基于CFG构建控制依赖关系
                    self._build_control_dependencies_from_cfg(cfg, cdg)
                    
                    self.cdgs.append(cdg)
                except Exception as e:
                    print(f'⚠️  CDG构建警告: CFG处理失败: {e}')
                    continue
        except Exception as e:
            print(f'⚠️  CDG构建警告: 代码解析失败: {e}')
            self.cdgs = []
        
        return self.cdgs
    
    def _build_control_dependencies_from_cfg(self, cfg: Graph, cdg: Graph):
        """基于CFG构建控制依赖关系"""
        # 找到函数定义节点作为根节点
        function_node = None
        for node in cfg.nodes:
            if node.type == 'function_definition':
                function_node = node
                break
        
        if not function_node:
            return
        
        # 找到所有分支节点
        branch_nodes = [node for node in cfg.nodes if node.is_branch]
        
        # 跟踪已经有控制依赖的节点
        controlled_nodes_set = set()
        
        for branch_node in branch_nodes:
            # 找到该分支节点控制的所有节点
            controlled_nodes = self._find_controlled_nodes_in_cfg(cfg, branch_node)
            
            # 建立控制依赖边：从分支节点指向被控制的节点
            for controlled_node in controlled_nodes:
                if controlled_node.id != branch_node.id:
                    edge = Edge(controlled_node.id, '', 'CDG')
                    if branch_node.id not in cdg.edges:
                        cdg.edges[branch_node.id] = []
                    cdg.edges[branch_node.id].append(edge)
                    controlled_nodes_set.add(controlled_node.id)
        
        # 将所有没有控制依赖的节点连接到函数根节点
        # 这样确保CDG是连通的，以函数签名为根
        for node in cfg.nodes:
            if node.id != function_node.id and node.id not in controlled_nodes_set:
                # 对于分支节点和普通节点，都连接到函数根节点
                label = 'branch' if node.is_branch else 'entry'
                edge = Edge(node.id, label, 'CDG')
                if function_node.id not in cdg.edges:
                    cdg.edges[function_node.id] = []
                cdg.edges[function_node.id].append(edge)
    
    def _find_controlled_nodes_in_cfg(self, cfg: Graph, branch_node: Node) -> List[Node]:
        """在CFG中找到被分支节点控制的所有节点"""
        controlled = []
        
        # 找到以分支节点为源的所有边
        for target_id, edges in cfg.edges.items():
            for edge in edges:
                if edge.id == branch_node.id:  # 分支节点是这条边的源
                    target_node = cfg.id_to_nodes.get(target_id)
                    if target_node and target_node != branch_node:
                        # 根据分支类型和边标签判断是否为真正的控制依赖
                        if self._is_true_control_dependency(branch_node, edge):
                            controlled.append(target_node)
                            # 对于真正被控制的节点，递归找到其传递控制的节点
                            transitive = self._find_transitively_controlled(cfg, target_node, branch_node)
                            controlled.extend(transitive)
        
        return controlled
    
    def _is_true_control_dependency(self, branch_node: Node, edge) -> bool:
        """判断是否为真正的控制依赖关系"""
        branch_type = branch_node.type
        edge_label = edge.label if hasattr(edge, 'label') else ''
        
        if branch_type in ['while_statement', 'for_statement']:
            # 对于循环：只有进入循环体的边（通常是Y）才是控制依赖
            # 退出循环的边（通常是N）不是控制依赖，因为退出后的语句无论如何都会执行
            return edge_label == 'Y'
        elif branch_type == 'if_statement':
            # 对于if语句：then分支（Y）和else分支（N）都是控制依赖
            return edge_label in ['Y', 'N']
        elif branch_type == 'switch_statement':
            # 对于switch语句：所有case都是控制依赖
            return True
        else:
            # 其他分支类型（如三元运算符等）
            return edge_label in ['Y', 'N']
    
    def _find_transitively_controlled(self, cfg: Graph, start_node: Node, original_branch: Node) -> List[Node]:
        """递归找到传递控制的节点"""
        controlled = []
        visited = set()
        
        def dfs_controlled(node_id, depth=0):
            if node_id in visited or depth > 10:  # 防止无限递归
                return
            visited.add(node_id)
            
            if node_id in cfg.edges:
                edges = cfg.edges[node_id]
                # 如果只有一个后继，说明控制继续传递
                if len(edges) == 1:
                    edge = edges[0]
                    target_node = cfg.id_to_nodes.get(edge.id)
                    if target_node and target_node != original_branch:
                        # 检查这个节点是否还有其他前驱（如果有，说明是汇合点）
                        has_other_predecessors = False
                        for other_id, other_edges in cfg.edges.items():
                            if other_id != node_id:
                                for other_edge in other_edges:
                                    if other_edge.id == edge.id:
                                        has_other_predecessors = True
                                        break
                        
                        if not has_other_predecessors:
                            controlled.append(target_node)
                            dfs_controlled(edge.id, depth + 1)
        
        dfs_controlled(start_node.id)
        return controlled
    
    def see_cdg(self, code: str, filename: str = 'CDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化控制依赖图"""
        self.construct_cdg(code)
        visualize_cdg(self.cdgs, filename, pdf, dot_format, view)
        return self.cdgs
    
    def get_control_dependencies(self, code: str) -> List[Dict]:
        """
        获取结构化的控制依赖信息
        Returns:
            包含每个函数控制依赖信息的列表
        """
        self.construct_cdg(code)
        
        dependencies = []
        for i, cdg in enumerate(self.cdgs):
            func_deps = {
                'function_index': i,
                'dependencies': []
            }
            
            for node_id, edges in cdg.edges.items():
                if node_id in cdg.id_to_nodes:
                    source_node = cdg.id_to_nodes[node_id]
                    
                    for edge in edges:
                        if edge.id in cdg.id_to_nodes:
                            target_node = cdg.id_to_nodes[edge.id]
                            
                            dep_info = {
                                'source': {
                                    'id': source_node.id,
                                    'line': source_node.line,
                                    'text': source_node.text,
                                    'type': source_node.type,
                                    'is_branch': source_node.is_branch
                                },
                                'target': {
                                    'id': target_node.id,
                                    'line': target_node.line,
                                    'text': target_node.text,
                                    'type': target_node.type
                                }
                            }
                            
                            func_deps['dependencies'].append(dep_info)
            
            dependencies.append(func_deps)
        
        return dependencies


