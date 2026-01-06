#!/usr/bin/env python3
"""
OGHarn 三步筛选流程演示主程序
按顺序执行三个筛选步骤：编译筛选 -> 执行筛选 -> 覆盖率筛选
"""

import sys
from pathlib import Path
from log import *

from step1_compile_filter import compile_filter
from step2_execution_filter import execution_filter
from step3_coverage_filter import coverage_filter

def run_ogharn_demo(harness_dir, seeds_valid_dir, output_dir="output", log_dir="logs", final_dir="final_best", max_harnesses=3):
    """
    运行完整的OGHarn三步筛选演示
    
    Args:
        harness_dir: harness源文件目录
        seeds_valid_dir: 有效种子文件目录
        output_dir: 编译输出目录
        log_dir: 日志输出目录
        final_dir: 最终最佳harness输出目录
        max_harnesses: 最多选择的harness数量
    
    Returns:
        dict: 包含各步骤结果的字典
    """
    
    log_info("OGHarn 三步筛选流程演示")
    log_info(f"Harness目录: {harness_dir}")
    log_info(f"种子文件目录: {seeds_valid_dir}")
    log_info(f"输出目录: {output_dir}")
    log_info(f"日志目录: {log_dir}")
    log_info(f"最终目录: {final_dir}")
    log_info(f"最大选择数量: {max_harnesses}")
    log_info("")
    
    results = {
        'step1_compile': None,
        'step2_execution': None,
        'step3_coverage': None,
        'final_harnesses': []
    }
    
    try:
        # 第一步：编译筛选
        log_info("第一步: 编译筛选")
        
        # 创建中间目录
        stage1_dir = Path(log_dir) / "stage1_passed"
        
        step1_result = compile_filter(
            harness_dir=harness_dir,
            output_dir=output_dir,
            log_dir=log_dir,
            next_stage_dir=stage1_dir
        )
        
        results['step1_compile'] = step1_result
        
        if not step1_result:
            log_error("第一步编译筛选失败，没有harness通过编译")
            return results
        
        log_success(f"第一步完成，{len(step1_result)}个harness通过编译筛选")
        
        # 第二步：执行筛选
        log_info("第二步: 执行筛选")
        
        # 创建中间目录
        stage2_dir = Path(log_dir) / "stage2_passed"
        
        step2_result = execution_filter(
            log_dir=log_dir,
            seeds_valid_dir=seeds_valid_dir,
            next_stage_dir=stage2_dir
        )
        
        results['step2_execution'] = step2_result
        
        if not step2_result:
            log_error("第二步执行筛选失败，没有harness通过执行测试")
            return results
        
        log_success(f"第二步完成，{len(step2_result)}个harness通过执行筛选")
        
        # 第三步：覆盖率筛选
        log_info("第三步: 覆盖率筛选")
        
        step3_result = coverage_filter(
            log_dir=log_dir,
            seeds_valid_dir=seeds_valid_dir,
            final_dir=final_dir,
            max_harnesses=max_harnesses
        )
        
        results['step3_coverage'] = step3_result
        results['final_harnesses'] = step3_result
        
        if not step3_result:
            log_error("第三步覆盖率筛选失败，没有harness通过质量评估")
            return results
        
        log_success(f"第三步完成，{len(step3_result)}个harness通过覆盖率筛选")
        
        # 总结
        log_info("🎉 OGHarn 三步筛选流程完成")
        log_info(f"📁 原始harness目录: {harness_dir}")
        log_info(f"📊 编译通过: {len(step1_result)}个")
        log_info(f"🚀 执行通过: {len(step2_result)}个")
        log_info(f"🏆 最终选择: {len(step3_result)}个")
        log_info(f"📂 最佳harness保存在: {final_dir}")
        log_info(f"📋 详细日志保存在: {log_dir}")
        
        if step3_result:
            log_info("🏆 最终选择的最佳harness")
            for i, harness in enumerate(step3_result, 1):
                harness_name = harness.get('harness', 'unknown')
                quality_score = harness.get('quality_score', 0)
                coverage_gain = harness.get('coverage_gain', 0)
                log_info(f"  {i}. {harness_name} (质量分数: {quality_score:.2f}, 覆盖率增益: {coverage_gain})")
        
        log_success("✨ 演示完成！")
        
    except Exception as e:
        log_error(f"演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()
    
    return results

def main():
    """主函数入口"""
    # 写死参数，无需命令行输入
    harness_dir = '/home/shuangxiang/workspace/code/Slicer/tools/driver/harness_filter_demo/harness_samples'
    seeds_valid_dir = '/home/shuangxiang/workspace/code/Slicer/tools/driver/harness_filter_demo/seeds'
    output_dir = '/home/shuangxiang/workspace/code/Slicer/tools/driver/harness_filter_demo/output'
    log_dir = '/home/shuangxiang/workspace/code/Slicer/tools/driver/harness_filter_demo/logs'
    final_dir = '/home/shuangxiang/workspace/code/Slicer/tools/driver/harness_filter_demo/final_best'
    max_harnesses = 3
    
    # 检查输入目录是否存在
    harness_path = Path(harness_dir)
    seeds_path = Path(seeds_valid_dir)
    
    if not harness_path.exists():
        log_error(f"harness目录不存在: {harness_path}")
        sys.exit(1)
    
    if not seeds_path.exists():
        log_error(f"种子文件目录不存在: {seeds_path}")
        sys.exit(1)
    
    # 运行演示
    results = run_ogharn_demo(
        harness_dir=harness_dir,
        seeds_valid_dir=seeds_valid_dir,
        output_dir=output_dir,
        log_dir=log_dir,
        final_dir=final_dir,
        max_harnesses=max_harnesses
    )
    
    # 根据结果设置退出码
    if results['final_harnesses']:
        sys.exit(0)  # 成功
    else:
        sys.exit(1)  # 失败

if __name__ == "__main__":
    main()