#!/usr/bin/env python3
"""
配置文件解析器 - 解析用户分析配置
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any
from .file_finder import FileFinder


class ConfigParser:
    """用户配置文件解析器"""
    
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # 验证必要的配置项
            if 'library_path' not in config:
                raise ValueError("配置文件缺少 'library_path' 配置项")
            
            # 设置默认值
            config.setdefault('include_files', [])
            config.setdefault('exclude_files', [])
            
            # 验证互斥性
            if config['include_files'] and config['exclude_files']:
                raise ValueError("include_files 和 exclude_files 不能同时指定，请选择其中一种模式")
            
            return config
            
        except FileNotFoundError:
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def get_library_path(self) -> str:
        """获取库路径"""
        library_path = self.config['library_path']
        
        # 如果是相对路径，转换为绝对路径
        if not os.path.isabs(library_path):
            # 获取项目根目录（configs目录的上上级目录）
            config_dir = os.path.dirname(os.path.abspath(self.config_path))
            benchmarks_dir = os.path.dirname(config_dir)  # benchmarks目录
            project_root = os.path.dirname(benchmarks_dir)  # 项目根目录
            library_path = os.path.join(project_root, library_path)
            library_path = os.path.abspath(library_path)
        
        return library_path
    
    def is_include_mode(self) -> bool:
        """判断是否为包含模式"""
        return bool(self.config['include_files'])
    
    def is_exclude_mode(self) -> bool:
        """判断是否为排除模式"""
        return bool(self.config['exclude_files'])
    
    def is_analyze_all_mode(self) -> bool:
        """判断是否为分析全部模式（既没有include也没有exclude）"""
        return not self.config['include_files'] and not self.config['exclude_files']
    
    def get_target_files(self) -> List[str]:
        """获取目标文件列表（绝对路径）"""
        library_path = self.get_library_path()
        
        if self.is_include_mode():
            # 包含模式：返回要分析的文件
            target_files = []
            for file_name in self.config['include_files']:
                file_path = os.path.join(library_path, file_name)
                target_files.append(file_path)
            return target_files
        elif self.is_exclude_mode():
            # 排除模式：返回要排除的文件
            exclude_files = []
            for file_name in self.config['exclude_files']:
                file_path = os.path.join(library_path, file_name)
                exclude_files.append(file_path)
            return exclude_files
        else:
            # 分析全部模式：返回空列表
            return []
    
    def get_analysis_targets(self) -> List[str]:
        """
        获取分析目标列表
        
        Returns:
            包含模式：返回要分析的文件列表
            排除模式：返回整个库的文件 - 被排除的文件
            分析全部模式：返回整个库的所有文件
        """
        if self.is_include_mode():
            # 包含模式：只分析指定的文件
            return self.get_target_files()
        elif self.is_exclude_mode():
            # 排除模式：整个库的文件 - 被排除的文件
            finder = FileFinder()
            all_files = finder.find_files(self.get_library_path(), recursive=True)
            exclude_files = set(self.get_target_files())  # get_target_files在排除模式下返回要排除的文件
            return [f for f in all_files if f not in exclude_files]
        else:
            # 分析全部模式：分析整个库的所有文件
            finder = FileFinder()
            return finder.find_files(self.get_library_path(), recursive=True)
    
    def get_exclude_targets(self) -> List[str]:
        """
        获取排除目标列表
        
        Returns:
            排除模式：返回要排除的文件列表
            包含模式或分析全部模式：返回空列表
        """
        if self.is_exclude_mode():
            return self.get_target_files()
        else:
            return []
    
    def get_config_summary_text(self) -> str:
        """获取配置文件摘要文本"""
        summary = "📋 配置文件摘要:\n"
        summary += f"   库路径: {self.get_library_path()}\n"
        
        if self.is_include_mode():
            summary += f"   包含文件: {self.config['include_files']}\n"
            summary += "   ➤ 只分析指定的文件"
        elif self.is_exclude_mode():
            summary += f"   排除文件: {self.config['exclude_files']}\n"
            summary += "   ➤ 分析整个库，排除指定的文件"
        else:
            summary += "   ➤ 分析整个库（未指定包含或排除文件）"
        
        return summary