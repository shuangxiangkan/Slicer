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
                                       max_depth: int = None) -> bool:
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
            
            # 不再过滤外部函数，保留所有依赖
            # existing_functions = set(self.call_graph.functions.keys())
            # related_functions = related_functions.intersection(existing_functions)
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title=f"Call Graph - {func_name} Callees (Total: {len(related_functions)-1})",
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
                                       max_depth: int = None) -> bool:
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
            
            # 不再过滤外部函数，保留所有调用者
            # existing_functions = set(self.call_graph.functions.keys())
            # related_functions = related_functions.intersection(existing_functions)
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title=f"Call Graph - {func_name} Callers (Total: {len(related_functions)-1})",
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
                                   max_depth: int = None) -> bool:
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
            
            # 不再过滤外部函数，保留所有相关函数
            # existing_functions = set(self.call_graph.functions.keys())
            # related_functions = related_functions.intersection(existing_functions)
            
            # 计算callees和callers数量
            callees_count = len(dependencies)
            callers_count = len(dependents)
            
            # 生成DOT内容
            dot_content = self._generate_dot_content(
                title=f"Call Graph - {func_name} Complete ({callers_count} Callers + {callees_count} Callees)",
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
        
        # 获取所有函数定义，用于判断函数是否有函数体
        all_functions = self.analyzer.get_functions()
        functions_with_definition = {f.name: f for f in all_functions}
        
        for func_name in sorted(selected_functions):
            escaped_name = self._escape_dot_string(func_name)
            
            if func_name in functions_with_definition:
                # 有函数定义的函数：显示完整签名
                func_info = functions_with_definition[func_name]
                signature = self._get_function_signature_simple(func_info)
                
                # 如果是中心函数，高亮显示
                if center_function and func_name == center_function:
                    lines.append(f'    "{escaped_name}" [label="{signature}", style=filled, fillcolor=lightcoral];')
                else:
                    lines.append(f'    "{escaped_name}" [label="{signature}"];')
            else:
                # 真正的外部函数（如strlen等）：只显示函数名
                if center_function and func_name == center_function:
                    lines.append(f'    "{escaped_name}" [label="{escaped_name}", style=filled, fillcolor=lightcoral];')
                else:
                    lines.append(f'    "{escaped_name}" [label="{escaped_name}"];')
        
        lines.append("")
        
        # 生成边定义
        lines.append("    // Call relationships")
        edges = set()
        for func_name in selected_functions:
            if func_name in self.call_graph.functions:
                # 获取直接调用的函数
                callees = self.analyzer.get_direct_callees(func_name)
                for callee in callees:
                    if callee in selected_functions:
                        edges.add((func_name, callee))
            # 对于外部函数，我们无法获取其调用关系，所以跳过
        
        for caller, callee in sorted(edges):
            escaped_caller = self._escape_dot_string(caller)
            escaped_callee = self._escape_dot_string(callee)
            lines.append(f'    "{escaped_caller}" -> "{escaped_callee}";')
        
        lines.append("}")
        
        return "\n".join(lines)
    
    def _escape_dot_string(self, text: str) -> str:
        """转义DOT字符串中的特殊字符"""
        # 转义引号和反斜杠
        text = text.replace('\\', '\\\\')
        text = text.replace('"', '\\"')
        text = text.replace('\n', '\\n')
        text = text.replace('\r', '\\r')
        text = text.replace('\t', '\\t')
        return text
    
    def _get_function_signature_simple(self, func_info) -> str:
        """获取简化的函数签名，适用于DOT格式"""
        # 构建返回类型
        return_type = "void"
        if hasattr(func_info, 'return_type') and func_info.return_type:
            return_type = func_info.return_type.strip()
        
        # 构建参数列表
        params = []
        if hasattr(func_info, 'parameters') and func_info.parameters:
            for param in func_info.parameters:
                clean_param = param.strip()
                # 移除过长的参数描述，只保留类型和名称
                if len(clean_param) > 30:
                    clean_param = clean_param[:27] + "..."
                params.append(clean_param)
        
        # 构建简化的函数签名
        func_name = func_info.name
        
        # 限制参数显示长度
        if not params:
            signature = f"{return_type} {func_name}()"
        elif len(params) == 1:
            signature = f"{return_type} {func_name}({params[0]})"
        elif len(params) <= 3:
            params_str = ", ".join(params)
            if len(params_str) > 60:
                # 如果参数太长，分行显示
                signature = f"{return_type} {func_name}(\\n  " + "\\n  ".join(params) + "\\n)"
            else:
                signature = f"{return_type} {func_name}({params_str})"
        else:
            # 参数太多，只显示前2个
            signature = f"{return_type} {func_name}({params[0]}, {params[1]}, ...)"
        
        # 转义DOT字符串
        return self._escape_dot_string(signature)

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
            signature = f"{return_type} {func_name_bold}"
            signature += f"<BR/>()"
        elif len(params) == 1:
            # 单参数函数，在函数名和括号间添加空格
            signature = f"{return_type} {func_name_bold}<BR/>({params[0]})"
        else:
            # 多参数函数，每个参数换行显示
            signature = f"{return_type} {func_name_bold}<BR/>(<BR/>"
            for i, param in enumerate(params):
                if i == 0:
                    signature += f"&nbsp;&nbsp;&nbsp;&nbsp;{param}"
                else:
                    signature += f",<BR/>&nbsp;&nbsp;&nbsp;&nbsp;{param}"
            signature += "<BR/>)"
        
        return signature 