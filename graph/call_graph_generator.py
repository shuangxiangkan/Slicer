#!/usr/bin/env python3
"""
简化的Call Graph DOT文件生成器
"""

import os
from typing import Set, Dict, List
from parser.repo_analyzer import RepoAnalyzer


class CallGraphGenerator:
    """简化的Call Graph DOT文件生成器"""
    
    def __init__(self, analyzer: RepoAnalyzer):
        self.analyzer = analyzer
        self.call_graph = analyzer.get_call_graph()
        
    def generate_repo_call_graph(self, output_file: str) -> bool:
        """生成整个仓库的Call Graph DOT文件"""
        try:
            # 获取所有函数
            all_functions = set(self.call_graph.functions.keys())
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title="Repository Call Graph",
                selected_functions=all_functions
            )
            
            # 写入文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成仓库Call Graph失败: {e}")
            return False
    
    def generate_function_callees_graph(self, func_name: str, output_file: str, 
                                       max_depth: int = 2) -> bool:
        """生成函数的所有callees图（直接和间接调用的函数）"""
        try:
            if func_name not in self.call_graph.functions:
                print(f"❌ 函数 {func_name} 不存在")
                return False
            
            # 收集相关函数（只包含callees）
            related_functions = {func_name}
            
            # 添加所有依赖的函数（直接和间接callees）
            dependencies = self.analyzer.get_function_dependencies(func_name, max_depth)
            related_functions.update(dependencies.keys())
            
            # 只保留在当前分析范围内的函数
            existing_functions = set(self.call_graph.functions.keys())
            related_functions = related_functions.intersection(existing_functions)
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title=f"Call Graph - {func_name} Callees",
                selected_functions=related_functions,
                center_function=func_name
            )
            
            # 写入文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成函数 {func_name} 的Callees Graph失败: {e}")
            return False
    
    def generate_function_callers_graph(self, func_name: str, output_file: str, 
                                       max_depth: int = 2) -> bool:
        """生成函数的所有callers图（直接和间接调用该函数的函数）"""
        try:
            if func_name not in self.call_graph.functions:
                print(f"❌ 函数 {func_name} 不存在")
                return False
            
            # 收集相关函数（只包含callers）
            related_functions = {func_name}
            
            # 添加所有调用该函数的函数（直接和间接callers）
            dependents = self.analyzer.get_function_dependents(func_name, max_depth)
            related_functions.update(dependents.keys())
            
            # 只保留在当前分析范围内的函数
            existing_functions = set(self.call_graph.functions.keys())
            related_functions = related_functions.intersection(existing_functions)
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title=f"Call Graph - {func_name} Callers",
                selected_functions=related_functions,
                center_function=func_name
            )
            
            # 写入文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成函数 {func_name} 的Callers Graph失败: {e}")
            return False
    
    def generate_function_call_graph(self, func_name: str, output_file: str, 
                                   max_depth: int = 2) -> bool:
        """生成函数的完整Call Graph（包含所有callers和callees）"""
        try:
            if func_name not in self.call_graph.functions:
                print(f"❌ 函数 {func_name} 不存在")
                return False
            
            # 收集相关函数（调用者和被调用者）
            related_functions = {func_name}
            
            # 添加所有依赖的函数（callees）
            dependencies = self.analyzer.get_function_dependencies(func_name, max_depth)
            related_functions.update(dependencies.keys())
            
            # 添加所有调用该函数的函数（callers）
            dependents = self.analyzer.get_function_dependents(func_name, max_depth)
            related_functions.update(dependents.keys())
            
            # 只保留在当前分析范围内的函数
            existing_functions = set(self.call_graph.functions.keys())
            related_functions = related_functions.intersection(existing_functions)
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title=f"Call Graph - {func_name} Complete",
                selected_functions=related_functions,
                center_function=func_name
            )
            
            # 写入文件
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(dot_content)
            
            return True
            
        except Exception as e:
            print(f"❌ 生成函数 {func_name} 的Complete Call Graph失败: {e}")
            return False
    
    def _generate_dot_content(self, title: str, selected_functions: Set[str],
                            center_function: str = None) -> str:
        """生成DOT格式内容"""
        
        lines = []
        
        # DOT文件头部
        lines.append("digraph CallGraph {")
        lines.append("    rankdir=TB;")
        lines.append("    node [shape=box];")
        lines.append("")
        
        # 图表标题
        lines.append(f'    label="{title}";')
        lines.append("    labelloc=t;")
        lines.append("    fontsize=14;")
        lines.append("")
        
        # 生成节点定义
        lines.append("    // Function nodes")
        for func_name in sorted(selected_functions):
            if func_name in self.call_graph.functions:
                func_info = self.call_graph.functions[func_name]
                signature = self._get_function_signature(func_info)
                
                # 如果是中心函数，高亮显示
                if center_function and func_name == center_function:
                    lines.append(f'    "{func_name}" [label=<{signature}>, style=filled, fillcolor=lightcoral];')
                else:
                    lines.append(f'    "{func_name}" [label=<{signature}>];')
        
        lines.append("")
        
        # 生成边定义
        lines.append("    // Call relationships")
        edges = set()
        for func_name in selected_functions:
            if func_name in self.call_graph.functions:
                callees = self.analyzer.get_direct_callees(func_name)
                for callee in callees:
                    if callee in selected_functions:
                        edges.add((func_name, callee))
        
        for caller, callee in sorted(edges):
            lines.append(f'    "{caller}" -> "{callee}";')
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _get_function_signature(self, func_info) -> str:
        """获取函数签名，函数名加粗显示，参数每行一个"""
        # 构建返回类型
        return_type = "void"
        if hasattr(func_info, 'return_type') and func_info.return_type:
            return_type = func_info.return_type
        
        # 构建参数列表
        params = []
        if hasattr(func_info, 'parameters') and func_info.parameters:
            for param in func_info.parameters:
                params.append(param.strip())
        
        # 构建函数名（加粗）
        func_name_bold = f"<B>{func_info.name}</B>"
        
        # 构建完整签名
        if not params:
            # 无参数函数
            signature = f"{return_type} {func_name_bold} (void)"
        elif len(params) == 1:
            # 单参数函数，在函数名和括号间添加空格
            signature = f"{return_type} {func_name_bold} ({params[0]})"
        else:
            # 多参数函数，每个参数换行显示
            signature = f"{return_type} {func_name_bold}   (<BR/>"
            for i, param in enumerate(params):
                if i == 0:
                    signature += f"&nbsp;&nbsp;&nbsp;&nbsp;{param}"
                else:
                    signature += f",<BR/>&nbsp;&nbsp;&nbsp;&nbsp;{param}"
            signature += "<BR/>)"
        
        return signature 