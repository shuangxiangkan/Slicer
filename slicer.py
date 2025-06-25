#!/usr/bin/env python3
"""
C/C++ 函数程序切片工具 - 主入口

使用方法:
    传统程序切片:
        python slicer.py file function variable line [options]
    参数切片分析:
        python slicer.py file function --param [options]
"""

import sys
import os

if __name__ == "__main__":
    # 检查是否是参数切片分析模式
    if "--param" in sys.argv:
        # 移除--param参数，传递给参数分析器
        args = sys.argv[1:]
        args.remove("--param")
        
        # 运行参数分析器
        from tools.param_analyzer import main
        sys.argv = [sys.argv[0]] + args
        main()
    else:
        # 检查参数格式，确保有足够的参数进行传统切片
        if len(sys.argv) < 5:
            print("使用方法:")
            print("  传统程序切片: python slicer.py <file> <function> <variable> <line> [options]")
            print("  参数切片分析: python slicer.py <file> <function> --param [options]")
            print()
            print("示例:")
            print("  python slicer.py example.c example_function result 7")
            print("  python slicer.py complex_example.c complex_function --param")
            sys.exit(1)
        
        # 运行传统程序切片器
        from tools.program_slicer import main
        main() 