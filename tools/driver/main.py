#!/usr/bin/env python3
"""
Library compilation utility
"""

import sys
from library_handler import LibraryHandler
from config_parser import ConfigParser
from logging import logger

def compile_library_with_config(config_parser: ConfigParser, library_type: str = "static") -> bool:
    """
    编译库文件的通用函数
    
    Args:
        config_parser: 配置解析器对象
        library_type: 库类型 ("static", "shared")
    
    Returns:
        True if compilation is successful, False otherwise.
    """
    logger.info(f"Compilation type: {library_type}")
    
    if library_type not in ["static", "shared"]:
        logger.error(f"Invalid library type: {library_type}. Must be 'static' or 'shared'.")
        return False
    
    try:
        handler = LibraryHandler(config_parser)
        
        if library_type == "static":
            logger.info("Starting static library compilation...")
            success = handler.compile_library("static")
            if success:
                logger.info("Static library compiled successfully.")
            else:
                logger.error("Failed to compile static library.")
        
        elif library_type == "shared":
            logger.info("Starting shared library compilation...")
            success = handler.compile_library("shared")
            if success:
                logger.info("Shared library compiled successfully.")
            else:
                logger.error("Failed to compile shared library.")
        
        if success:
            logger.info("Library compilation completed successfully.")
        else:
            logger.error("Library compilation failed.")
            
        return success
        
    except Exception as e:
        logger.error(f"Error during library compilation: {e}")
        return False

def harness_generation(config_path: str, library_type: str = "static") -> bool:
    """
    Harness生成的主函数，负责配置解析和库编译
    
    Args:
        config_path: 配置文件路径
        library_type: 库类型 ("static", "shared")
    
    Returns:
        True if successful, False otherwise.
    """
    logger.info(f"Starting harness generation with config: {config_path}")
    
    try:
        # 全局配置解析
        config_parser = ConfigParser(config_path)
        logger.info("Configuration parsed successfully.")
        
        # 调用库编译函数
        success = compile_library_with_config(config_parser, library_type)
        
        if success:
            logger.success("Harness generation completed successfully.")
        else:
            logger.error("Harness generation failed.")
            
        return success
        
    except Exception as e:
        logger.error(f"Error during harness generation: {e}")
        return False

if __name__ == "__main__":
    # 手动修改这些参数
    config_path = "configs/cJSON.yaml"
    library_type = "static"  # "static", "shared"
    
    success = harness_generation(config_path, library_type)
    if not success:
        sys.exit(1)