#!/usr/bin/env python3
"""
Utility functions for the fuzzing driver
"""

import shutil
from typing import List, Tuple


def verify_fuzzing_environment() -> Tuple[bool, List[str]]:
    """
    Verify if all required fuzzing tools are available in the environment.
    
    Returns:
        Tuple of (all_tools_available, missing_tools_list)
    """
    # required fuzzing tools
    required_tools = [
        'afl-clang-fast',  
        'afl-clang-fast++',  
        'afl-showmap',       
        'afl-fuzz'           
    ]
    
    missing_tools = []
    
    for tool in required_tools:
        if not shutil.which(tool):
            missing_tools.append(tool)
    
    return len(missing_tools) == 0, missing_tools


if __name__ == "__main__":
    ready, missing = verify_fuzzing_environment()
    if ready:
        print("✓ 模糊测试环境已就绪!")
    else:
        print(f"✗ 缺少必要工具: {', '.join(missing)}")
        print("请安装AFL++并确保其在PATH环境变量中")