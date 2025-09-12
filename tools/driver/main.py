#!/usr/bin/env python3
"""
Library compilation utility
"""

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
    创建并初始化RepoAnalyzer实例
    
    Args:
        config_parser: 配置解析器实例
        
    Returns:
        已完成基础分析的RepoAnalyzer实例
    """
    log_info(f"使用直接参数模式进行分析: {config_parser.get_target_library_dir()}")
    
    # 初始化分析器（直接参数模式）
    analyzer = RepoAnalyzer(
        library_path=config_parser.get_target_library_dir(),
        header_files=config_parser.get_headers(),
        include_files=config_parser.get_source_dirs(),
        exclude_files=config_parser.get_exclude_dirs()
    )
    
    # 执行基础分析
    result = analyzer.analyze()
    log_info(f"基础分析完成，总共找到 {result['total_functions']} 个函数")
    
    return analyzer

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
        # 解析配置
        config_parser = ConfigParser(config_path)
        log_success("Configuration parsed successfully.")
        
        # 通过config_parser获取目录路径
        library_output_dir = config_parser.get_output_dir()
        
        # 创建LibraryHandler实例
        handler = LibraryHandler(config_parser)
        
        # 步骤1: 编译库文件
        success = handler.compile_library(library_type)
        if not success:
            log_error("库文件编译失败，终止harness生成")
            return False
        
        # 步骤2: 创建RepoAnalyzer实例（在编译完成后）
        analyzer = create_repo_analyzer(config_parser)
        
        # 步骤3: 提取API并保存到文件
        api_functions = handler.get_all_apis(library_output_dir, analyzer)
        
        # 步骤3: 检查API函数提取结果
        if not api_functions:
            log_error("未找到API函数，终止harness生成")
            return False
        
        # 步骤4: 计算API相似性并保存结果
        similarity_results = handler.compute_api_similarity(api_functions, library_output_dir)
        
        # 步骤5: 提取API注释并保存结果
        comments_results = handler.get_api_comments(api_functions, analyzer, library_output_dir)
        
        # 步骤6: 搜索API文档说明并保存结果
        documentation_results = handler.get_api_documentation(api_functions, analyzer, library_output_dir)
        
        # 步骤5: 计算API usage统计并保存结果
        usage_results, api_categories = handler.get_api_usage(api_functions, analyzer, library_output_dir)
        
        # 步骤8: 生成API harness
        from harness_generator import HarnessGenerator
        harness_generator = HarnessGenerator(config_parser)
        harness_success = harness_generator.generate_harnesses_for_all_apis(
             api_functions,
             api_categories,
             usage_results,
             similarity_results,
             comments_results,
             documentation_results,
             library_output_dir
         )
        
        if not harness_success:
            log_warning("Harness生成过程中出现问题，但分析结果已保存")
        
        log_success("Harness generation completed successfully.")
            
        return True
        
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