#!/usr/bin/env python3
"""
文件查找器 - 在目录中查找C/C++相关文件
"""

import os
import glob
import json
import logging
from pathlib import Path
from typing import List, Set

# 配置logging
logger = logging.getLogger(__name__)


class FileFinder:
    """C/C++文件查找器"""
    
    def __init__(self):
        # 从配置文件加载设置
        self._load_config()
        self.ALL_EXTENSIONS = self.C_EXTENSIONS | self.CPP_EXTENSIONS
        self.found_files = []
    
    def _load_config(self):
        """从配置文件加载设置"""
        config_path = Path(__file__).parent / "config.json"
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            raise RuntimeError(f"无法加载配置文件 {config_path}: {e}")
        
        # 加载文件扩展名
        file_ext = config.get("file_extensions", {})
        self.C_EXTENSIONS = set(file_ext.get("c_extensions", []))
        self.CPP_EXTENSIONS = set(file_ext.get("cpp_extensions", []))
        
        # 加载要跳过的目录
        self.SKIP_DIRECTORIES = set(config.get("skip_directories", []))
    
    def find_files(self, path: str, recursive: bool = True) -> List[str]:
        """
        查找指定路径下的C/C++文件
        
        Args:
            path: 文件或目录路径
            recursive: 是否递归查找子目录
            
        Returns:
            找到的文件路径列表
        """
        path_obj = Path(path)
        
        if not path_obj.exists():
            raise FileNotFoundError(f"路径不存在: {path}")
        
        self.found_files = []
        
        if path_obj.is_file():
            # 如果是单个文件，检查是否为C/C++文件
            if self._is_c_cpp_file(path_obj):
                self.found_files.append(str(path_obj.absolute()))
        else:
            # 如果是目录，搜索其中的C/C++文件
            self._search_directory(path_obj, recursive)
        
        return sorted(self.found_files)
    
    def _is_c_cpp_file(self, file_path: Path) -> bool:
        """检查文件是否为C/C++文件"""
        return file_path.suffix.lower() in self.ALL_EXTENSIONS
    
    def _search_directory(self, dir_path: Path, recursive: bool):
        """搜索目录中的C/C++文件"""
        try:
            if recursive:
                # 递归搜索
                for root, dirs, files in os.walk(dir_path):
                    # 跳过一些常见的无关目录
                    dirs[:] = [d for d in dirs if not self._should_skip_directory(d)]
                    
                    for file in files:
                        file_path = Path(root) / file
                        if self._is_c_cpp_file(file_path):
                            self.found_files.append(str(file_path.absolute()))
            else:
                # 只搜索当前目录
                for item in dir_path.iterdir():
                    if item.is_file() and self._is_c_cpp_file(item):
                        self.found_files.append(str(item.absolute()))
        except PermissionError as e:
            logger.warning(f"无法访问目录 {dir_path}: {e}")
    
    def _should_skip_directory(self, dir_name: str) -> bool:
        """判断是否应该跳过某个目录"""
        return dir_name in self.SKIP_DIRECTORIES
    
    def get_file_stats(self) -> dict:
        """获取文件统计信息"""
        if not self.found_files:
            return {}
        
        stats = {
            'total_files': len(self.found_files),
            'c_files': 0,
            'cpp_files': 0,
            'header_files': 0,
        }
        
        for file_path in self.found_files:
            ext = Path(file_path).suffix.lower()
            if ext == '.c':
                stats['c_files'] += 1
            elif ext in {'.cpp', '.cxx', '.cc'}:
                stats['cpp_files'] += 1
            elif ext in {'.h', '.hpp', '.hxx', '.hh'}:
                stats['header_files'] += 1
        
        return stats
    
    def get_file_list_info(self, show_stats: bool = True) -> dict:
        """获取文件列表信息（用于日志或返回）"""
        if not self.found_files:
            return {"message": "未找到任何C/C++文件", "files": [], "stats": {}}
        
        file_info = {
            "message": f"找到 {len(self.found_files)} 个C/C++文件",
            "files": []
        }
        
        for i, file_path in enumerate(self.found_files, 1):
            file_obj = Path(file_path)
            file_info["files"].append({
                "index": i,
                "name": file_obj.name,
                "extension": file_obj.suffix,
                "path": file_path
            })
        
        if show_stats:
            file_info["stats"] = self.get_file_stats()
        
        return file_info 