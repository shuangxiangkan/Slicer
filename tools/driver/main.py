#!/usr/bin/env python3
"""
Library compilation utility
"""

import os
import sys
from pathlib import Path
from library_handler import LibraryHandler
from config_parser import ConfigParser
from log import *

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from parser.repo_analyzer import RepoAnalyzer

def create_repo_analyzer(config_parser: ConfigParser) -> RepoAnalyzer:
    """
    创建并配置RepoAnalyzer实例，并执行基础分析
    
    Args:
        config_parser: 配置解析器对象
        
    Returns:
        已完成基础分析的RepoAnalyzer实例
    """
    library_name = config_parser.get_library_info()['name']
    source_dirs = config_parser.get_source_dirs()
    
    config_dict = {
        "library_path": f"benchmarks/{library_name}",  # 相对于项目根目录的路径
        "header_files": config_parser.get_headers(),
        "include_files": source_dirs,  # 使用处理后的source_dirs作为include_files
        "exclude_files": config_parser.get_exclude_dirs(),
        "api_selection": config_parser.get_api_selection()
    }
    
    log_info(f"使用配置字典进行分析: {config_dict['library_path']}")
    
    # 初始化分析器（字典配置模式）
    analyzer = RepoAnalyzer(config_dict=config_dict)
    
    # 执行基础分析
    result = analyzer.analyze()
    log_info(f"基础分析完成，总共找到 {result['total_functions']} 个函数")
    
    return analyzer

def compile_library_static_or_dynamic(handler: LibraryHandler, library_type: str = "static") -> bool:
    """
    编译库文件的通用函数
    
    Args:
        handler: LibraryHandler实例
        library_type: 库类型 ("static", "shared")
    
    Returns:
        True if compilation is successful, False otherwise.
    """
    log_info(f"Compilation type: {library_type}")
    
    if library_type not in ["static", "shared"]:
        log_error(f"Invalid library type: {library_type}. Must be 'static' or 'shared'.")
        return False
    
    try:
        if library_type == "static":
            success = handler.compile_library("static")
        elif library_type == "shared":
            success = handler.compile_library("shared")
        
        return success
        
    except Exception as e:
        log_error(f"Error during library compilation: {e}")
        return False

def harness_generation(config_path: str, library_type: str = "static") -> bool:
    """
    生成harness的主函数
    
    Args:
        config_path: 配置文件路径
        library_type: 库类型 ("static", "shared")
        
    Returns:
        True if harness generation is successful, False otherwise.
    """
    try:
        # 获取当前脚本所在目录
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 解析配置获取库名
        config_parser = ConfigParser(config_path)
        library_name = config_parser.get_library_info()['name']
        log_success("Configuration parsed successfully.")
        
        # 创建Libraries目录（不创建库子目录，让构建命令通过git clone创建）
        libraries_base_dir = os.path.join(base_dir, "Libraries")
        os.makedirs(libraries_base_dir, exist_ok=True)
        library_dir = libraries_base_dir  # 构建命令将在此目录下执行
        
        # 创建Output目录和库子目录
        output_dir = os.path.join(base_dir, "Output")
        library_output_dir = os.path.join(output_dir, library_name)
        os.makedirs(library_output_dir, exist_ok=True)
        
        # 创建LibraryHandler和RepoAnalyzer实例
        handler = LibraryHandler(config_parser, library_dir)
        analyzer = create_repo_analyzer(config_parser)
        
        # 步骤1: 编译库文件
        success = compile_library_static_or_dynamic(handler, library_type)
        
        # 步骤2: 提取API并保存到文件
        api_functions = handler.get_all_apis(library_output_dir, analyzer)
        
        # 步骤3: 计算API相似性并保存结果
        similarity_results = {}
        if api_functions:
            similarity_results = handler.compute_api_similarity(api_functions, library_output_dir)
        
        # 步骤4: 计算API usage统计并保存结果
        usage_results = {}
        if api_functions:
            usage_results = handler.get_api_usage(api_functions, analyzer, library_output_dir)
        
        
        log_success("Harness generation completed successfully.")
            
        return 1
        
    except Exception as e:
        log_error(f"Error during harness generation: {e}")
        return False

if __name__ == "__main__":
    # 手动修改这些参数
    config_path = "/home/kansx/SVF-Tools/Slicer/tools/driver/configs/cJSON.yaml"
    library_type = "static"  # "static", "shared"
    
    success = harness_generation(config_path, library_type)
    if not success:
        sys.exit(1)