#!/usr/bin/env python3
"""
头文件分析器 - 分析C/C++头文件的include关系
"""

import os
import logging
from typing import List, Dict, Optional
from .file_extensions import is_header_file

logger = logging.getLogger(__name__)


class IncludeInfo:
    """包含文件信息"""
    
    def __init__(self, include_path: str, line_number: int, file_path: str, 
                 is_system: bool = False):
        self.include_path = include_path
        self.line_number = line_number
        self.file_path = file_path
        self.is_system = is_system  # True: <header.h>, False: "header.h"
    
    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            'include_path': self.include_path,
            'line_number': self.line_number,
            'file_path': self.file_path,
            'is_system': self.is_system,
            'include_type': 'system' if self.is_system else 'local'
        }


class HeaderAnalyzer:
    """头文件include分析器"""
    
    def __init__(self, header_file: Optional[str] = None, config_file: Optional[str] = None):
        """初始化头文件分析器
        
        Args:
            header_file: 单个头文件路径
            config_file: 配置文件路径
        """
        self.header_file = header_file
        self.config_file = config_file
        self.config_parser = None
        self.includes = []  # 存储include信息
        self.dependency_graph = {}  # 依赖图
        
        # 配置logging
        self.logger = logging.getLogger(__name__)
    
    def analyze_single_file(self, file_path: str) -> Dict:
        """分析单个头文件的include关系"""
        if not os.path.isfile(file_path):
            return {'error': f'文件不存在: {file_path}'}
        
        if not self._is_header_file(file_path):
            return {'error': f'不是头文件: {file_path}'}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            return {'error': f'无法读取文件: {e}'}
        
        includes = self._extract_includes(content, file_path)
        
        return {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'includes': includes,
            'include_count': len(includes),
            'line_count': len(content.splitlines())
        }
    
    def analyze_file(self, file_path: str) -> Dict:
        """分析单个头文件的include关系（向后兼容）"""
        return self.analyze_single_file(file_path)
    
    def analyze_from_repo(self, config_parser, target_files: List[str] = None) -> Dict:
        """
        从repo配置分析头文件
        
        Args:
            config_parser: 配置解析器对象
            target_files: 指定要分析的头文件列表（可选）
            
        Returns:
            头文件分析结果
        """
        logger.info("开始头文件批量include分析")
        
        # 收集要分析的头文件
        header_files = self._collect_header_files_from_repo(config_parser, target_files)
        
        logger.info(f"找到 {len(header_files)} 个头文件")
        
        if not header_files:
            return {
                'message': '未找到任何头文件',
                'results': {},
                'summary': self._get_empty_summary()
            }
        
        # 批量分析
        logger.info(f"批量分析 {len(header_files)} 个头文件")
        
        analysis_result = self.analyze_files(header_files)
        analysis_result['message'] = f'成功分析 {analysis_result["summary"]["total_files"]} 个头文件'
        
        summary = analysis_result['summary']
        logger.info(f"头文件分析完成: {summary['total_includes']} 个include")
        
        return analysis_result
    
    def analyze_from_single_file_mode(self, file_path: str) -> Dict:
        """
        单文件模式分析
        
        Args:
            file_path: 头文件路径
            
        Returns:
            头文件分析结果
        """
        logger.info("开始单头文件include分析")
        
        # 检查是否是头文件
        if not self._is_header_file(file_path):
            return {
                'message': '不是头文件',
                'results': {},
                'summary': {
                    'total_files': 0,
                    'total_includes': 0,
                    'system_includes': 0,
                    'local_includes': 0,
                    'errors': ['不是头文件']
                }
            }
        
        logger.info("找到 1 个头文件")
        file_name = os.path.basename(file_path)
        logger.info(f"分析头文件: {file_name}")
        
        result = self.analyze_single_file(file_path)
        
        if 'error' in result:
            return {
                'message': f'分析失败: {result["error"]}',
                'results': {},
                'summary': {
                    'total_files': 1,
                    'total_includes': 0,
                    'system_includes': 0,
                    'local_includes': 0,
                    'errors': [result['error']]
                }
            }
        
        # 转换为批量分析格式
        includes = result['includes']
        analysis_result = {
            'message': f'成功分析 1 个头文件，找到 {len(includes)} 个include',
            'results': {file_path: result},
            'summary': {
                'total_files': 1,
                'total_includes': len(includes),
                'system_includes': sum(1 for inc in includes if inc.is_system),
                'local_includes': sum(1 for inc in includes if not inc.is_system),
                'errors': []
            }
        }
        
        summary = analysis_result['summary']
        logger.info(f"头文件分析完成: {summary['total_includes']} 个include")
        
        return analysis_result
    
    def analyze_files(self, file_paths: List[str]) -> Dict:
        """分析多个头文件"""
        results = {}
        summary = {
            'total_files': len(file_paths),
            'total_includes': 0,
            'system_includes': 0,
            'local_includes': 0,
            'errors': []
        }
        
        for file_path in file_paths:
            result = self.analyze_single_file(file_path)
            
            if 'error' in result:
                summary['errors'].append(result['error'])
            else:
                results[file_path] = result
                includes = result['includes']
                summary['total_includes'] += len(includes)
                summary['system_includes'] += sum(1 for inc in includes if inc.is_system)
                summary['local_includes'] += sum(1 for inc in includes if not inc.is_system)
        
        return {
            'results': results,
            'summary': summary
        }
    
    def _collect_header_files_from_repo(self, config_parser, target_files: List[str] = None) -> List[str]:
        """从repo配置收集要分析的头文件"""
        if target_files:
            # 用户指定了特定文件
            header_files = []
            for file_path in target_files:
                abs_path = os.path.abspath(file_path)
                if os.path.isfile(abs_path) and self._is_header_file(abs_path):
                    header_files.append(abs_path)
                else:
                    logger.warning(f"指定的文件不存在或不是头文件: {file_path}")
            return header_files
        
        # 未指定文件：从配置中收集所有头文件
        all_files = []
        analysis_targets = config_parser.get_analysis_targets()
        
        for target_path in analysis_targets:
            if not os.path.exists(target_path):
                logger.warning(f"目标路径不存在: {target_path}")
                continue
            
            if os.path.isfile(target_path):
                if self._is_header_file(target_path):
                    all_files.append(target_path)
            else:
                # 目录：查找所有头文件
                header_files = self.find_all_headers(target_path)
                all_files.extend(header_files)
        
        # 应用排除规则
        return self._apply_exclusions_from_repo(config_parser, all_files)
    
    def _apply_exclusions_from_repo(self, config_parser, files: List[str]) -> List[str]:
        """应用repo配置的排除规则过滤文件"""
        exclude_targets = config_parser.get_exclude_targets()
        if not exclude_targets:
            return files
        
        filtered_files = []
        for file_path in files:
            should_exclude = False
            for exclude_target in exclude_targets:
                if exclude_target in file_path:
                    should_exclude = True
                    break
            
            if not should_exclude:
                filtered_files.append(file_path)
        
        return filtered_files
    
    def find_all_headers(self, directory: str) -> List[str]:
        """查找目录下的所有头文件"""
        header_files = []
        
        if not os.path.isdir(directory):
            return header_files
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_path = os.path.join(root, file)
                if self._is_header_file(file_path):
                    header_files.append(file_path)
        
        return header_files
    
    def _is_header_file(self, file_path: str) -> bool:
        """判断是否是头文件"""
        return is_header_file(file_path)
    
    def _extract_includes(self, content: str, file_path: str) -> List[IncludeInfo]:
        """提取include语句"""
        includes = []
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            
            # 跳过注释行
            if line.startswith('//') or line.startswith('/*'):
                continue
            
            # 检查是否是include指令
            if line.startswith('#include'):
                include_info = self._parse_include_line(line, line_num, file_path)
                if include_info:
                    includes.append(include_info)
        
        return includes
    
    def _parse_include_line(self, line: str, line_num: int, file_path: str) -> Optional[IncludeInfo]:
        """解析include行"""
        # 移除 #include 前缀和多余空白
        content = line[8:].strip()  # len('#include') = 8
        
        if not content:
            return None
        
        # 检查包含类型
        if content.startswith('<') and content.endswith('>'):
            # 系统头文件: #include <header.h>
            include_path = content[1:-1]
            return IncludeInfo(include_path, line_num, file_path, is_system=True)
        elif content.startswith('"') and content.endswith('"'):
            # 本地头文件: #include "header.h"
            include_path = content[1:-1]
            return IncludeInfo(include_path, line_num, file_path, is_system=False)
        else:
            # 其他形式（可能是宏）- 尝试提取
            # 移除可能的注释
            content = content.split('//')[0].split('/*')[0].strip()
            if content:
                return IncludeInfo(content, line_num, file_path, is_system=False)
        
        return None
    
    def _get_single_file_summary_text(self, file_path: str) -> str:
        """获取单文件分析配置摘要文本"""
        return (f"📋 单头文件include分析模式:\n"
                f"   文件路径: {file_path}\n"
                f"   文件名: {os.path.basename(file_path)}\n"
                f"   ➤ 分析单个头文件的include关系")
    
    def _get_repo_summary_text(self, config_parser) -> str:
        """获取repo分析配置摘要文本"""
        return (f"📋 头文件批量include分析模式:\n"
                f"   ➤ 分析指定头文件的include关系")
    
    def _get_empty_summary(self) -> dict:
        """获取空的统计摘要"""
        return {
            'total_files': 0,
            'total_includes': 0,
            'system_includes': 0,
            'local_includes': 0,
            'errors': []
        }
    
    def get_dependency_graph(self, results: Dict) -> Dict[str, List[str]]:
        """获取依赖关系图"""
        if not results or 'results' not in results:
            return {}
            
        graph = {}
        
        for file_path, result in results.get('results', {}).items():
            dependencies = []
            for include in result['includes']:
                dependencies.append(include.include_path)
            graph[file_path] = dependencies
        
        return graph
    
    def search_includes(self, results: Dict, pattern: str) -> List[Dict]:
        """搜索包含特定模式的include"""
        if not results or 'results' not in results:
            return []
            
        matches = []
        
        for file_path, result in results.get('results', {}).items():
            for include in result['includes']:
                if pattern.lower() in include.include_path.lower():
                    matches.append({
                        'file_path': file_path,
                        'file_name': os.path.basename(file_path),
                        'include_path': include.include_path,
                        'line_number': include.line_number,
                        'is_system': include.is_system
                    })
        
        return matches