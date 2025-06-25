#!/usr/bin/env python3
"""
参数切片分析工具
用于分析C/C++函数参数的数据流依赖关系，生成代码片段供大模型分析
"""

import argparse
import os
import shutil
import sys

# 添加父目录到路径，以便导入slicer包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicer.slicer_core import CFunctionSlicer
from slicer.output_utils import (
    print_parameter_slice_result, save_parameter_slice_to_file
)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="C/C++ 参数切片分析工具")
    parser.add_argument("file", help="源代码文件路径")
    parser.add_argument("function", help="函数名")
    parser.add_argument("--language", choices=["c", "cpp"], default="c", help="语言类型")
    parser.add_argument("--no-save", action="store_true", 
                       help="不保存分析结果到文件，只显示")
    parser.add_argument("--output-dir", default=".", 
                       help="输出目录（默认为当前目录）")
    parser.add_argument("--verbose", action="store_true",
                       help="显示详细的分析提示信息")
    
    args = parser.parse_args()
    
    # 读取源代码
    try:
        with open(args.file, 'r', encoding='utf-8') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"错误：文件 '{args.file}' 不存在")
        return
    except Exception as e:
        print(f"错误：无法读取文件 '{args.file}': {e}")
        return
    
    # 创建切片器
    slicer = CFunctionSlicer(args.language)
    
    try:
        # 分析函数
        print(f"正在分析函数 '{args.function}'...")
        slicer.analyze_function(code, args.function)
        print("函数分析完成！\n")
        
        # 创建输出目录
        if args.output_dir != "." and not os.path.exists(args.output_dir):
            os.makedirs(args.output_dir)
        
        # 执行参数切片分析
        print("执行参数切片分析...")
        param_result = slicer.perform_parameter_slice_analysis(code)
        print_parameter_slice_result(param_result)
        
        # 显示详细提示信息
        if args.verbose:
            print("\n" + "=" * 60)
            print("代码片段分析提示：")
            print("=" * 60)
            
            # 显示具体的代码片段和分析提示
            for snippet_name, snippet_code in param_result.slice_code_snippets.items():
                print(f"\n📋 {snippet_name}:")
                print("-" * 40)
                print(snippet_code)
                print("\n🤖 建议问大模型的问题：")
                if "forward" in snippet_name:
                    param_name = snippet_name.split('_')[1]
                    print(f"   '参数{param_name}是否会影响这些代码行的执行？是否存在数据流依赖？'")
                elif "return" in snippet_name:
                    print("   '这些代码行是否会影响函数的返回值？存在什么样的数据流关系？'")
                elif "affects" in snippet_name:
                    params = snippet_name.split('_')[1::2]  # 提取参数名
                    if len(params) >= 2:
                        print(f"   '参数{params[0]}是否会影响参数{params[1]}的值？是否存在数据流依赖？'")
                print()
        
        # 保存分析结果
        if not args.no_save:
            param_file = save_parameter_slice_to_file(
                param_result, args.file, args.function
            )
            
            # 移动文件到指定目录
            if args.output_dir != ".":
                dest_file = os.path.join(args.output_dir, os.path.basename(param_file))
                shutil.move(param_file, dest_file)
                param_file = dest_file
            
            print(f"\n参数切片分析报告已保存到: {param_file}")
    
    except Exception as e:
        print(f"错误：{e}")
        return


if __name__ == "__main__":
    main() 