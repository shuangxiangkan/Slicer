#!/usr/bin/env python3
"""
仓库分析器 - 基于用户配置文件的C/C++代码分析工具（核心分析逻辑）
"""

import time
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from .file_finder import FileFinder
from .function_extractor import FunctionExtractor
from .function_info import FunctionInfo
from .type_registry import TypeRegistry
from .type_extractor import TypeExtractor
from .config_parser import ConfigParser
from .summary import AnalysisSummary

# 配置logging
logger = logging.getLogger(__name__)


class RepoAnalyzer:
    """代码仓库分析器（核心分析功能）"""
    
    def __init__(self, config_path: str):
        """
        初始化分析器
        
        Args:
            config_path: 用户配置文件路径
        """
        self.file_finder = FileFinder()
        
        # 初始化类型注册表和相关组件
        self.type_registry = TypeRegistry()
        self.type_extractor = TypeExtractor(self.type_registry)
        self.function_extractor = FunctionExtractor(self.type_registry)
        
        self.all_functions = []
        self.analysis_stats = {}
        self.processed_files = []
        
        # 解析配置文件
        self.config_parser = ConfigParser(config_path)
    
    def analyze(self, show_progress: bool = True) -> Dict:
        """
        根据配置文件分析代码库
        
        Args:
            show_progress: 是否显示进度信息
            
        Returns:
            分析结果字典
        """
        start_time = time.time()
        
        if show_progress:
            print("🔍 开始基于配置文件的代码分析")
            self.config_parser.print_config_summary()
            print("=" * 80)
        
        logger.info("开始基于配置文件的代码分析")
        
        # 1. 收集所有文件
        if show_progress:
            print("📂 正在收集C/C++文件...")
        
        try:
            files = self._collect_files()
                
        except Exception as e:
            error_msg = f"收集文件时出错: {e}"
            logger.error(error_msg)
            if show_progress:
                print(f"错误: {error_msg}")
            return {}
        
        if not files:
            logger.warning("未找到任何C/C++文件")
            if show_progress:
                print("❌ 未找到任何C/C++文件")
            return {}
        
        self.processed_files = files
        logger.info(f"找到 {len(files)} 个文件")
        
        if show_progress:
            # 使用summary模块显示文件统计
            summary = AnalysisSummary([], {})
            summary.print_file_stats(files)
        
        # 2. 提取类型定义
        if show_progress:
            print("🔍 正在提取类型定义...")
        
        self._extract_types(files, show_progress)
        
        # 3. 提取函数
        if show_progress:
            print("🔧 正在提取函数定义...")
        
        self.all_functions, failed_files = self._extract_functions(files, show_progress)
        
        # 4. 生成统计信息
        duration = time.time() - start_time
        self.analysis_stats = self._generate_statistics(files, failed_files, duration)
        
        if show_progress:
            print("\n" + "=" * 80)
            print("📊 分析完成！")
            # 使用summary模块显示摘要
            summary = AnalysisSummary(self.all_functions, self.analysis_stats)
            summary.print_summary()
        
        logger.info(f"分析完成，用时 {duration:.2f} 秒，找到 {len(self.all_functions)} 个函数")
        
        return self.analysis_stats
    
    def _collect_files(self) -> List[str]:
        """收集需要分析的文件"""
        all_files = []
        analysis_targets = self.config_parser.get_analysis_targets()
        
        for target_path in analysis_targets:
            if not os.path.exists(target_path):
                logger.warning(f"目标路径不存在: {target_path}")
                continue
            
            if os.path.isfile(target_path):
                # 单个文件
                if self._is_supported_file(target_path):
                    all_files.append(target_path)
            else:
                # 目录
                files = self.file_finder.find_files(target_path, recursive=True)
                all_files.extend(files)
        
        # 应用排除规则
        return self._apply_exclusions(all_files)
    
    def _extract_functions(self, files: List[str], show_progress: bool = False) -> tuple[List[FunctionInfo], List]:
        """提取函数定义"""
        all_functions = []
        failed_files = []
        
        for i, file_path in enumerate(files, 1):
            try:
                if show_progress:
                    # 显示相对路径，更清晰
                    rel_path = self._get_relative_path(file_path)
                    print(f"  处理文件 {i}/{len(files)}: {rel_path}", end="")
                
                functions = self.function_extractor.extract_from_file(file_path)
                all_functions.extend(functions)
                
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
        
        return all_functions, failed_files
    
    def _is_supported_file(self, file_path: str) -> bool:
        """检查是否为支持的C/C++文件"""
        return self.file_finder._is_c_cpp_file(Path(file_path))
    
    def _apply_exclusions(self, files: List[str]) -> List[str]:
        """应用排除规则过滤文件"""
        exclude_targets = self.config_parser.get_exclude_targets()
        if not exclude_targets:
            return files
        
        filtered_files = []
        exclude_paths_abs = [os.path.abspath(path) for path in exclude_targets]
        
        for file_path in files:
            abs_file_path = os.path.abspath(file_path)
            should_exclude = False
            
            for exclude_path in exclude_paths_abs:
                if os.path.isfile(exclude_path):
                    # 排除特定文件
                    if abs_file_path == exclude_path:
                        should_exclude = True
                        break
                else:
                    # 排除目录下的所有文件
                    if abs_file_path.startswith(exclude_path + os.sep) or abs_file_path == exclude_path:
                        should_exclude = True
                        break
            
            if not should_exclude:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def _extract_types(self, files: List[str], show_progress: bool = False) -> None:
        """提取类型定义"""
        type_count = 0
        
        for i, file_path in enumerate(files, 1):
            try:
                if show_progress:
                    rel_path = self._get_relative_path(file_path)
                    print(f"  分析类型 {i}/{len(files)}: {rel_path}", end="")
                
                # 读取文件内容
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 判断是否为C++文件
                is_cpp = any(file_path.endswith(ext) for ext in ['.cpp', '.cxx', '.cc', '.hpp', '.hxx', '.hh'])
                
                # 选择合适的解析器
                parser = self.function_extractor.cpp_parser if is_cpp else self.function_extractor.c_parser
                
                # 解析代码
                tree = parser.parse(content.encode('utf-8'))
                root_node = tree.root_node
                
                # 提取类型定义
                self.type_extractor.extract_from_content(content, root_node, file_path)
                
                # 从预处理器指令中提取类型（如#define的类型别名）
                self.type_extractor.extract_from_preprocessor(content)
                
                if show_progress:
                    print(f" -> OK")
                
            except Exception as e:
                logger.error(f"提取类型定义失败 {file_path}: {e}")
                if show_progress:
                    print(f" -> 失败: {e}")
        
        # 获取类型统计
        type_stats = self.type_registry.get_statistics()
        type_count = type_stats.get('total_types', 0)
        
        if show_progress:
            print(f"✅ 类型提取完成，找到 {type_count} 个类型定义")
            self._print_type_summary()
    
    def _print_type_summary(self):
        """打印类型摘要"""
        stats = self.type_registry.get_statistics()
        
        print("📋 类型统计:")
        print(f"  • 总计: {stats.get('total_types', 0)} 个类型")
        print(f"  • typedef: {stats.get('typedef', 0)} 个")
        print(f"  • 结构体: {stats.get('struct', 0)} 个")
        print(f"  • 联合体: {stats.get('union', 0)} 个")
        print(f"  • 枚举: {stats.get('enum', 0)} 个")
        print(f"  • 指针typedef: {stats.get('pointer_typedefs', 0)} 个")
    
    def _get_relative_path(self, file_path: str) -> str:
        """获取相对路径显示"""
        try:
            # 尝试相对于库路径
            library_path = self.config_parser.get_library_path()
            return os.path.relpath(file_path, library_path)
        except ValueError:
            # 如果无法计算相对路径，返回文件名
            return os.path.basename(file_path)
    
    def _generate_statistics(self, files: List[str], failed_files: List, duration: float) -> Dict:
        """生成分析统计信息"""
        total_functions = len(self.all_functions)
        definitions = len([f for f in self.all_functions if not f.is_declaration])
        declarations = len([f for f in self.all_functions if f.is_declaration])
        
        # 检测重复函数
        function_names = {}
        for func in self.all_functions:
            key = (func.name, func.is_declaration)
            if key not in function_names:
                function_names[key] = []
            function_names[key].append(func)
        
        duplicate_functions = {k: v for k, v in function_names.items() if len(v) > 1}
        
        # 获取类型统计
        type_stats = self.type_registry.get_statistics()
        
        stats = {
            'total_files': len(files),
            'processed_files': len(files) - len(failed_files),
            'failed_files': len(failed_files),
            'total_functions': total_functions,
            'function_definitions': definitions,
            'function_declarations': declarations,
            'duplicate_functions': len(duplicate_functions),
            'processing_time': duration,
            'files_per_second': len(files) / duration if duration > 0 else 0,
            'failed_file_list': failed_files,
            'duplicate_function_details': duplicate_functions,
            # 新增：类型统计信息
            'type_statistics': type_stats
        }
        
        return stats
    
    def search_functions(self, pattern: str, case_sensitive: bool = False) -> List[FunctionInfo]:
        """搜索函数"""
        if not case_sensitive:
            pattern = pattern.lower()
        
        matched_functions = []
        for func in self.all_functions:
            search_text = func.name if case_sensitive else func.name.lower()
            if pattern in search_text:
                matched_functions.append(func)
        
        return matched_functions
    
    def get_summary(self) -> AnalysisSummary:
        """获取分析结果的展示对象"""
        return AnalysisSummary(self.all_functions, self.analysis_stats)
    
    def get_functions(self) -> List[FunctionInfo]:
        """获取所有找到的函数"""
        return self.all_functions
    
    def get_stats(self) -> Dict[str, Any]:
        """获取分析统计信息"""
        return self.analysis_stats
    
    def get_processed_files(self) -> List[str]:
        """获取已处理的文件列表"""
        return self.processed_files
    
    def get_function_by_name(self, function_name: str, exact_match: bool = True) -> List[FunctionInfo]:
        """
        根据函数名获取函数信息
        
        Args:
            function_name: 要查找的函数名
            exact_match: 是否精确匹配，False时进行模糊匹配
            
        Returns:
            匹配的函数信息列表
        """
        matches = []
        for func in self.all_functions:
            if exact_match:
                if func.name == function_name:
                    matches.append(func)
            else:
                if function_name.lower() in func.name.lower():
                    matches.append(func)
        return matches
    
    def get_function_body(self, function_name: str, exact_match: bool = True) -> Dict[str, str]:
        """
        根据函数名获取函数体内容
        
        Args:
            function_name: 要查找的函数名
            exact_match: 是否精确匹配
            
        Returns:
            字典，键为函数的唯一标识，值为函数体内容
        """
        matches = self.get_function_by_name(function_name, exact_match)
        result = {}
        
        for func in matches:
            # 创建唯一标识：函数名_文件名_行号
            import os
            file_name = os.path.basename(func.file_path)
            key = f"{func.name}_{file_name}_{func.start_line}"
            
            body = func.get_body()
            if body is not None:
                result[key] = body
        
        return result
    
    def get_type_registry(self) -> TypeRegistry:
        """获取类型注册表"""
        return self.type_registry
    
    def lookup_type(self, type_name: str) -> Optional[Dict]:
        """查找类型信息"""
        type_info = self.type_registry.lookup_type(type_name)
        return type_info.to_dict() if type_info else None
    
    def get_type_statistics(self) -> Dict:
        """获取类型统计信息"""
        return self.type_registry.get_statistics()
    
    def print_type_info(self, type_name: str):
        """打印类型详细信息"""
        self.type_registry.print_type_info(type_name)
    
    def export_all_types(self) -> Dict:
        """导出所有类型信息"""
        return self.type_registry.export_types()
 