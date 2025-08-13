#!/usr/bin/env python3
"""
程序依赖图(PDG)构建器

结合控制流图(CFG)和数据依赖图(DDG)构建程序依赖图
"""

from typing import List, Dict, Optional
from .cfg import CFG
from .cdg import CDG
from .ddg import DDG
from .graph import Graph, Edge
from .node import Node
from .visualization import visualize_pdg


class PDG(CFG):
    """程序依赖图构建器 - 单函数版本"""
    
    def __init__(self, language: str = "c"):
        """初始化PDG构建器"""
        super().__init__(language)
        self.pdg: Optional[Graph] = None  # 单个PDG图
    
    def construct_pdg(self, code: str) -> Optional[Graph]:
        """构建程序依赖图 - 单函数版本"""
        try:
            # 构建CDG和DDG
            cdg_builder = CDG(self.language_name)
            ddg_builder = DDG(self.language_name)
            
            cdg_graph = cdg_builder.construct_cdg(code)
            ddg_graph = ddg_builder.construct_ddg(code)
            
            if not cdg_graph or not ddg_graph:
                print('⚠️  PDG构建警告: CDG或DDG构建失败')
                self.pdg = None
                return None
            
            try:
                pdg = Graph()
                
                # 复制所有节点
                for node in cdg_graph.nodes:
                    pdg.add_node(node)
                
                # 复制控制依赖边
                for edge in cdg_graph.edges:
                    pdg.edges.append(edge)
                
                # 添加数据依赖边
                for edge in ddg_graph.edges:
                    pdg.edges.append(edge)
                
                self.pdg = pdg
                return pdg
            except Exception as e:
                print(f'⚠️  PDG构建警告: 图合并失败: {e}')
                self.pdg = None
                return None
        except Exception as e:
            print(f'⚠️  PDG构建警告: CDG/DDG构建失败: {e}')
            self.pdg = None
            return None
    
    def see_pdg(self, code: str, filename: str = 'PDG', pdf: bool = True, dot_format: bool = True, view: bool = False):
        """可视化PDG - 单函数版本"""
        pdg = self.construct_pdg(code)
        if pdg:
            visualize_pdg([pdg], filename, pdf, dot_format, view)  # 传入单元素列表以兼容可视化函数
        return pdg
    
    def get_dependencies(self, code: str) -> Optional[Dict]:
        """
        获取程序依赖信息 - 单函数版本
        Returns:
            单个函数的依赖信息
        """
        pdg = self.construct_pdg(code)
        if not pdg:
            return None
        
        func_deps = {
            'nodes': len(pdg.nodes),
            'control_dependencies': [],
            'data_dependencies': []
        }
        
        for edge in pdg.edges:
            if edge.target_node and edge.source_node:
                source_node = edge.source_node
                target_node = edge.target_node
                
                dep_info = {
                    'source': {
                        'id': source_node.id,
                        'line': source_node.line,
                        'text': source_node.text,
                        'type': source_node.type
                    },
                    'target': {
                        'id': target_node.id,
                        'line': target_node.line,
                        'text': target_node.text,
                        'type': target_node.type
                    }
                }
                
                if edge.type == 'DDG':
                    dep_info['variables'] = edge.token
                    func_deps['data_dependencies'].append(dep_info)
                elif edge.type == 'CDG':
                    func_deps['control_dependencies'].append(dep_info)
        
        return func_deps
    
    def analyze_function_complexity(self, code: str) -> Optional[Dict]:
        """分析函数复杂度 - 单函数版本"""
        pdg = self.construct_pdg(code)
        if not pdg:
            return None
        
        func_info = {
            'nodes': len(pdg.nodes),
            'control_dependencies': 0,
            'data_dependencies': 0,
            'total_dependencies': 0
        }
        
        for edge in pdg.edges:
            if edge.type == 'DDG':
                func_info['data_dependencies'] += 1
            elif edge.type == 'CDG':
                func_info['control_dependencies'] += 1
                func_info['total_dependencies'] += 1
        
        return func_info
    
    def print_pdg_edges(self):
        """打印PDG的边信息，格式：语句A (序号) --> 语句B (序号) [类型]"""
        if not hasattr(self, 'pdg') or not self.pdg:
            print("PDG未构建，请先调用construct_pdg()")
            return
        
        print("=== PDG 边信息 ===")
        if not self.pdg.edges:
            print("该图没有边")
            return
            
        # 按边类型分组统计
        control_edges = []
        data_edges = []
        other_edges = []
        
        for edge in self.pdg.edges:
            if hasattr(edge, 'type'):
                if edge.type.name == 'CDG':
                    control_edges.append(edge)
                elif edge.type.name == 'DDG':
                    data_edges.append(edge)
                else:
                    other_edges.append(edge)
            else:
                other_edges.append(edge)
        
        edge_count = 1
        
        # 打印控制依赖边
        if control_edges:
            print("\n--- 控制依赖边 (CDG) ---")
            for edge in control_edges:
                if edge.source_node and edge.target_node:
                    source_text = edge.source_node.text.strip().replace('\n', ' ')
                    target_text = edge.target_node.text.strip().replace('\n', ' ')
                    source_id = edge.source_node.id
                    target_id = edge.target_node.id
                    
                    # 限制文本长度
                    if len(source_text) > 50:
                        source_text = source_text[:47] + "..."
                    if len(target_text) > 50:
                        target_text = target_text[:47] + "..."
                    
                    label_info = f" [{edge.label}]" if hasattr(edge, 'label') and edge.label else ""
                    print(f"{edge_count:3d}. {source_text} ({source_id}) --> {target_text} ({target_id}) [控制依赖]{label_info}")
                    edge_count += 1
        
        # 打印数据依赖边
        if data_edges:
            print("\n--- 数据依赖边 (DDG) ---")
            for edge in data_edges:
                if edge.source_node and edge.target_node:
                    source_text = edge.source_node.text.strip().replace('\n', ' ')
                    target_text = edge.target_node.text.strip().replace('\n', ' ')
                    source_id = edge.source_node.id
                    target_id = edge.target_node.id
                    
                    # 限制文本长度
                    if len(source_text) > 50:
                        source_text = source_text[:47] + "..."
                    if len(target_text) > 50:
                        target_text = target_text[:47] + "..."
                    
                    # 显示依赖的变量信息
                    variables = []
                    if hasattr(edge, 'variables') and edge.variables:
                        variables = edge.variables
                    elif hasattr(edge, 'token') and edge.token:
                        variables = edge.token
                    
                    var_info = f" [变量: {', '.join(variables)}]" if variables else ""
                    print(f"{edge_count:3d}. {source_text} ({source_id}) --> {target_text} ({target_id}) [数据依赖]{var_info}")
                    edge_count += 1
        
        # 打印其他类型边
        if other_edges:
            print("\n--- 其他类型边 ---")
            for edge in other_edges:
                if edge.source_node and edge.target_node:
                    source_text = edge.source_node.text.strip().replace('\n', ' ')
                    target_text = edge.target_node.text.strip().replace('\n', ' ')
                    source_id = edge.source_node.id
                    target_id = edge.target_node.id
                    
                    # 限制文本长度
                    if len(source_text) > 50:
                        source_text = source_text[:47] + "..."
                    if len(target_text) > 50:
                        target_text = target_text[:47] + "..."
                    
                    edge_type = edge.type.name if hasattr(edge, 'type') and hasattr(edge.type, 'name') else "未知"
                    print(f"{edge_count:3d}. {source_text} ({source_id}) --> {target_text} ({target_id}) [{edge_type}]")
                    edge_count += 1
        
        print(f"\n总计: {len(self.pdg.edges)} 条边 (控制依赖: {len(control_edges)}, 数据依赖: {len(data_edges)}, 其他: {len(other_edges)})")



