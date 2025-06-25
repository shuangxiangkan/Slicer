#!/usr/bin/env python3
"""
仓库分析器 - 综合的C/C++代码仓库分析工具
"""

import time
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from .file_finder import FileFinder
from .function_extractor import FunctionExtractor, FunctionInfo

# 配置logging
logger = logging.getLogger(__name__)


class RepoAnalyzer:
    """代码仓库分析器"""
    
    def __init__(self):
        self.file_finder = FileFinder()
        self.function_extractor = FunctionExtractor()
        self.all_functions = []
        self.analysis_stats = {}
    
    def analyze_repository(self, repo_path: str, recursive: bool = True, 
                          show_progress: bool = True,
                          include_patterns: Optional[List[str]] = None,
                          exclude_patterns: Optional[List[str]] = None) -> Dict:
        """
        分析代码仓库
        
        Args:
            repo_path: 仓库路径
            recursive: 是否递归搜索
            show_progress: 是否显示进度信息
            include_patterns: 包含的文件/目录模式列表 (支持通配符)
            exclude_patterns: 排除的文件/目录模式列表 (支持通配符)
            
        Returns:
            分析结果字典
        """
        start_time = time.time()
        
        if show_progress:
            print(f"🔍 开始分析代码仓库: {repo_path}")
            if include_patterns:
                print(f"📋 包含模式: {include_patterns}")
            if exclude_patterns:
                print(f"🚫 排除模式: {exclude_patterns}")
            print("=" * 80)
        
        logger.info(f"开始分析代码仓库: {repo_path}")
        
        # 1. 搜索文件
        if show_progress:
            print("📂 正在搜索C/C++文件...")
        
        try:
            files = self.file_finder.find_files(repo_path, recursive)
            
            # 应用用户指定的包含/排除模式
            if include_patterns or exclude_patterns:
                files = self._filter_files(files, include_patterns, exclude_patterns)
                
        except Exception as e:
            error_msg = f"搜索文件时出错: {e}"
            logger.error(error_msg)
            if show_progress:
                print(f"错误: {error_msg}")
            return {}
        
        if not files:
            logger.warning("未找到任何C/C++文件")
            if show_progress:
                print("❌ 未找到任何C/C++文件")
            return {}
        
        file_stats = self._get_filtered_file_stats(files)
        logger.info(f"找到 {file_stats['total_files']} 个文件")
        
        if show_progress:
            print(f"✅ 找到 {file_stats['total_files']} 个文件")
            print(f"   - C文件: {file_stats['c_files']}")
            print(f"   - C++文件: {file_stats['cpp_files']}")
            print(f"   - 头文件: {file_stats['header_files']}")
            print()
        
        # 2. 提取函数
        if show_progress:
            print("🔧 正在提取函数定义...")
        
        self.all_functions = []
        failed_files = []
        
        for i, file_path in enumerate(files, 1):
            try:
                if show_progress:
                    # 显示相对路径，更清晰
                    rel_path = self._get_relative_path(file_path, repo_path)
                    print(f"  处理文件 {i}/{len(files)}: {rel_path}", end="")
                
                functions = self.function_extractor.extract_from_file(file_path)
                self.all_functions.extend(functions)
                
                if show_progress:
                    # 分别显示定义和声明的数量
                    definitions = len([f for f in functions if not f.is_declaration])
                    declarations = len([f for f in functions if f.is_declaration])
                    print(f" -> {definitions}定义 + {declarations}声明 = {len(functions)}函数")
                
                logger.debug(f"处理文件 {file_path}: 找到 {len(functions)} 个函数")
                
            except Exception as e:
                failed_files.append((file_path, str(e)))
                logger.error(f"处理文件 {file_path} 失败: {e}")
                if show_progress:
                    print(f" -> 失败: {e}")
        
        # 3. 生成统计信息
        duration = time.time() - start_time
        self.analysis_stats = self._generate_statistics(files, failed_files, duration)
        
        if show_progress:
            print("\n" + "=" * 80)
            print("📊 分析完成！")
            self._print_summary()
        
        logger.info(f"分析完成，用时 {duration:.2f} 秒，找到 {len(self.all_functions)} 个函数")
        
        return self.analysis_stats
    
    def _filter_files(self, files: List[str], include_patterns: Optional[List[str]] = None,
                     exclude_patterns: Optional[List[str]] = None) -> List[str]:
        """根据用户指定的模式过滤文件"""
        import fnmatch
        
        filtered_files = files[:]
        
        # 应用包含模式（如果指定）
        if include_patterns:
            included_files = []
            for file_path in filtered_files:
                file_obj = Path(file_path)
                # 检查文件名或路径是否匹配任何包含模式
                if any(fnmatch.fnmatch(file_obj.name, pattern) or 
                      fnmatch.fnmatch(str(file_obj), pattern) or
                      any(fnmatch.fnmatch(part, pattern) for part in file_obj.parts)
                      for pattern in include_patterns):
                    included_files.append(file_path)
            filtered_files = included_files
        
        # 应用排除模式（如果指定）
        if exclude_patterns:
            excluded_files = []
            for file_path in filtered_files:
                file_obj = Path(file_path)
                # 检查文件名或路径是否匹配任何排除模式
                should_exclude = any(fnmatch.fnmatch(file_obj.name, pattern) or 
                                   fnmatch.fnmatch(str(file_obj), pattern) or
                                   any(fnmatch.fnmatch(part, pattern) for part in file_obj.parts)
                                   for pattern in exclude_patterns)
                if not should_exclude:
                    excluded_files.append(file_path)
            filtered_files = excluded_files
        
        return filtered_files
    
    def _get_filtered_file_stats(self, files: List[str]) -> dict:
        """获取过滤后文件的统计信息"""
        stats = {
            'total_files': len(files),
            'c_files': 0,
            'cpp_files': 0,
            'header_files': 0,
        }
        
        for file_path in files:
            ext = Path(file_path).suffix.lower()
            if ext == '.c':
                stats['c_files'] += 1
            elif ext in {'.cpp', '.cxx', '.cc'}:
                stats['cpp_files'] += 1
            elif ext in {'.h', '.hpp', '.hxx', '.hh'}:
                stats['header_files'] += 1
        
        return stats
    
    def _get_relative_path(self, file_path: str, base_path: str) -> str:
        """获取相对于基础路径的相对路径"""
        try:
            return str(Path(file_path).relative_to(Path(base_path)))
        except ValueError:
            # 如果无法获取相对路径，返回文件名
            return Path(file_path).name
    
    def _generate_statistics(self, files: List[str], failed_files: List, duration: float) -> Dict:
        """生成分析统计信息"""
        
        # 基本统计
        definitions = [f for f in self.all_functions if not f.is_declaration]
        declarations = [f for f in self.all_functions if f.is_declaration]
        
        # 检测重复函数定义
        function_names = {}
        for func in definitions:
            full_name = f"{func.scope}::{func.name}" if func.scope else func.name
            if full_name not in function_names:
                function_names[full_name] = []
            function_names[full_name].append(func)
        
        # 找出重复定义
        duplicate_functions = {name: funcs for name, funcs in function_names.items() 
                             if len(funcs) > 1}
        
        stats = {
            'processing_time': duration,
            'total_files': len(files),
            'successful_files': len(files) - len(failed_files),
            'failed_files': len(failed_files),
            'failed_file_list': failed_files,
            'total_functions': len(self.all_functions),
            'function_definitions': len(definitions),
            'function_declarations': len(declarations),
            'duplicate_functions': duplicate_functions,
            'unique_function_names': len(function_names),
        }
        
        return stats
    
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
    
    def print_all_functions(self, group_by_file: bool = True, show_details: bool = True,
                           show_full_path: bool = True):
        """打印所有找到的函数"""
        if not self.all_functions:
            print("❌ 没有找到任何函数")
            return
        
        print(f"\n📋 所有函数列表 ({len(self.all_functions)} 个函数):")
        print("=" * 80)
        
        if group_by_file:
            self._print_functions_by_file(show_details, show_full_path)
        else:
            self._print_functions_flat(show_details, show_full_path)
    
    def _print_functions_by_file(self, show_details: bool, show_full_path: bool):
        """按文件分组打印函数"""
        files_functions = {}
        for func in self.all_functions:
            file_path = func.file_path if func.file_path else "Unknown"
            if file_path not in files_functions:
                files_functions[file_path] = []
            files_functions[file_path].append(func)
        
        for file_path, functions in sorted(files_functions.items()):
            # 根据选项显示完整路径或文件名
            display_name = file_path if show_full_path else Path(file_path).name
            
            # 统计定义和声明
            definitions = [f for f in functions if not f.is_declaration]
            declarations = [f for f in functions if f.is_declaration]
            
            print(f"\n📁 {display_name}")
            print(f"   ({len(definitions)} 个定义 + {len(declarations)} 个声明 = {len(functions)} 个函数)")
            print("-" * 60)
            
            for i, func in enumerate(functions, 1):
                func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
                print(f"{i:3d}. {func_type} {func.get_signature()}")
                
                if show_details:
                    print(f"     📍 第{func.start_line}-{func.end_line}行")
                    if func.scope:
                        print(f"     🏷️  作用域: {func.scope}")
    
    def _print_functions_flat(self, show_details: bool, show_full_path: bool):
        """平铺打印所有函数"""
        for i, func in enumerate(self.all_functions, 1):
            file_path = func.file_path if func.file_path else "Unknown"
            display_name = file_path if show_full_path else Path(file_path).name
            
            func_type = "🔧 定义" if not func.is_declaration else "🔗 声明"
            
            print(f"{i:3d}. {func_type} {func.get_signature()}")
            if show_details:
                print(f"     📁 {display_name}:{func.start_line}-{func.end_line}")
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
                print(f"  {i}. 📁 {func.file_path}:{func.start_line}-{func.end_line}")
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
        
        logger.info(f"搜索模式 '{pattern}' 找到 {len(matched_functions)} 个匹配函数")
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
                duplicates = stats.get('duplicate_functions', {})
                if duplicates:
                    f.write("## 重复函数\n\n")
                    for func_name, functions in duplicates.items():
                        f.write(f"### {func_name}\n\n")
                        for func in functions:
                            f.write(f"- {func.file_path}:{func.start_line}-{func.end_line}\n")
                        f.write("\n")
            
            logger.info(f"分析报告已保存到: {output_file}")
            print(f"✅ 分析报告已保存到: {output_file}")
            
        except Exception as e:
            error_msg = f"保存报告失败: {e}"
            logger.error(error_msg)
            print(f"❌ {error_msg}") 