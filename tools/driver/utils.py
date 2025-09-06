#!/usr/bin/env python3
"""
Utility functions for the fuzzing driver
"""

import shutil
import subprocess
import os
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


def check_afl_instrumentation(library_path: str) -> Tuple[bool, str]:
    """
    检查编译好的库文件是否被AFL++成功插桩。
    
    Args:
        library_path: 库文件的路径(.a或.so文件)
        
    Returns:
        Tuple of (is_instrumented, message)
    """
    if not os.path.exists(library_path):
        return False, f"库文件不存在: {library_path}"
    
    try:
        # 使用strings命令检查二进制文件中的字符串
        result = subprocess.run(
            ['strings', library_path], 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        if result.returncode != 0:
            return False, f"无法读取库文件内容: {library_path}"
        
        output = result.stdout.lower()
        
        # 检查AFL++插桩的特征字符串
        afl_signatures = [
            '__afl_',           # AFL++函数前缀
            'afl_area_ptr',     # AFL++共享内存指针
            'afl_prev_loc',     # AFL++前一个位置
            '__sanitizer_cov_trace_pc_guard',  # 覆盖率追踪
            'llvm_gcov_',       # LLVM覆盖率
        ]
        
        found_signatures = []
        for signature in afl_signatures:
            if signature in output:
                found_signatures.append(signature)
        
        if found_signatures:
            return True, f"检测到AFL++插桩特征: {', '.join(found_signatures)}"
        else:
            return False, "未检测到AFL++插桩特征，可能编译时未使用afl-clang-fast"
            
    except subprocess.TimeoutExpired:
        return False, f"检查超时: {library_path}"
    except Exception as e:
        return False, f"检查过程中发生错误: {str(e)}"


if __name__ == "__main__":
    ready, missing = verify_fuzzing_environment()
    if ready:
        print("✓ 模糊测试环境已就绪!")
    else:
        print(f"✗ 缺少必要工具: {', '.join(missing)}")
        print("请安装AFL++并确保其在PATH环境变量中")