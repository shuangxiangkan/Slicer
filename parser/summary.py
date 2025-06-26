#!/usr/bin/env python3
"""
分析结果展示和报告生成器
"""

import os
import logging
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from .function_info import FunctionInfo

# 配置logging
logger = logging.getLogger(__name__)


class AnalysisSummary:
    """分析结果展示和报告生成器"""
    
    def __init__(self, functions: List[FunctionInfo], stats: Dict[str, Any], processing_time: float = 0.0):
        self.functions = functions
        self.stats = stats
        self.processing_time = processing_time
    
    def print_summary(self, show_details: bool = True):
        """打印分析摘要"""
        print(f"✅ 分析成功完成!")
        print(f"📁 处理文件: {self.stats.get('files_processed', 0)}/{self.stats.get('total_files', 0)}")
        print(f"🎯 总函数数: {self.stats.get('total_functions', 0)}")
        print(f"🔧 函数定义: {self.stats.get('function_definitions', 0)}")
        print(f"🔗 函数声明: {self.stats.get('function_declarations', 0)}")
        print(f"⏱️  处理时间: {self.processing_time:.3f}秒")
        
        if show_details and self.functions:
            print(f"\n📊 详细统计:")
            self._print_detailed_stats()
    
    def _print_detailed_stats(self):
        """打印详细统计信息"""
        definitions = [f for f in self.functions if not f.is_declaration]
        
        if not definitions:
            print("   无函数定义")
            return
        
        # 文件分布
        files_count = {}
        for func in definitions:
            file_name = Path(func.file_path).name if func.file_path else "Unknown"
            files_count[file_name] = files_count.get(file_name, 0) + 1
        
        print(f"   文件分布: {dict(files_count)}")
        
        # 作用域分布
        scopes = [func.scope for func in definitions if func.scope]
        if scopes:
            scope_count = {}
            for scope in scopes:
                scope_count[scope] = scope_count.get(scope, 0) + 1
            print(f"   作用域: {dict(scope_count)}")
    
    def print_file_stats(self, files: List[str]):
        """打印文件统计信息"""
        file_stats = self._get_file_stats(files)
        
        print(f"✅ 找到 {file_stats['total_files']} 个文件")
        print(f"   - C文件: {file_stats['c_files']}")
        print(f"   - C++文件: {file_stats['cpp_files']}")
        print(f"   - 头文件: {file_stats['header_files']}")
        print()
    
    def _get_file_stats(self, files: List[str]) -> dict:
        """获取文件统计信息"""
        stats = {
            'total_files': len(files),
            'c_files': 0,
            'cpp_files': 0,
            'header_files': 0
        }
        
        for file_path in files:
            file_obj = Path(file_path)
            suffix = file_obj.suffix.lower()
            
            if suffix == '.c':
                stats['c_files'] += 1
            elif suffix in {'.cpp', '.cxx', '.cc'}:
                stats['cpp_files'] += 1
            elif suffix in {'.h', '.hpp', '.hxx', '.hh'}:
                stats['header_files'] += 1
        
        return stats
    
    def print_all_functions(self, group_by_file: bool = True, show_signatures: bool = False):
        """
        打印所有函数
        
        Args:
            group_by_file: 是否按文件分组
            show_signatures: 是否显示函数签名
        """
        if not self.functions:
            print("🚫 未找到任何函数")
            return
        
        total = len(self.functions)
        definitions = [f for f in self.functions if not f.is_declaration]
        declarations = [f for f in self.functions if f.is_declaration]
        
        print(f"📊 函数统计:")
        print(f"   总函数数: {total}")
        print(f"   函数定义: {len(definitions)}")
        print(f"   函数声明: {len(declarations)}")
        
        print(f"\n📋 所有函数列表 ({total} 个函数):")
        print("=" * 80)
        
        if group_by_file:
            # 按文件分组
            file_groups = {}
            for func in self.functions:
                file_name = Path(func.file_path).name if func.file_path else "Unknown"
                if file_name not in file_groups:
                    file_groups[file_name] = {'definitions': [], 'declarations': []}
                
                if func.is_declaration:
                    file_groups[file_name]['declarations'].append(func)
                else:
                    file_groups[file_name]['definitions'].append(func)
            
            for file_name, groups in file_groups.items():
                defs = groups['definitions']
                decls = groups['declarations']
                total_in_file = len(defs) + len(decls)
                
                print(f"\n📁 {file_name}")
                print(f"   ({len(defs)} 个定义 + {len(decls)} 个声明 = {total_in_file} 个函数)")
                print("-" * 60)
                
                # 合并并排序
                all_funcs = []
                for func in defs:
                    all_funcs.append((func, "🔧 定义"))
                for func in decls:
                    all_funcs.append((func, "🔗 声明"))
                
                # 按行号排序
                all_funcs.sort(key=lambda x: x[0].start_line)
                
                for i, (func, func_type) in enumerate(all_funcs, 1):
                    if show_signatures:
                        print(f"{i:3}. {func_type} {func.get_signature()}")
                    else:
                        print(f"{i:3}. {func_type} {func.name}")
        else:
            # 不分组，直接列出所有函数
            for i, func in enumerate(self.functions, 1):
                func_type = "🔗 声明" if func.is_declaration else "🔧 定义"
                if show_signatures:
                    print(f"{i:3}. {func_type} {func.get_signature()}")
                else:
                    print(f"{i:3}. {func_type} {func.name}")
    
    def print_function_body(self, function_name: str, functions: List[FunctionInfo] = None, 
                           exact_match: bool = False, show_metadata: bool = True):
        """
        打印指定函数的函数体
        
        Args:
            function_name: 函数名
            functions: 函数列表，如果为None则使用self.functions
            exact_match: 是否精确匹配
            show_metadata: 是否显示元数据
        """
        if functions is None:
            functions = self.functions
        
        matches = self.get_function_by_name(function_name, functions, exact_match)
        
        if not matches:
            print(f"❌ 未找到函数: {function_name}")
            return
        
        print(f"🔍 找到 {len(matches)} 个匹配的函数:")
        print("=" * 80)
        
        for i, func in enumerate(matches, 1):
            print(f"\n[{i}/{len(matches)}] {'🔧 函数定义' if not func.is_declaration else '🔗 函数声明'}: {func.name}")
            print(f"📁 文件: {Path(func.file_path).name}:{func.start_line}-{func.end_line}")
            
            if show_metadata:
                print(f"🏷️  签名: {func.get_signature()}")
                if func.scope:
                    print(f"📂 作用域: {func.scope}")
            
            print("=" * 60)
            
            # 获取函数体
            body = func.get_body()
            if body:
                print(body)
            else:
                print("❌ 无法读取函数体内容")
            
            print("=" * 60)
            
            # 如果有多个匹配，询问是否继续
            if i < len(matches):
                choice = input("\n按回车键继续显示下一个函数，或输入 'q' 退出: ").strip().lower()
                if choice == 'q':
                    break
    
    def get_function_by_name(self, function_name: str, functions: List[FunctionInfo] = None, 
                            exact_match: bool = False) -> List[FunctionInfo]:
        """
        根据函数名查找函数
        
        Args:
            function_name: 函数名
            functions: 函数列表，如果为None则使用self.functions
            exact_match: 是否精确匹配
            
        Returns:
            匹配的函数列表
        """
        if functions is None:
            functions = self.functions
        
        if exact_match:
            return [func for func in functions if func.name == function_name]
        else:
            return [func for func in functions if function_name.lower() in func.name.lower()]
    
    def export_function_bodies(self, output_file: str, functions: List[FunctionInfo] = None, 
                              include_metadata: bool = True) -> bool:
        """
        导出所有函数体到文件
        
        Args:
            output_file: 输出文件路径
            functions: 函数列表，如果为None则使用self.functions中的定义
            include_metadata: 是否包含元数据
            
        Returns:
            是否导出成功
        """
        if functions is None:
            functions = [f for f in self.functions if not f.is_declaration]
        
        try:
            export_data = {
                'export_info': {
                    'total_functions': len(functions),
                    'export_time': Path(output_file).stem,
                    'include_metadata': include_metadata
                },
                'functions': []
            }
            
            for func in functions:
                func_data = {
                    'name': func.name,
                    'body': func.get_body()
                }
                
                if include_metadata:
                    func_data.update(func.get_info_dict())
                
                export_data['functions'].append(func_data)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 成功导出 {len(functions)} 个函数到: {output_file}")
            return True
            
        except Exception as e:
            print(f"❌ 导出失败: {e}")
            return False
    
    def print_parameter_analysis(self):
        """打印参数和返回类型的详细分析"""
        definitions = [f for f in self.functions if not f.is_declaration]
        
        if not definitions:
            print("❌ 没有函数定义可以分析")
            return
        
        print(f"🔬 参数和返回类型详细分析")
        print("=" * 80)
        print(f"📊 基于 {len(definitions)} 个函数定义的分析")
        
        # 返回类型分析
        print(f"\n📤 返回类型分析:")
        print("-" * 40)
        
        return_types = {}
        pointer_returns = 0
        const_returns = 0
        
        for func in definitions:
            ret_info = func.return_type_details
            ret_type = ret_info.return_type
            
            if ret_type not in return_types:
                return_types[ret_type] = 0
            return_types[ret_type] += 1
            
            if ret_info.is_pointer:
                pointer_returns += 1
            if ret_info.is_const:
                const_returns += 1
        
        # 排序显示最常见的返回类型
        sorted_returns = sorted(return_types.items(), key=lambda x: x[1], reverse=True)
        
        print(f"最常见的返回类型:")
        for ret_type, count in sorted_returns[:10]:  # 显示前10个
            percentage = count / len(definitions) * 100
            print(f"   {ret_type}: {count} ({percentage:.1f}%)")
        
        print(f"\n返回类型特征:")
        print(f"   返回指针的函数: {pointer_returns} ({pointer_returns/len(definitions)*100:.1f}%)")
        print(f"   返回const的函数: {const_returns} ({const_returns/len(definitions)*100:.1f}%)")
        
        # 参数分析
        print(f"\n📥 参数分析:")
        print("-" * 40)
        
        total_params = 0
        param_types = {}
        pointer_params = 0
        const_params = 0
        reference_params = 0
        
        param_count_dist = {}  # 参数个数分布
        
        for func in definitions:
            param_count = len(func.parameter_details)
            if param_count not in param_count_dist:
                param_count_dist[param_count] = 0
            param_count_dist[param_count] += 1
            
            for param in func.parameter_details:
                total_params += 1
                
                param_type = param.param_type
                if param_type not in param_types:
                    param_types[param_type] = 0
                param_types[param_type] += 1
                
                if param.is_actually_pointer():
                    pointer_params += 1
                if param.is_const:
                    const_params += 1
                if param.is_reference:
                    reference_params += 1
        
        print(f"参数统计:")
        print(f"   总参数数: {total_params}")
        print(f"   平均每个函数参数数: {total_params/len(definitions):.1f}")
        
        print(f"\n参数个数分布:")
        sorted_param_counts = sorted(param_count_dist.items())
        for count, funcs in sorted_param_counts:
            percentage = funcs / len(definitions) * 100
            print(f"   {count}个参数: {funcs} 个函数 ({percentage:.1f}%)")
        
        if total_params > 0:
            print(f"\n参数类型特征:")
            print(f"   指针参数: {pointer_params} ({pointer_params/total_params*100:.1f}%)")
            print(f"   const参数: {const_params} ({const_params/total_params*100:.1f}%)")
            print(f"   引用参数: {reference_params} ({reference_params/total_params*100:.1f}%)")
            
            # 最常见的参数类型
            sorted_param_types = sorted(param_types.items(), key=lambda x: x[1], reverse=True)
            print(f"\n最常见的参数类型:")
            for param_type, count in sorted_param_types[:10]:
                percentage = count / total_params * 100
                print(f"   {param_type}: {count} ({percentage:.1f}%)")
        
        # 复杂函数分析
        print(f"\n🎯 复杂函数分析:")
        print("-" * 40)
        
        functions_with_pointers = [f for f in definitions if f.has_pointer_params()]
        functions_with_const = [f for f in definitions if f.has_const_params()]
        functions_returning_pointers = [f for f in definitions if f.has_pointer_return()]
        
        print(f"有指针参数的函数: {len(functions_with_pointers)} ({len(functions_with_pointers)/len(definitions)*100:.1f}%)")
        print(f"有const参数的函数: {len(functions_with_const)} ({len(functions_with_const)/len(definitions)*100:.1f}%)")
        print(f"返回指针的函数: {len(functions_returning_pointers)} ({len(functions_returning_pointers)/len(definitions)*100:.1f}%)")
        
        # 最复杂的函数（参数最多的）
        most_complex = max(definitions, key=lambda f: len(f.parameter_details))
        print(f"\n参数最多的函数: {most_complex.name} ({len(most_complex.parameter_details)} 个参数)")
        
        # 指针层级分析
        pointer_levels = {}
        typedef_pointer_levels = {}
        total_pointer_levels = {}
        
        for func in definitions:
            for param in func.parameter_details:
                # 字面指针层级
                if param.is_pointer:
                    level = param.pointer_level
                    if level not in pointer_levels:
                        pointer_levels[level] = 0
                    pointer_levels[level] += 1
                
                # typedef指针层级
                if param.typedef_is_pointer:
                    level = param.typedef_pointer_level
                    if level not in typedef_pointer_levels:
                        typedef_pointer_levels[level] = 0
                    typedef_pointer_levels[level] += 1
                
                # 总指针层级
                if param.is_actually_pointer():
                    total_level = param.get_total_pointer_level()
                    if total_level not in total_pointer_levels:
                        total_pointer_levels[total_level] = 0
                    total_pointer_levels[total_level] += 1
        
        if pointer_levels or typedef_pointer_levels or total_pointer_levels:
            print(f"\n指针层级分布:")
            
            if pointer_levels:
                print(f"  字面指针层级:")
                for level in sorted(pointer_levels.keys()):
                    count = pointer_levels[level]
                    print(f"     {level}级指针: {count} 个参数")
            
            if typedef_pointer_levels:
                print(f"  typedef指针层级:")
                for level in sorted(typedef_pointer_levels.keys()):
                    count = typedef_pointer_levels[level]
                    print(f"     {level}级指针: {count} 个参数")
            
            if total_pointer_levels:
                print(f"  总指针层级:")
                for level in sorted(total_pointer_levels.keys()):
                    count = total_pointer_levels[level]
                    print(f"     {level}级指针: {count} 个参数")
    
    def get_functions_by_criteria(self, **criteria) -> List[FunctionInfo]:
        """
        根据条件筛选函数
        
        Args:
            criteria: 筛选条件，可包含:
                - has_pointer_params: 是否有指针参数
                - has_const_params: 是否有const参数
                - has_pointer_return: 是否返回指针
                - min_params: 最少参数个数
                - max_params: 最多参数个数
                - return_type: 返回类型
                - is_declaration: 是否是声明
                
        Returns:
            符合条件的函数列表
        """
        result = self.functions.copy()
        
        if 'has_pointer_params' in criteria:
            result = [f for f in result if f.has_pointer_params() == criteria['has_pointer_params']]
        
        if 'has_const_params' in criteria:
            result = [f for f in result if f.has_const_params() == criteria['has_const_params']]
        
        if 'has_pointer_return' in criteria:
            result = [f for f in result if f.has_pointer_return() == criteria['has_pointer_return']]
        
        if 'min_params' in criteria:
            result = [f for f in result if len(f.parameter_details) >= criteria['min_params']]
        
        if 'max_params' in criteria:
            result = [f for f in result if len(f.parameter_details) <= criteria['max_params']]
        
        if 'return_type' in criteria:
            result = [f for f in result if f.return_type_details.return_type == criteria['return_type']]
        
        if 'is_declaration' in criteria:
            result = [f for f in result if f.is_declaration == criteria['is_declaration']]
        
        return result