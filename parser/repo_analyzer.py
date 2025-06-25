#!/usr/bin/env python3
"""
仓库分析器 - 对整个代码仓库进行函数分析
"""

import os
import time
from pathlib import Path
from typing import List, Dict, Optional
from .file_finder import FileFinder
from .function_extractor import FunctionExtractor, FunctionInfo


class RepoAnalyzer:
    """代码仓库分析器"""
    
    def __init__(self):
        self.file_finder = FileFinder()
        self.function_extractor = FunctionExtractor()
        self.all_functions = []
        self.analysis_stats = {}
    
    def analyze_repository(self, repo_path: str, recursive: bool = True, 
                          show_progress: bool = True) -> Dict:
        """
        分析整个代码仓库
        
        Args:
            repo_path: 仓库路径
            recursive: 是否递归搜索子目录
            show_progress: 是否显示进度
            
        Returns:
            分析结果字典
        """
        print(f"🔍 开始分析代码仓库: {repo_path}")
        print("=" * 80)
        
        start_time = time.time()
        
        # 1. 查找所有C/C++文件
        print("📂 正在搜索C/C++文件...")
        try:
            files = self.file_finder.find_files(repo_path, recursive)
        except Exception as e:
            print(f"错误: 搜索文件时出错: {e}")
            return {}
        
        if not files:
            print("❌ 未找到任何C/C++文件")
            return {}
        
        file_stats = self.file_finder.get_file_stats()
        print(f"✅ 找到 {file_stats['total_files']} 个文件")
        print(f"   - C文件: {file_stats['c_files']}")
        print(f"   - C++文件: {file_stats['cpp_files']}")
        print(f"   - 头文件: {file_stats['header_files']}")
        print()
        
        # 2. 提取函数定义
        print("🔧 正在提取函数定义...")
        self.all_functions = []
        failed_files = []
        
        for i, file_path in enumerate(files, 1):
            if show_progress:
                print(f"  处理文件 {i}/{len(files)}: {Path(file_path).name}", end="")
            
            try:
                functions = self.function_extractor.extract_from_file(file_path)
                self.all_functions.extend(functions)
                
                if show_progress:
                    print(f" -> 找到 {len(functions)} 个函数")
                    
            except Exception as e:
                failed_files.append((file_path, str(e)))
                if show_progress:
                    print(f" -> 失败: {e}")
        
        end_time = time.time()
        
        # 3. 生成分析统计
        self.analysis_stats = self._generate_statistics(files, failed_files, end_time - start_time)
        
        print("\n" + "=" * 80)
        print("📊 分析完成！")
        self._print_summary()
        
        return {
            'functions': self.all_functions,
            'stats': self.analysis_stats,
            'files': files,
            'failed_files': failed_files
        }
    
    def _generate_statistics(self, files: List[str], failed_files: List, duration: float) -> Dict:
        """生成分析统计信息"""
        file_function_count = {}
        definitions = [f for f in self.all_functions if not f.is_declaration]
        declarations = [f for f in self.all_functions if f.is_declaration]
        
        # 按文件统计函数数量
        for func in self.all_functions:
            file_name = Path(func.file_path).name if func.file_path else "Unknown"
            if file_name not in file_function_count:
                file_function_count[file_name] = {'definitions': 0, 'declarations': 0}
            
            if func.is_declaration:
                file_function_count[file_name]['declarations'] += 1
            else:
                file_function_count[file_name]['definitions'] += 1
        
        # 按函数名统计（找重复定义）
        function_names = {}
        for func in definitions:
            full_name = f"{func.scope}::{func.name}" if func.scope else func.name
            if full_name not in function_names:
                function_names[full_name] = []
            function_names[full_name].append(func)
        
        duplicate_functions = {name: funcs for name, funcs in function_names.items() if len(funcs) > 1}
        
        return {
            'total_files': len(files),
            'successful_files': len(files) - len(failed_files),
            'failed_files': len(failed_files),
            'total_functions': len(self.all_functions),
            'function_definitions': len(definitions),
            'function_declarations': len(declarations),
            'file_function_count': file_function_count,
            'duplicate_functions': duplicate_functions,
            'processing_time': duration
        }
    
    def _print_summary(self):
        """打印分析摘要"""
        stats = self.analysis_stats
        
        print(f"⏱️  处理时间: {stats['processing_time']:.2f} 秒")
        print(f"📁 处理文件: {stats['successful_files']}/{stats['total_files']}")
        if stats['failed_files'] > 0:
            print(f"❌ 失败文件: {stats['failed_files']}")
        
        print(f"🎯 总函数数: {stats['total_functions']}")
        print(f"   - 函数定义: {stats['function_definitions']}")
        print(f"   - 函数声明: {stats['function_declarations']}")
        
        if stats['duplicate_functions']:
            print(f"⚠️  重复函数: {len(stats['duplicate_functions'])}")
    
    def print_all_functions(self, group_by_file: bool = True, show_details: bool = True):
        """打印所有找到的函数"""
        if not self.all_functions:
            print("❌ 没有找到任何函数")
            return
        
        print(f"\n📋 所有函数列表 ({len(self.all_functions)} 个函数):")
        print("=" * 80)
        
        if group_by_file:
            self._print_functions_by_file(show_details)
        else:
            self._print_functions_flat(show_details)
    
    def _print_functions_by_file(self, show_details: bool):
        """按文件分组打印函数"""
        files_functions = {}
        for func in self.all_functions:
            file_name = Path(func.file_path).name if func.file_path else "Unknown"
            if file_name not in files_functions:
                files_functions[file_name] = []
            files_functions[file_name].append(func)
        
        for file_name, functions in sorted(files_functions.items()):
            print(f"\n📁 {file_name} ({len(functions)} 个函数)")
            print("-" * 60)
            
            for i, func in enumerate(functions, 1):
                decl_marker = "🔗" if func.is_declaration else "🔧"
                print(f"{i:3d}. {decl_marker} {func.get_signature()}")
                
                if show_details:
                    print(f"     📍 第{func.start_line}-{func.end_line}行")
                    if func.scope:
                        print(f"     🏷️  作用域: {func.scope}")
    
    def _print_functions_flat(self, show_details: bool):
        """平铺打印所有函数"""
        for i, func in enumerate(self.all_functions, 1):
            file_name = Path(func.file_path).name if func.file_path else "Unknown"
            decl_marker = "🔗" if func.is_declaration else "🔧"
            
            print(f"{i:3d}. {decl_marker} {func.get_signature()}")
            if show_details:
                print(f"     📁 {file_name}:{func.start_line}-{func.end_line}")
                if func.scope:
                    print(f"     🏷️  作用域: {func.scope}")
                print()
    
    def print_duplicate_functions(self):
        """打印重复的函数定义"""
        duplicates = self.analysis_stats.get('duplicate_functions', {})
        
        if not duplicates:
            print("✅ 没有发现重复的函数定义")
            return
        
        print(f"\n⚠️  发现 {len(duplicates)} 个重复函数:")
        print("=" * 80)
        
        for func_name, functions in duplicates.items():
            print(f"\n🔄 函数: {func_name} (定义了 {len(functions)} 次)")
            print("-" * 60)
            
            for i, func in enumerate(functions, 1):
                file_name = Path(func.file_path).name if func.file_path else "Unknown"
                print(f"  {i}. 📁 {file_name}:{func.start_line}-{func.end_line}")
                print(f"     {func.get_signature()}")
    
    def search_functions(self, pattern: str, case_sensitive: bool = False) -> List[FunctionInfo]:
        """搜索函数名匹配指定模式的函数"""
        import re
        
        flags = 0 if case_sensitive else re.IGNORECASE
        regex = re.compile(pattern, flags)
        
        matched_functions = []
        for func in self.all_functions:
            if regex.search(func.name):
                matched_functions.append(func)
        
        return matched_functions
    
    def save_analysis_report(self, output_file: str):
        """保存分析报告到文件"""
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# C/C++ 代码仓库函数分析报告\n\n")
                
                # 统计信息
                stats = self.analysis_stats
                f.write("## 分析统计\n\n")
                f.write(f"- 处理时间: {stats['processing_time']:.2f} 秒\n")
                f.write(f"- 处理文件: {stats['successful_files']}/{stats['total_files']}\n")
                f.write(f"- 总函数数: {stats['total_functions']}\n")
                f.write(f"- 函数定义: {stats['function_definitions']}\n")
                f.write(f"- 函数声明: {stats['function_declarations']}\n\n")
                
                # 函数列表
                f.write("## 函数列表\n\n")
                
                files_functions = {}
                for func in self.all_functions:
                    file_name = Path(func.file_path).name if func.file_path else "Unknown"
                    if file_name not in files_functions:
                        files_functions[file_name] = []
                    files_functions[file_name].append(func)
                
                for file_name, functions in sorted(files_functions.items()):
                    f.write(f"### {file_name}\n\n")
                    
                    for func in functions:
                        decl_type = "声明" if func.is_declaration else "定义"
                        f.write(f"- **{func.name}** ({decl_type})\n")
                        f.write(f"  - 签名: `{func.get_signature()}`\n")
                        f.write(f"  - 位置: 第{func.start_line}-{func.end_line}行\n")
                        if func.scope:
                            f.write(f"  - 作用域: {func.scope}\n")
                        f.write("\n")
                
                # 重复函数
                duplicates = stats.get('duplicate_functions', {})
                if duplicates:
                    f.write("## 重复函数\n\n")
                    for func_name, functions in duplicates.items():
                        f.write(f"### {func_name}\n\n")
                        for func in functions:
                            file_name = Path(func.file_path).name
                            f.write(f"- {file_name}:{func.start_line}-{func.end_line}\n")
                        f.write("\n")
            
            print(f"✅ 分析报告已保存到: {output_file}")
            
        except Exception as e:
            print(f"❌ 保存报告失败: {e}")


def main():
    """命令行入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='C/C++ 代码仓库函数分析工具')
    parser.add_argument('path', help='要分析的文件或目录路径')
    parser.add_argument('--no-recursive', action='store_true', help='不递归搜索子目录')
    parser.add_argument('--no-progress', action='store_true', help='不显示处理进度')
    parser.add_argument('--no-details', action='store_true', help='不显示详细信息')
    parser.add_argument('--flat', action='store_true', help='平铺显示函数，不按文件分组')
    parser.add_argument('--search', type=str, help='搜索函数名匹配的模式')
    parser.add_argument('--case-sensitive', action='store_true', help='区分大小写搜索')
    parser.add_argument('--report', type=str, help='保存分析报告到指定文件')
    parser.add_argument('--duplicates-only', action='store_true', help='只显示重复的函数')
    
    args = parser.parse_args()
    
    # 创建分析器
    analyzer = RepoAnalyzer()
    
    # 执行分析
    try:
        result = analyzer.analyze_repository(
            args.path, 
            recursive=not args.no_recursive,
            show_progress=not args.no_progress
        )
        
        if not result:
            return
        
        # 处理搜索
        if args.search:
            print(f"\n🔍 搜索函数名包含 '{args.search}' 的函数:")
            matched = analyzer.search_functions(args.search, args.case_sensitive)
            if matched:
                analyzer.function_extractor.print_functions(matched, not args.no_details)
            else:
                print("❌ 没有找到匹配的函数")
            return
        
        # 显示重复函数
        if args.duplicates_only:
            analyzer.print_duplicate_functions()
            return
        
        # 显示所有函数
        analyzer.print_all_functions(
            group_by_file=not args.flat, 
            show_details=not args.no_details
        )
        
        # 显示重复函数
        analyzer.print_duplicate_functions()
        
        # 保存报告
        if args.report:
            analyzer.save_analysis_report(args.report)
            
    except KeyboardInterrupt:
        print("\n❌ 用户中断分析")
    except Exception as e:
        print(f"❌ 分析出错: {e}")


if __name__ == "__main__":
    main() 