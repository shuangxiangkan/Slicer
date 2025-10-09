#!/usr/bin/env python3
"""
控制流图(CFG)构建器

基于tree-sitter构建函数级控制流图
"""

from typing import Optional
from .base import BaseAnalyzer
from .node import Node
from .graph import Graph, Edge, EdgeType
from .visualization import visualize_cfg

class CFG(BaseAnalyzer):
    """单函数控制流图构建器"""

    def __init__(self, language: str = "c"):
        """初始化CFG构建器"""
        super().__init__(language)
        self.cfg: Optional[Graph] = None

    def create_cfg(self, node, in_nodes=[()]):
        """
        递归创建CFG
        Args:
            node: 当前tree-sitter节点
            in_nodes: 入节点列表，格式为[(node_info, edge_label), ...]
        Returns:
            (CFG_edges, out_nodes): CFG边列表和出节点列表
        """
        if node.child_count == 0 or in_nodes == []:
            return [], in_nodes
        
        if node.type == 'function_definition':
            # 如果节点是函数，则创建函数节点，并且递归遍历函数的compound_statement
            body = node.child_by_field_name('body')
            node_info = Node(node)
            CFG, _ = self.create_cfg(body, [(node_info, '')])
            return CFG + [(node_info, [])], []

        elif node.type == 'compound_statement':
            # 如果是复合语句，则递归遍历复合语句的每一条statement
            CFG = []
            pending_break_nodes = []  # 存储需要连接到后续语句的break节点
            
            for i, child in enumerate(node.children):
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                
                # 如果当前语句是循环，收集其中的break节点
                if child.type in ['while_statement', 'for_statement', 'do_statement']:
                    break_nodes, _ = self.get_break_continue_nodes(child)
                    pending_break_nodes.extend([Node(bn) for bn in break_nodes])
                
                # 如果有待处理的break节点且当前不是循环语句，连接break节点到当前语句
                if pending_break_nodes and child.type not in ['while_statement', 'for_statement', 'do_statement', '{', '}']:
                    # 找到当前语句的节点
                    current_stmt_node = None
                    for node_info, _ in cfg:
                        if node_info.text.strip() and node_info.text != '{':
                            current_stmt_node = node_info
                            break
                    
                    if current_stmt_node:
                        # 为每个break节点添加到当前语句的边
                        for break_node in pending_break_nodes:
                            break_edge = Edge(label='', edge_type=EdgeType.CFG, 
                                            source_node=break_node, target_node=current_stmt_node)
                            # 找到break节点在CFG中的位置并添加边
                            for j, (cfg_node, cfg_edges) in enumerate(CFG):
                                if cfg_node.id == break_node.id:
                                    CFG[j] = (cfg_node, list(cfg_edges) + [break_edge])
                                    break
                        pending_break_nodes = []  # 清空已处理的break节点
                
                in_nodes = out_nodes
            return CFG, in_nodes

        elif node.type == 'else_clause':
            # 处理else子句，递归解析其内容
            CFG = []
            # else子句通常包含一个子节点（可能是compound_statement或单个语句）
            if node.child_count > 1:  # else { ... } 或 else statement
                for child in node.children:
                    if child.type not in ['else']:  # 跳过'else'关键字
                        cfg, out_nodes = self.create_cfg(child, in_nodes)
                        CFG.extend(cfg)
                        in_nodes = out_nodes
            return CFG, in_nodes
        
        elif node.type not in ['if_statement', 'while_statement', 'for_statement', 'switch_statement', 'case_statement', 'translation_unit', 'do_statement']:
            # 如果是普通的语句
            node_info = Node(node)
            edges = self.get_edge(in_nodes, node_info)
            in_nodes = [(node_info, '')]
            if node.type in ['return_statement', 'break_statement', 'continue_statement']:
                # return，break，continue语句没有出节点
                return [(node_info, edges)], []
            else:
                return [(node_info, edges)], in_nodes

        elif node.type == 'if_statement':
            return self._handle_if_statement(node, in_nodes)

        elif node.type in ['while_statement', 'for_statement']:
            return self._handle_loop_statement(node, in_nodes)

        elif node.type == 'do_statement':
            return self._handle_do_statement(node, in_nodes)

        elif node.type == 'switch_statement':
            return self._handle_switch_statement(node, in_nodes)

        elif node.type == 'case_statement':
            return self._handle_case_statement(node, in_nodes)

        else:
            # 对于其他类型的节点，递归处理子节点
            CFG = []
            for child in node.children:
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                in_nodes = out_nodes
            return CFG, in_nodes
    
    def _handle_if_statement(self, node, in_nodes):
        """处理if语句"""
        CFG = []
        node_info = Node(node)
        edges = self.get_edge(in_nodes, node_info)
        CFG.append((node_info, edges))

        # 处理then分支
        consequence = node.child_by_field_name('consequence')
        cfg, then_out = self.create_cfg(consequence, [(node_info, 'Y')])
        CFG.extend(cfg)

        # 处理else分支
        alternative = node.child_by_field_name('alternative')
        if alternative:
            cfg, else_out = self.create_cfg(alternative, [(node_info, 'N')])
            CFG.extend(cfg)
            out_nodes = then_out + else_out
        else:
            out_nodes = then_out + [(node_info, 'N')]

        return CFG, out_nodes
    
    def _handle_loop_statement(self, node, in_nodes):
        """处理循环语句"""
        CFG = []
        node_info = Node(node)
        edges = self.get_edge(in_nodes, node_info)
        CFG.append((node_info, edges))

        # 处理循环体
        body = node.child_by_field_name('body')
        cfg, body_out = self.create_cfg(body, [(node_info, 'Y')])
        CFG.extend(cfg)

        # 处理break和continue语句
        break_nodes, continue_nodes = self.get_break_continue_nodes(node)

        # 循环体的出口回到条件 - 为循环条件节点添加来自循环体出口的边
        # 但是要排除 break 节点，因为 break 节点应该跳出循环
        loop_back_edges = []
        break_node_ids = {Node(break_node).id for break_node in break_nodes}
        for out_node, label in body_out:
            if out_node and out_node.id not in break_node_ids:
                back_edge = Edge(label=label, edge_type=EdgeType.CFG, source_node=out_node, target_node=node_info)
                loop_back_edges.append(back_edge)
        
        # continue语句也应该回到循环条件
        for continue_node in continue_nodes:
            continue_node_info = Node(continue_node)
            # 对于for循环，continue应该跳转到更新部分（如果有），然后到条件
            # 对于while循环和for(;;)，continue应该直接跳转到循环条件
            # 当前简化为直接跳转到循环条件
            back_edge = Edge(label='', edge_type=EdgeType.CFG, source_node=continue_node_info, target_node=node_info)
            loop_back_edges.append(back_edge)

        # 更新循环条件节点的入边，添加回边
        if loop_back_edges:
            for i, (cfg_node, cfg_edges) in enumerate(CFG):
                if cfg_node.id == node_info.id:
                    CFG[i] = (cfg_node, list(cfg_edges) + loop_back_edges)
                    break

        # 循环的出口：循环条件为false时跳出
        # break语句不应该作为出口节点返回，因为它们已经在循环内部处理了
        out_nodes = [(node_info, 'N')]  # 循环条件为false时跳出

        return CFG, out_nodes

    def _handle_do_statement(self, node, in_nodes):
        """处理do-while语句"""
        # 1. 循环体
        body = node.child_by_field_name('body')
        body_cfg, body_out_nodes = self.create_cfg(body, in_nodes)

        # 2. 条件
        condition = node.child_by_field_name('condition')
        condition_node_info = Node(condition)
        condition_node_info.text = f'while ({condition_node_info.text})'
        condition_node_info.is_branch = True

        # 3. break 和 continue 节点
        break_ts_nodes, continue_ts_nodes = self.get_break_continue_nodes(body)
        
        # 4. 找到CFG中的Node对象
        all_cfg_nodes = {node_info.id: node_info for node_info, _ in body_cfg}
        break_nodes = [all_cfg_nodes[Node(n).id] for n in break_ts_nodes if Node(n).id in all_cfg_nodes]
        continue_nodes = [all_cfg_nodes[Node(n).id] for n in continue_ts_nodes if Node(n).id in all_cfg_nodes]

        # 5. 连接循环体正常出口和 continue 节点到条件节点
        condition_in_nodes = body_out_nodes
        for cont_node in continue_nodes:
            condition_in_nodes.append((cont_node, ''))

        # 6. 将条件节点添加到CFG
        CFG = body_cfg
        condition_edges = self.get_edge(condition_in_nodes, condition_node_info)
        CFG.append((condition_node_info, condition_edges))

        # 7. 从条件节点连接回循环体入口 (回边)
        if body_cfg:
            first_node_in_body = body_cfg[0][0]
            for i, (cfg_node, cfg_edges) in enumerate(CFG):
                if cfg_node.id == first_node_in_body.id:
                    new_edges = list(cfg_edges)
                    back_edge = Edge(label='Y', edge_type=EdgeType.CFG, source_node=condition_node_info, target_node=first_node_in_body)
                    new_edges.append(back_edge)
                    CFG[i] = (cfg_node, new_edges)
                    break
        
        # 8. 确定整个 do-while 语句的出口
        out_nodes = [(condition_node_info, 'N')]
        for brk_node in break_nodes:
            out_nodes.append((brk_node, ''))

        return CFG, out_nodes
    
    def _handle_switch_statement(self, node, in_nodes):
        """处理switch语句"""
        CFG = []
        node_info = Node(node)
        edges = self.get_edge(in_nodes, node_info)
        CFG.append((node_info, edges))

        # 处理switch体
        body = node.child_by_field_name('body')
        if body:
            cfg, body_out = self.create_cfg(body, [(node_info, '')])
            CFG.extend(cfg)

            # 处理break语句
            break_nodes, _ = self.get_break_continue_nodes(node)
            for break_node in break_nodes:
                body_out.append((Node(break_node), ''))

            return CFG, body_out

        return CFG, [(node_info, '')]

    def _handle_case_statement(self, node, in_nodes):
        """处理case语句"""
        CFG = []
        node_info = Node(node)
        edge = self.get_edge(in_nodes, node_info)
        CFG.append((node_info, edge))

        if node.children and node.children[0].type == 'case':
            # case语句
            in_nodes = [(node_info, 'Y')]
            for child in node.children[3:]:  # 跳过 'case', 'value', ':'
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                in_nodes = out_nodes
            return CFG, in_nodes + [(node_info, 'N')]
        else:
            # default语句
            in_nodes = [(node_info, '')]
            for child in node.children[2:]:  # 跳过 'default', ':'
                cfg, out_nodes = self.create_cfg(child, in_nodes)
                CFG.extend(cfg)
                in_nodes = out_nodes
            return CFG, in_nodes
        
    def get_break_continue_nodes(self, node):
        """找到节点循环中的所有break和continue节点"""
        break_nodes, continue_nodes = [], []
        for child in node.children:
            if child.type == 'break_statement':
                break_nodes.append(child)
            elif child.type == 'continue_statement':
                continue_nodes.append(child)
            elif child.type not in ['for_statement', 'while_statement']:
                b_nodes, c_nodes = self.get_break_continue_nodes(child)
                break_nodes.extend(b_nodes)
                continue_nodes.extend(c_nodes)
        return break_nodes, continue_nodes

    def get_edge(self, in_nodes, target_node):
        """输入入节点和目标节点，返回完整的Edge对象列表"""
        edges = []
        for in_node in in_nodes:
            parent, label = in_node
            if parent:
                edge = Edge(label=label, edge_type=EdgeType.CFG, source_node=parent, target_node=target_node)
                edges.append(edge)
        return edges
    
    def construct_cfg(self, code_or_node):
        """构建CFG - 可以接受代码字符串、函数节点或根节点"""
        try:
            # 如果传入的是字符串，先解析代码
            if isinstance(code_or_node, str):
                if self.check_syntax(code_or_node):
                    print('⚠️  CFG构建警告: 检测到语法错误，但将继续尝试构建CFG')
                node = self.parse_code(code_or_node)
            else:
                node = code_or_node
            
            # 如果传入的不是function_definition，查找第一个函数
            if node.type != 'function_definition':
                functions = self.find_functions(node)
                if not functions:
                    print('⚠️  CFG构建警告: 未找到函数定义')
                    self.cfg = None
                    return None
                func_node = functions[0]
            else:
                func_node = node
                
            cfg_edges, _ = self.create_cfg(func_node)

            # 构建图对象
            cfg = Graph()
            for node_info, edges in cfg_edges:
                cfg.add_node(node_info)
                # edges现在已经是完整的Edge对象列表，直接添加到图的边列表中
                for edge in edges:
                    if isinstance(edge, Edge):
                        cfg.edges.append(edge)

            cfg.get_def_use_info()
            self.cfg = cfg
            return cfg
        except Exception as e:
            print(f'⚠️  CFG构建警告: 函数处理失败: {e}')
            self.cfg = None
            return None
    
    def see_cfg(self, code: str, filename: str = 'CFG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化单个函数的CFG"""
        try:
            cfg = self.construct_cfg(code)
            if cfg:
                visualize_cfg([cfg], filename, pdf, dot_format, view)
            return cfg
        except Exception as e:
            print(f'⚠️  CFG构建警告: 代码解析失败: {e}')
            self.cfg = None
            return None
    
    def print_cfg_edges(self):
        """打印CFG的边信息，格式：语句A (序号) --> 语句B (序号)"""
        if not hasattr(self, 'cfg') or not self.cfg:
            print("CFG未构建，请先调用construct_cfg()")
            return
        
        print("=== CFG 边信息 ===")
        if not self.cfg.edges:
            print("该图没有边")
            return
            
        for i, edge in enumerate(self.cfg.edges, 1):
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
                
                print(f"{i:3d}. {source_text} ({source_id}) --> {target_text} ({target_id})")
            else:
                print(f"{i:3d}. [无效边: 缺少源节点或目标节点]")
        
        print(f"\n总计: {len(self.cfg.edges)} 条边")
    
    def print_statement_defs_uses(self):
        """打印CFG中每条语句的defs和uses信息"""
        if not hasattr(self, 'cfg') or not self.cfg:
            print("CFG未构建，请先调用construct_cfg()")
            return
        
        print("=== CFG 语句的 Defs 和 Uses 信息 ===")
        if not self.cfg.nodes:
            print("该图没有节点")
            return
        
        # 按行号排序节点
        sorted_nodes = sorted(self.cfg.nodes, key=lambda node: node.line)
        
        for i, node in enumerate(sorted_nodes, 1):
            # 获取语句文本，限制长度
            stmt_text = node.text.strip().replace('\n', ' ')
            if len(stmt_text) > 60:
                stmt_text = stmt_text[:57] + "..."
            
            # 格式化defs和uses
            defs_str = ', '.join(sorted(node.defs)) if node.defs else "无"
            uses_str = ', '.join(sorted(node.uses)) if node.uses else "无"
            
            print(f"{i:3d}. 行{node.line:3d}: {stmt_text}")
            print(f"     Defs: {defs_str}")
            print(f"     Uses: {uses_str}")
            print()
        
        print(f"总计: {len(sorted_nodes)} 个语句节点")


def main():
    """主函数 - 演示CFG的使用"""
    # 示例C代码
    sample_code = """
    int factorial(int n) {
        int result = 1;
        if (n <= 1) {
            return result;
        } else {
            for (int i = 2; i <= n; i++) {
                result = result * i;
            }
            return result;
        }
    }
    """
    
    print("=== CFG构建器演示 ===")
    print("示例代码:")
    print(sample_code)
    print("\n" + "="*50)
    
    # 创建CFG构建器
    cfg_builder = CFG(language="c")
    
    # 构建CFG
    print("\n1. 构建控制流图...")
    cfg = cfg_builder.construct_cfg(sample_code)
    
    if cfg:
        print("✅ CFG构建成功!")
        print(f"   节点数量: {len(cfg.nodes)}")
        print(f"   边数量: {len(cfg.edges)}")
        
        # 打印CFG边信息
        print("\n2. CFG边信息:")
        cfg_builder.print_cfg_edges()
        
        # 打印语句的defs和uses信息
        print("\n3. 语句的Defs/Uses信息:")
        cfg_builder.print_statement_defs_uses()
        
        # 生成可视化文件
        print("\n4. 生成可视化文件...")
        try:
            cfg_builder.see_cfg(sample_code, filename="example_cfg", pdf=True, dot_format=True, view=False)
            print("✅ 可视化文件已生成: example_cfg.pdf 和 example_cfg.dot")
        except Exception as e:
            print(f"⚠️  可视化生成失败: {e}")
    else:
        print("❌ CFG构建失败")
    
    print("\n" + "="*50)
    print("演示完成!")


if __name__ == "__main__":
    main()
