#!/usr/bin/env python3
"""
传统程序切片工具
用于对C/C++函数进行前向或后向程序切片分析
"""

import argparse
import os
import shutil
import sys

# 添加父目录到路径，以便导入slicer包
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from slicer.models import SliceType
from slicer.slicer_core import CFunctionSlicer
from slicer.output_utils import (
    print_slice_result, save_slice_to_file, save_combined_slice_to_file
)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="C/C++ 传统程序切片工具")
    parser.add_argument("file", help="源代码文件路径")
    parser.add_argument("function", help="函数名")
    parser.add_argument("variable", help="目标变量名")
    parser.add_argument("line", type=int, help="目标行号")
    parser.add_argument("--language", choices=["c", "cpp"], default="c", help="语言类型")
    parser.add_argument("--type", choices=["backward", "forward", "both"], default="both", 
                       help="切片类型：backward(后向)、forward(前向)、both(默认，同时进行两种切片)")
    parser.add_argument("--no-save", action="store_true", 
                       help="不保存切片结果到文件，只显示")
    parser.add_argument("--output-dir", default=".", 
                       help="输出目录（默认为当前目录）")
    
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
        
        if args.type == "both":
            # 同时进行前向和后向切片
            print("1. 后向切片分析（影响目标变量的语句）")
            print("-" * 50)
            backward_lines = slicer.slice_function(args.variable, args.line, SliceType.BACKWARD)
            print_slice_result(code, backward_lines)
            
            print("\n2. 前向切片分析（被目标变量影响的语句）")
            print("-" * 50)
            forward_lines = slicer.slice_function(args.variable, args.line, SliceType.FORWARD)
            print_slice_result(code, forward_lines)
            
            if not args.no_save:
                # 保存单独的切片文件
                backward_file = save_slice_to_file(
                    code, backward_lines, args.file, args.function, 
                    args.variable, args.line, SliceType.BACKWARD
                )
                forward_file = save_slice_to_file(
                    code, forward_lines, args.file, args.function, 
                    args.variable, args.line, SliceType.FORWARD
                )
                
                # 保存综合切片文件
                combined_file = save_combined_slice_to_file(
                    code, backward_lines, forward_lines, args.file, 
                    args.function, args.variable, args.line
                )
                
                # 移动文件到指定目录
                if args.output_dir != ".":
                    backward_dest = os.path.join(args.output_dir, os.path.basename(backward_file))
                    forward_dest = os.path.join(args.output_dir, os.path.basename(forward_file))
                    combined_dest = os.path.join(args.output_dir, os.path.basename(combined_file))
                    
                    shutil.move(backward_file, backward_dest)
                    shutil.move(forward_file, forward_dest)
                    shutil.move(combined_file, combined_dest)
                    
                    backward_file = backward_dest
                    forward_file = forward_dest
                    combined_file = combined_dest
                
                print(f"\n切片结果已保存到:")
                print(f"  后向切片: {backward_file}")
                print(f"  前向切片: {forward_file}")
                print(f"  综合切片: {combined_file}")
        
        else:
            # 单一类型切片
            slice_type = SliceType.BACKWARD if args.type == "backward" else SliceType.FORWARD
            print(f"{args.type.title()} 切片分析:")
            print("-" * 50)
            
            slice_lines = slicer.slice_function(args.variable, args.line, slice_type)
            print_slice_result(code, slice_lines)
            
            if not args.no_save:
                output_file = save_slice_to_file(
                    code, slice_lines, args.file, args.function, 
                    args.variable, args.line, slice_type
                )
                
                # 移动文件到指定目录
                if args.output_dir != ".":
                    dest_file = os.path.join(args.output_dir, os.path.basename(output_file))
                    shutil.move(output_file, dest_file)
                    output_file = dest_file
                
                print(f"\n切片结果已保存到: {output_file}")
    
    except Exception as e:
        print(f"错误：{e}")
        return


if __name__ == "__main__":
    main() 