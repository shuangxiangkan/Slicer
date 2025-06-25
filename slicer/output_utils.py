#!/usr/bin/env python3
"""
输出和文件保存工具
"""

import os
from datetime import datetime
from typing import List

from .models import SliceType, ParameterSliceResult


def print_slice_result(code: str, slice_lines: List[int]):
    """
    打印切片结果
    
    Args:
        code: 源代码
        slice_lines: 切片包含的行号列表
    """
    lines = code.split('\n')
    
    print(f"切片包含 {len(slice_lines)} 行代码:")
    print("-" * 40)
    
    for line_num in slice_lines:
        if 1 <= line_num <= len(lines):
            print(f"行{line_num:3d}: {lines[line_num-1]}")
    print()


def save_slice_to_file(code: str, slice_lines: List[int], 
                      original_filename: str, function_name: str,
                      variable_name: str, target_line: int, 
                      slice_type: SliceType) -> str:
    """
    将切片结果保存到文件
    
    Args:
        code: 原始代码
        slice_lines: 切片包含的行号列表
        original_filename: 原始文件名
        function_name: 函数名
        variable_name: 目标变量名
        target_line: 目标行号
        slice_type: 切片类型
        
    Returns:
        保存的文件名
    """
    lines = code.split('\n')
    
    # 生成输出文件名
    base_name = original_filename.rsplit('.', 1)[0]  # 去掉扩展名
    extension = original_filename.rsplit('.', 1)[1] if '.' in original_filename else 'c'
    
    slice_type_str = "backward" if slice_type == SliceType.BACKWARD else "forward"
    output_filename = f"{base_name}_{function_name}_{variable_name}_line{target_line}_{slice_type_str}_slice.{extension}"
    
    # 收集切片代码
    slice_code_lines = []
    slice_code_lines.append(f"// 程序切片结果 - {slice_type_str.upper()}")
    slice_code_lines.append(f"// 原始文件: {original_filename}")
    slice_code_lines.append(f"// 函数: {function_name}")
    slice_code_lines.append(f"// 目标变量: {variable_name} (第{target_line}行)")
    slice_code_lines.append(f"// 切片类型: {slice_type_str}")
    slice_code_lines.append(f"// 切片包含 {len(slice_lines)} 行代码")
    slice_code_lines.append("")
    
    # 添加切片的代码行
    for i, line in enumerate(lines, 1):
        if i in slice_lines:
            slice_code_lines.append(f"/* 行{i:3d} */ {line}")
    
    # 保存到文件
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(slice_code_lines))
    
    return output_filename


def save_combined_slice_to_file(code: str, backward_lines: List[int], 
                               forward_lines: List[int], original_filename: str, 
                               function_name: str, variable_name: str, 
                               target_line: int) -> str:
    """
    将前向和后向切片结果保存到一个文件中
    
    Args:
        code: 原始代码
        backward_lines: 后向切片行号列表
        forward_lines: 前向切片行号列表
        original_filename: 原始文件名
        function_name: 函数名
        variable_name: 目标变量名
        target_line: 目标行号
        
    Returns:
        保存的文件名
    """
    lines = code.split('\n')
    
    # 生成输出文件名
    base_name = original_filename.rsplit('.', 1)[0]  # 去掉扩展名
    extension = original_filename.rsplit('.', 1)[1] if '.' in original_filename else 'c'
    
    output_filename = f"{base_name}_{function_name}_{variable_name}_line{target_line}_combined_slice.{extension}"
    
    # 收集切片代码
    slice_code_lines = []
    slice_code_lines.append(f"// 综合程序切片结果")
    slice_code_lines.append(f"// 原始文件: {original_filename}")
    slice_code_lines.append(f"// 函数: {function_name}")
    slice_code_lines.append(f"// 目标变量: {variable_name} (第{target_line}行)")
    slice_code_lines.append(f"// 后向切片包含 {len(backward_lines)} 行代码")
    slice_code_lines.append(f"// 前向切片包含 {len(forward_lines)} 行代码")
    
    # 合并切片行号
    all_slice_lines = set(backward_lines + forward_lines)
    slice_code_lines.append(f"// 综合切片包含 {len(all_slice_lines)} 行代码")
    slice_code_lines.append("")
    
    # 添加图例
    slice_code_lines.append("// 图例:")
    slice_code_lines.append("// [B] = 仅后向切片")
    slice_code_lines.append("// [F] = 仅前向切片") 
    slice_code_lines.append("// [BF] = 前向和后向切片都包含")
    slice_code_lines.append("")
    
    # 添加切片的代码行
    for i, line in enumerate(lines, 1):
        if i in all_slice_lines:
            # 确定标记
            in_backward = i in backward_lines
            in_forward = i in forward_lines
            
            if in_backward and in_forward:
                marker = "[BF]"
            elif in_backward:
                marker = "[B] "
            else:
                marker = "[F] "
            
            slice_code_lines.append(f"/* 行{i:3d} {marker} */ {line}")
    
    # 保存到文件
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(slice_code_lines))
    
    return output_filename


def print_parameter_slice_result(result: ParameterSliceResult):
    """
    打印参数切片分析结果
    
    Args:
        result: 参数切片分析结果
    """
    print("参数切片分析结果")
    print("=" * 60)
    
    print(f"函数参数: {', '.join(result.function_parameters)}")
    print()
    
    print("参数前向切片分析（每个参数影响的代码行）:")
    print("-" * 50)
    for param, slice_lines in result.parameter_slices.items():
        if slice_lines:
            lines_str = ', '.join(map(str, slice_lines))
            print(f"  参数 '{param}' -> 影响行: {lines_str}")
        else:
            print(f"  参数 '{param}' -> 没有影响其他代码")
    print()
    
    print("返回值后向切片分析（影响返回值的代码行）:")
    print("-" * 50)
    if result.return_slice:
        lines_str = ', '.join(map(str, result.return_slice))
        print(f"  返回值 <- 受影响于行: {lines_str}")
    else:
        print("  返回值不受任何代码影响")
    print()
    
    print("参数间交互分析（参数A影响参数B）:")
    print("-" * 50)
    if result.parameter_interactions:
        for param1, interactions in result.parameter_interactions.items():
            for param2, lines in interactions.items():
                lines_str = ', '.join(map(str, lines))
                print(f"  参数 '{param1}' -> 影响参数 '{param2}' (行: {lines_str})")
    else:
        print("  没有发现参数间的直接影响")
    print()
    
    print("代码片段（供大模型分析）:")
    print("-" * 50)
    for snippet_name, snippet_code in result.slice_code_snippets.items():
        print(f"\n{snippet_name}:")
        print(snippet_code)
        print()
        
    print("\n" + "=" * 60)
    print("提示：将上述代码片段提供给大模型，询问是否存在数据流依赖关系")
    print("=" * 60)


def save_parameter_slice_to_file(result: ParameterSliceResult, 
                                original_filename: str, function_name: str) -> str:
    """
    保存参数切片分析结果到文件
    
    Args:
        result: 参数切片分析结果
        original_filename: 原始文件名
        function_name: 函数名
        
    Returns:
        保存的文件名
    """
    base_name = original_filename.rsplit('.', 1)[0]
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_filename = f"{base_name}_{function_name}_param_slice_{timestamp}.txt"
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write("参数切片分析报告\n")
        f.write("=" * 60 + "\n")
        f.write(f"文件: {original_filename}\n")
        f.write(f"函数: {function_name}\n")
        f.write(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write(f"函数参数: {', '.join(result.function_parameters)}\n\n")
        
        f.write("参数前向切片分析（每个参数影响的代码行）:\n")
        f.write("-" * 50 + "\n")
        for param, slice_lines in result.parameter_slices.items():
            if slice_lines:
                lines_str = ', '.join(map(str, slice_lines))
                f.write(f"  参数 '{param}' -> 影响行: {lines_str}\n")
            else:
                f.write(f"  参数 '{param}' -> 没有影响其他代码\n")
        f.write("\n")
        
        f.write("返回值后向切片分析（影响返回值的代码行）:\n")
        f.write("-" * 50 + "\n")
        if result.return_slice:
            lines_str = ', '.join(map(str, result.return_slice))
            f.write(f"  返回值 <- 受影响于行: {lines_str}\n")
        else:
            f.write("  返回值不受任何代码影响\n")
        f.write("\n")
        
        f.write("参数间交互分析（参数A影响参数B）:\n")
        f.write("-" * 50 + "\n")
        if result.parameter_interactions:
            for param1, interactions in result.parameter_interactions.items():
                for param2, lines in interactions.items():
                    lines_str = ', '.join(map(str, lines))
                    f.write(f"  参数 '{param1}' -> 影响参数 '{param2}' (行: {lines_str})\n")
        else:
            f.write("  没有发现参数间的直接影响\n")
        f.write("\n")
        
        f.write("代码片段（供大模型分析）:\n")
        f.write("-" * 50 + "\n")
        for snippet_name, snippet_code in result.slice_code_snippets.items():
            f.write(f"\n{snippet_name}:\n")
            f.write(snippet_code + '\n')
            f.write("-" * 30 + "\n")
        
        f.write("\n" + "=" * 60 + "\n")
        f.write("提示：将上述代码片段提供给大模型，询问是否存在数据流依赖关系\n")
        f.write("=" * 60 + "\n")
    
    return output_filename 