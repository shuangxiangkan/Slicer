#!/usr/bin/env python3
"""
控制依赖图(CDG)构建器

基于CFG构建控制依赖图，使用Lengauer-Tarjan算法构建后支配树和支配边界算法
借鉴static_program_analysis_by_tree_sitter/CDG.py, 并优化为使用高效的Lengauer-Tarjan算法
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
        self.children = children
        self.root = root
        self.parent = {}
        
        # 初始化parent字典
        for node in children:
            for each in children[node]:
                self.parent[each] = node
        self.parent[self.root] = self.root
        
        # 确保所有节点都在children中
        for v in V:
            if v not in self.children:
                self.children[v] = []
        
class CDG(CFG):
    """控制依赖图构建器"""
    
    def __init__(self, language: str = "c"):
        """初始化CDG构建器"""
        super().__init__(language)
        self.cdg: Optional[Graph] = None

    
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
    
    def post_dominator_tree(self, cfg: Graph, prev: Dict[int, List[int]]) -> Tree:
        """
        使用Lengauer-Tarjan算法生成后支配树
        """
        exit_id = getattr(cfg, 'Exit', -1)
        V = {node.id for node in cfg.nodes}
        
        # 构建后继节点字典（用于DFS）
        succ = {}
        for edge in cfg.edges:
            if edge.source_node and edge.target_node:
                source_id = edge.source_node.id
                target_id = edge.target_node.id
                succ.setdefault(source_id, [])
                succ[source_id].append(target_id)
        
        # 执行Lengauer-Tarjan算法
        idom = self.lengauer_tarjan(V, succ, exit_id)
        
        # 构建支配树
        children = {v: [] for v in V}
        parent = {}
        for v in V:
            if v in idom and idom[v] != v:
                children[idom[v]].append(v)
                parent[v] = idom[v]
            else:
                parent[v] = v  # 根节点
        
        tree = Tree(V, children, exit_id)
        tree.parent = parent
        return tree
    
    def lengauer_tarjan(self, V: Set[int], succ: Dict[int, List[int]], root: int) -> Dict[int, int]:
        """
        Lengauer-Tarjan算法实现
        返回直接支配者字典 {node: immediate_dominator}
        """
        # 初始化数据结构
        n = len(V)
        node_map = {}  # DFS编号到节点的映射
        dfnum = {}   # 节点到DFS编号的映射
        parent = {}  # DFS树中的父节点
        semi = {}    # 半支配者
        idom = {}    # 直接支配者
        ancestor = {} # 祖先节点（用于路径压缩）
        label = {}   # 标签（用于路径压缩）
        bucket = {}  # 桶，存储半支配者相同的节点
        
        # Step 1: DFS编号
        counter = [0]
        self._dfs(root, succ, dfnum, node_map, parent, counter)
        
        # 初始化（在DFS之后，因为需要DFS编号）
        for v in V:
            if v in dfnum:  # 只处理可达节点
                semi[v] = dfnum[v]
                idom[v] = 0
                ancestor[v] = 0
                label[v] = v
                bucket[v] = []
        
        # Step 2: 计算半支配者
        for i in range(counter[0] - 1, 0, -1):
            w = node_map[i]
            
            # 计算w的半支配者
            for v in self._get_predecessors(w, succ, V):
                if v in dfnum:  # 确保前驱节点在DFS树中
                    u = self._eval(v, ancestor, label, semi, dfnum)
                    if semi[u] < semi[w]:
                        semi[w] = semi[u]
            
            # 将w添加到其半支配者的桶中
            if semi[w] < len(node_map) and semi[w] in node_map:
                semi_dom = node_map[semi[w]]
                bucket[semi_dom].append(w)
            
            # 链接w到其父节点
            if w in parent and parent[w] != 0:
                self._link(parent[w], w, ancestor, label)
                
                # 处理父节点桶中的节点
                for v in bucket[parent[w]]:
                    u = self._eval(v, ancestor, label, semi, dfnum)
                    if semi[u] < semi[v]:
                        idom[v] = u
                    else:
                        idom[v] = parent[w]
                
                bucket[parent[w]] = []
        
        # Step 3: 计算直接支配者
        for i in range(1, counter[0]):
            w = node_map[i]
            if w in idom and idom[w] != 0 and semi[w] < len(node_map) and semi[w] in node_map:
                if idom[w] != node_map[semi[w]]:
                    idom[w] = idom[idom[w]]
        
        # 设置根节点和不可达节点
        idom[root] = root
        for v in V:
            if v not in dfnum:
                idom[v] = root  # 不可达节点由根节点支配
        
        return idom
    
    def _dfs(self, v: int, succ: Dict[int, List[int]], dfnum: Dict[int, int], 
             node_map: Dict[int, int], parent: Dict[int, int], counter: List[int]):
        """深度优先搜索，进行DFS编号"""
        dfnum[v] = counter[0]
        node_map[counter[0]] = v
        counter[0] += 1
        
        for w in succ.get(v, []):
            if w not in dfnum:
                parent[w] = v
                self._dfs(w, succ, dfnum, node_map, parent, counter)
    
    def _get_predecessors(self, node: int, succ: Dict[int, List[int]], V: Set[int]) -> List[int]:
        """获取节点的前驱节点"""
        pred = []
        for v in V:
            if node in succ.get(v, []):
                pred.append(v)
        return pred
    
    def _eval(self, v: int, ancestor: Dict[int, int], label: Dict[int, int], 
              semi: Dict[int, int], dfnum: Dict[int, int]) -> int:
        """路径压缩的eval操作"""
        if ancestor[v] == 0:
            return label[v]
        else:
            self._compress(v, ancestor, label, semi, dfnum)
            if semi[label[ancestor[v]]] >= semi[label[v]]:
                return label[v]
            else:
                return label[ancestor[v]]
    
    def _compress(self, v: int, ancestor: Dict[int, int], label: Dict[int, int], 
                  semi: Dict[int, int], dfnum: Dict[int, int]):
        """路径压缩"""
        if ancestor[ancestor[v]] != 0:
            self._compress(ancestor[v], ancestor, label, semi, dfnum)
            if semi[label[ancestor[v]]] < semi[label[v]]:
                label[v] = label[ancestor[v]]
            ancestor[v] = ancestor[ancestor[v]]
    
    def _link(self, v: int, w: int, ancestor: Dict[int, int], label: Dict[int, int]):
        """链接操作"""
        ancestor[w] = v
    
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
            tree = self.post_dominator_tree(reverse_cfg, prev)
            if not tree:
                return {}
            
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
            # 注意：在支配边界计算中，df[runner].append(v) 表示 runner 在 v 的支配边界中
            # 这意味着 v 控制依赖于 runner，所以边应该从 runner 指向 v
            # 但根据控制依赖的语义，应该是控制节点指向被控制节点
            # 因此需要交换source和target的角色
            for controlled_id in df:  # controlled_id 是被控制的节点
                controlled_node = cfg_get_node(controlled_id)
                if controlled_node:
                    for controller_id in df[controlled_id]:  # controller_id 是控制节点
                        if controlled_id == controller_id:
                            continue
                        controller_node = cfg_get_node(controller_id)
                        if controller_node:
                            # 确定边标签
                            edge_label = ''
                            if entry_node and controller_node.id == entry_node.id:
                                if controlled_node.is_branch:
                                    edge_label = 'branch'
                                else:
                                    edge_label = 'entry'
                            
                            # 控制依赖边：从控制节点指向被控制节点
                            cdg_edge = Edge(
                                label=edge_label,
                                edge_type=EdgeType.CDG,
                                source_node=controller_node,   # 控制节点
                                target_node=controlled_node    # 被控制节点
                            )
                            cdg.edges.append(cdg_edge)
            
            cdg.get_def_use_info()
            self.cdg = cdg
            return cdg
            
        except Exception as e:
            print(f'⚠️  CDG构建警告: 构建失败: {e}')
            self.cdg = None
            return None
    
    def see_cdg(self, code: str, filename: str = 'CDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化CDG"""
        cdg = self.construct_cdg(code)
        if cdg:
            visualize_cdg([cdg], filename, pdf, dot_format, view)
        return cdg
    
    def print_cdg_edges(self):
        """打印CDG的边信息，格式：语句A (序号) --> 语句B (序号)"""
        if not hasattr(self, 'cdg') or not self.cdg:
            print("CDG未构建，请先调用construct_cdg()")
            return
        
        print("=== CDG 边信息 ===")
        if not self.cdg.edges:
            print("该图没有边")
            return
            
        for i, edge in enumerate(self.cdg.edges, 1):
            if edge.source_node and edge.target_node:
                source_text = edge.source_node.text.strip().replace('\n', ' ')
                target_text = edge.target_node.text.strip().replace('\n', ' ')
                source_id = edge.source_node.id
                target_id = edge.target_node.id
                
                # 限制文本长度，避免过长
                if len(source_text) > 50:
                    source_text = source_text[:47] + "..."
                if len(target_text) > 50:
                    target_text = target_text[:47] + "..."
                
                # 显示边的标签信息（如entry、branch等）
                label_info = f" [{edge.label}]" if edge.label else ""
                print(f"{i:3d}. {source_text} ({source_id}) --> {target_text} ({target_id}){label_info}")
            else:
                print(f"{i:3d}. [无效边: 缺少源节点或目标节点]")
        
        print(f"\n总计: {len(self.cdg.edges)} 条边")