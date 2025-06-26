#!/usr/bin/env python3
"""
分析结果展示和报告生成器
"""

import os
import logging
from typing import List, Dict, Any
from .function_info import FunctionInfo

# 配置logging
logger = logging.getLogger(__name__)


class AnalysisSummary:
    """分析结果展示和报告生成器"""
    
    def __init__(self, functions: List[FunctionInfo], stats: Dict[str, Any]):
        self.functions = functions
        self.stats = stats
    
    def print_summary(self):
        """打印分析摘要"""
        print(f"⏱️  处理时间: {self.stats['processing_time']:.2f} 秒")
        print(f"📁 处理文件: {self.stats['processed_files']}/{self.stats['total_files']}")
        print(f"🎯 总函数数: {self.stats['total_functions']}")
        print(f"   - 函数定义: {self.stats['function_definitions']}")
        print(f"   - 函数声明: {self.stats['function_declarations']}")
        
        if self.stats['duplicate_functions'] > 0:
            print(f"⚠️  重复函数: {self.stats['duplicate_functions']}")
        
        if self.stats['failed_files'] > 0:
            print(f"❌ 失败文件: {self.stats['failed_files']}")
    
    def print_all_functions(self, group_by_file: bool = True, show_details: bool = True, 
                           show_full_path: bool = False):
        """打印所有找到的函数"""
        if not self.functions:
            print("❌ 没有找到任何函数")
            return
        
        if group_by_file:
            # 按文件分组
            files_functions = {}
            for func in self.functions:
                file_path = func.file_path or "Unknown"
                if file_path not in files_functions:
                    files_functions[file_path] = []
                files_functions[file_path].append(func)
            
            print(f"\n📋 所有函数列表 ({len(self.functions)} 个函数):")
            print("=" * 80)
            
            for file_path, functions in files_functions.items():
                if show_full_path:
                    display_path = file_path
                else:
                    display_path = os.path.basename(file_path)
                    
                definitions = len([f for f in functions if not f.is_declaration])
                declarations = len([f for f in functions if f.is_declaration])
                
                print(f"\n📁 {display_path}")
                print(f"   ({definitions} 个定义 + {declarations} 个声明 = {len(functions)} 个函数)")
                print("-" * 60)
                
                for i, func in enumerate(functions, 1):
                    func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
                    if show_details:
                        print(f"{i:3}. {func_type} {func.return_type} {func.name}({func.parameters})")
                        print(f"     📍 第{func.start_line}-{func.end_line}行")
                    else:
                        print(f"{i:3}. {func_type} {func.name}")
        else:
            # 不分组，直接列出
            print(f"\n📋 所有函数列表 ({len(self.functions)} 个函数):")
            print("=" * 80)
            
            for i, func in enumerate(self.functions, 1):
                func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
                if show_full_path:
                    file_display = func.file_path
                else:
                    file_display = os.path.basename(func.file_path or "Unknown")
                
                if show_details:
                    print(f"{i:3}. {func_type} {func.return_type} {func.name}({func.parameters})")
                    print(f"     📁 {file_display}:{func.start_line}")
                else:
                    print(f"{i:3}. {func_type} {func.name} - {file_display}")
    
    def print_search_results(self, pattern: str, matches: List[FunctionInfo], max_display: int = 10):
        """打印搜索结果"""
        if not matches:
            print(f"🔍 搜索 '{pattern}': 未找到匹配的函数")
            return
        
        print(f"🔍 搜索 '{pattern}': 找到 {len(matches)} 个匹配函数")
        
        # 显示前几个匹配结果
        display_count = min(len(matches), max_display)
        for i, func in enumerate(matches[:display_count], 1):
            func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
            file_name = os.path.basename(func.file_path) if func.file_path else "Unknown"
            print(f"  {i:2}. {func_type} {func.name} - {file_name}:{func.start_line}")
        
        if len(matches) > max_display:
            print(f"     ... 还有 {len(matches) - max_display} 个匹配结果")
    
    def print_duplicate_functions(self):
        """打印重复函数信息"""
        duplicates = self.stats.get('duplicate_function_details', {})
        if not duplicates:
            print("✅ 没有发现重复函数")
            return
        
        print(f"\n⚠️  发现 {len(duplicates)} 组重复函数:")
        print("=" * 80)
        
        for (func_name, is_declaration), func_list in duplicates.items():
            func_type = "声明" if is_declaration else "定义"
            print(f"\n🔄 函数: {func_name} ({func_type}了 {len(func_list)} 次)")
            print("-" * 60)
            
            for i, func in enumerate(func_list, 1):
                file_display = os.path.basename(func.file_path) if func.file_path else "Unknown"
                print(f"  {i}. 📁 {file_display}:{func.start_line}-{func.end_line}")
                print(f"     {func.return_type} {func.name}({func.parameters})")
    
    def print_file_stats(self, files: List[str]):
        """打印文件统计信息"""
        file_stats = self._get_file_stats(files)
        
        print(f"✅ 找到 {file_stats['total_files']} 个文件")
        print(f"   - C文件: {file_stats['c_files']}")
        print(f"   - C++文件: {file_stats['cpp_files']}")
        print(f"   - 头文件: {file_stats['header_files']}")
        print()
    
    def _get_file_stats(self, files: List[str]) -> Dict[str, int]:
        """获取文件统计信息"""
        from pathlib import Path
        
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
    
    def save_analysis_report(self, output_file: str):
        """保存分析报告到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# C/C++ 代码仓库函数分析报告\n\n")
                
                # 统计信息
                f.write("## 分析统计\n\n")
                f.write(f"- 处理时间: {self.stats['processing_time']:.2f} 秒\n")
                f.write(f"- 处理文件: {self.stats['processed_files']}/{self.stats['total_files']}\n")
                f.write(f"- 总函数数: {self.stats['total_functions']}\n")
                f.write(f"- 函数定义: {self.stats['function_definitions']}\n")
                f.write(f"- 函数声明: {self.stats['function_declarations']}\n\n")
                
                # 函数列表
                f.write("## 函数列表\n\n")
                
                files_functions = {}
                for func in self.functions:
                    file_path = func.file_path if func.file_path else "Unknown"
                    if file_path not in files_functions:
                        files_functions[file_path] = []
                    files_functions[file_path].append(func)
                
                for file_path, functions in sorted(files_functions.items()):
                    f.write(f"### {file_path}\n\n")
                    
                    for func in functions:
                        decl_type = "声明" if func.is_declaration else "定义"
                        f.write(f"- **{func.name}** ({decl_type})\n")
                        f.write(f"  - 签名: `{func.get_signature()}`\n")
                        f.write(f"  - 位置: 第{func.start_line}-{func.end_line}行\n")
                        if func.scope:
                            f.write(f"  - 作用域: {func.scope}\n")
                        f.write("\n")
                
                # 重复函数
                duplicates = self.stats.get('duplicate_function_details', {})
                if duplicates:
                    f.write("## 重复函数\n\n")
                    for (func_name, is_declaration), func_list in duplicates.items():
                        f.write(f"### {func_name} ({'声明' if is_declaration else '定义'})\n\n")
                        for i, func in enumerate(func_list, 1):
                            f.write(f"- {func.file_path}:{func.start_line}-{func.end_line}\n")
                        f.write("\n")
            
            logger.info(f"分析报告已保存到: {output_file}")
            print(f"✅ 分析报告已保存到: {output_file}")
            
        except Exception as e:
            error_msg = f"保存报告失败: {e}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
    
    def save_json_report(self, output_file: str):
        """保存JSON格式的分析报告"""
        import json
        
        try:
            # 构建JSON数据
            report_data = {
                "analysis_stats": self.stats,
                "functions": []
            }
            
            # 转换函数信息为字典
            for func in self.functions:
                func_data = {
                    "name": func.name,
                    "return_type": func.return_type,
                    "parameters": func.parameters,
                    "start_line": func.start_line,
                    "end_line": func.end_line,
                    "file_path": func.file_path,
                    "is_declaration": func.is_declaration,
                    "scope": func.scope,
                    "signature": func.get_signature()
                }
                report_data["functions"].append(func_data)
            
            # 保存JSON文件
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"JSON报告已保存到: {output_file}")
            print(f"✅ JSON报告已保存到: {output_file}")
            
        except Exception as e:
            error_msg = f"保存JSON报告失败: {e}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")

    def print_function_body(self, function_name: str, functions: List[FunctionInfo], 
                           exact_match: bool = True, show_metadata: bool = True) -> None:
        """
        打印函数体内容（格式化输出）
        
        Args:
            function_name: 要查找的函数名
            functions: 所有函数列表
            exact_match: 是否精确匹配
            show_metadata: 是否显示函数元信息
        """
        # 查找匹配的函数
        matches = []
        for func in functions:
            if exact_match:
                if func.name == function_name:
                    matches.append(func)
            else:
                if function_name.lower() in func.name.lower():
                    matches.append(func)
        
        if not matches:
            print(f"❌ 未找到函数: {function_name}")
            return
        
        print(f"🔍 找到 {len(matches)} 个匹配的函数:")
        print("=" * 80)
        
        for i, func in enumerate(matches, 1):
            func_type = "🔧 函数定义" if not func.is_declaration else "🔗 函数声明"
            file_name = os.path.basename(func.file_path) if func.file_path else "Unknown"
            
            print(f"\n[{i}/{len(matches)}] {func_type}: {func.name}")
            
            if show_metadata:
                print(f"📁 文件: {file_name}:{func.start_line}-{func.end_line}")
                print(f"🏷️  签名: {func.get_signature()}")
                if func.scope:
                    print(f"📂 作用域: {func.scope}")
            
            print("=" * 60)
            
            body = func.get_body()
            if body is not None:
                print(body)
            else:
                print("❌ 无法读取函数体内容")
            
            print("=" * 60)
            
            # 如果有多个匹配且不是最后一个，询问是否继续
            if i < len(matches):
                response = input("\n按回车键继续显示下一个函数，或输入 'q' 退出: ")
                if response.lower() == 'q':
                    break

    def export_function_bodies(self, function_names: List[str], functions: List[FunctionInfo], 
                              output_file: str = None) -> Dict[str, str]:
        """
        导出多个函数的函数体到文件或返回字典
        
        Args:
            function_names: 函数名列表
            functions: 所有函数列表
            output_file: 输出文件路径，如果为None则不保存文件
            
        Returns:
            包含所有函数体的字典
        """
        import time
        all_bodies = {}
        
        for func_name in function_names:
            # 查找匹配的函数
            for func in functions:
                if func.name == func_name:
                    # 创建唯一标识：函数名_文件名_行号
                    file_name = os.path.basename(func.file_path)
                    key = f"{func.name}_{file_name}_{func.start_line}"
                    
                    body = func.get_body()
                    if body is not None:
                        all_bodies[key] = body
        
        if output_file:
            try:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write("# 函数体导出结果\n")
                    f.write(f"# 导出时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"# 总函数数: {len(all_bodies)}\n\n")
                    
                    for key, body in all_bodies.items():
                        f.write(f"## {key}\n")
                        f.write("```c\n")
                        f.write(body)
                        f.write("\n```\n\n")
                
                print(f"✅ 函数体已导出到: {output_file}")
            except Exception as e:
                print(f"❌ 导出失败: {e}")
        
        return all_bodies

    def get_function_by_name(self, function_name: str, functions: List[FunctionInfo], 
                            exact_match: bool = True) -> List[FunctionInfo]:
        """
        根据函数名获取函数信息
        
        Args:
            function_name: 要查找的函数名
            functions: 所有函数列表
            exact_match: 是否精确匹配，False时进行模糊匹配
            
        Returns:
            匹配的函数信息列表
        """
        matches = []
        for func in functions:
            if exact_match:
                if func.name == function_name:
                    matches.append(func)
            else:
                if function_name.lower() in func.name.lower():
                    matches.append(func)
        return matches