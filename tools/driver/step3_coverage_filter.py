#!/usr/bin/env python3
"""
三步筛选流程演示 - 第三步：代码覆盖率筛选: 通过代码覆盖率分析选择最佳 harness
"""

import os
import subprocess
import json
import shutil
import tempfile
import time
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime
from log import *
from step1_compile_filter import create_compile_utils

class CoverageFilter:
    def __init__(self, log_dir, seeds_valid_dir, dict_file=None, config_parser=None):
        self.log_dir = Path(log_dir)  # 用于保存step3结果
        self.step2_log_dir = Path(log_dir)  # 用于读取step2结果，初始与log_dir相同
        self.seeds_valid_dir = Path(seeds_valid_dir)
        self.dict_file = Path(dict_file) if dict_file else None
        self.config_parser = config_parser
        self.global_bitmap = set()  # 模拟 OGHarn 的 globalBitmap
        self.coverage_stats = {
            'total_harnesses': 0,
            'coverage_success': 0,
            'coverage_failed': 0,
            'best_harnesses': [],
            'coverage_analysis': []
        }
        
        # 创建编译工具
        self.compile_utils = create_compile_utils(config_parser)
        
        # 创建crash调试信息目录
        self.crash_debug_dir = self.log_dir / "crash_failures"
        self.crash_debug_dir.mkdir(parents=True, exist_ok=True)
    
    def save_crash_debug_info(self, harness_name: str, binary_path: Path, crash_dir: Path, 
                             afl_cmd: List[str], fuzz_duration: int, crash_count: int):
        """保存fuzz过程中发现的crash调试信息"""
        try:
            # 为每个发现crash的harness创建单独的目录
            crash_debug_dir = self.crash_debug_dir / f"{harness_name}_crash_{crash_count}crashes"
            crash_debug_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制二进制文件
            if binary_path.exists():
                dest_binary = crash_debug_dir / binary_path.name
                shutil.copy2(binary_path, dest_binary)
                log_info(f"已保存crash的二进制文件: {dest_binary}")
            
            # 复制所有crash文件
            crashes_dir = crash_dir / "default" / "crashes"
            if crashes_dir.exists():
                dest_crashes_dir = crash_debug_dir / "crashes"
                shutil.copytree(crashes_dir, dest_crashes_dir, dirs_exist_ok=True)
                crash_files = list(dest_crashes_dir.glob("*"))
                log_info(f"已保存 {len(crash_files)} 个crash文件到: {dest_crashes_dir}")
            
            # 复制queue文件（测试用例）
            queue_dir = crash_dir / "default" / "queue"
            if queue_dir.exists():
                dest_queue_dir = crash_debug_dir / "queue"
                shutil.copytree(queue_dir, dest_queue_dir, dirs_exist_ok=True)
                queue_files = list(dest_queue_dir.glob("*"))
                log_info(f"已保存 {len(queue_files)} 个测试用例到: {dest_queue_dir}")
            
            # 复制AFL++统计文件
            stats_file = crash_dir / "default" / "fuzzer_stats"
            if stats_file.exists():
                dest_stats = crash_debug_dir / "fuzzer_stats"
                shutil.copy2(stats_file, dest_stats)
                log_info(f"已保存AFL++统计文件: {dest_stats}")
            
            # 复制plot数据文件
            plot_data = crash_dir / "default" / "plot_data"
            if plot_data.exists():
                dest_plot = crash_debug_dir / "plot_data"
                shutil.copy2(plot_data, dest_plot)
                log_info(f"已保存AFL++图表数据: {dest_plot}")
            
            # 保存crash调试信息
            debug_info = {
                'harness_name': harness_name,
                'binary_path': str(binary_path),
                'afl_command': afl_cmd,
                'fuzz_duration_seconds': fuzz_duration,
                'unique_crashes_found': crash_count,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'crash_files_location': str(dest_crashes_dir) if crashes_dir.exists() else "No crashes directory found",
                'queue_files_location': str(dest_queue_dir) if queue_dir.exists() else "No queue directory found",
                'reproduction_notes': [
                    f"1. 使用二进制文件: {binary_path.name}",
                    f"2. 运行任意crash文件: ./{binary_path.name} < crashes/id:000000,sig:*",
                    f"3. 或使用afl-tmin最小化crash: afl-tmin -i crashes/id:000000,sig:* -o minimized_crash -- ./{binary_path.name}",
                    f"4. 使用gdb调试: gdb ./{binary_path.name}, 然后 run < crashes/id:000000,sig:*"
                ]
            }
            
            debug_file = crash_debug_dir / "crash_debug_info.json"
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            
            # 创建crash重现脚本
            reproduce_script = crash_debug_dir / "reproduce_crashes.sh"
            with open(reproduce_script, 'w', encoding='utf-8') as f:
                f.write("#!/bin/bash\n")
                f.write("# AFL++ Crash重现脚本\n")
                f.write(f"# Harness: {harness_name}\n")
                f.write(f"# 发现时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# 发现的crash数量: {crash_count}\n\n")
                
                f.write("echo \"=== AFL++ Crash重现脚本 ===\"\n")
                f.write(f"echo \"Harness: {harness_name}\"\n")
                f.write(f"echo \"发现的crash数量: {crash_count}\"\n")
                f.write("echo \"\"\n\n")
                
                if crashes_dir.exists():
                    f.write("echo \"可用的crash文件:\"\n")
                    f.write("ls -la crashes/\n")
                    f.write("echo \"\"\n\n")
                    
                    f.write("echo \"重现第一个crash:\"\n")
                    f.write(f"FIRST_CRASH=$(ls crashes/ | head -1)\n")
                    f.write("if [ ! -z \"$FIRST_CRASH\" ]; then\n")
                    f.write(f"    echo \"使用crash文件: $FIRST_CRASH\"\n")
                    f.write(f"    ./{binary_path.name} < crashes/$FIRST_CRASH\n")
                    f.write("    echo \"返回码: $?\"\n")
                    f.write("else\n")
                    f.write("    echo \"没有找到crash文件\"\n")
                    f.write("fi\n\n")
                    
                    f.write("echo \"使用gdb调试第一个crash:\"\n")
                    f.write("echo \"运行命令: gdb ./{}\"\n".format(binary_path.name))
                    f.write("echo \"在gdb中运行: run < crashes/$FIRST_CRASH\"\n")
                else:
                    f.write("echo \"警告: 没有找到crash文件目录\"\n")
            
            # 设置脚本可执行权限
            reproduce_script.chmod(0o755)
            
            log_success(f"Crash调试信息已保存到: {crash_debug_dir}")
            log_info(f"Crash重现脚本: {reproduce_script}")
            
        except Exception as e:
            log_error(f"保存crash调试信息失败: {str(e)}")
    
    def load_execution_successful_harnesses_from_folder(self, execution_filtered_dir) -> List[Dict]:
        """从执行过滤后的文件夹加载harness列表"""
        execution_dir = Path(execution_filtered_dir)
        if not execution_dir.exists():
            log_error(f"执行过滤后的文件夹不存在: {execution_dir}")
            return []
        
        # 获取所有C/C++文件
        harness_files = list(execution_dir.glob("*.c")) + list(execution_dir.glob("*.cpp"))
        
        if not harness_files:
            log_warning(f"在 {execution_dir} 中未找到任何C/C++文件")
            return []
        
        log_info(f"从 {execution_dir} 加载了 {len(harness_files)} 个harness文件")
        
        # 转换为字典格式
        harness_list = []
        for harness_file in harness_files:
            harness_list.append({
                'source': str(harness_file)
            })
        
        return harness_list
    
    def get_seed_files(self, seed_dir: Path) -> List[Path]:
        """获取种子文件列表"""
        if not seed_dir.exists():
            return []
        
        # 获取目录中的所有文件作为种子文件
        seed_files = [f for f in seed_dir.iterdir() if f.is_file()]
        
        return seed_files
    
    def _compile_harness_in_tmp(self, source_file):
        """在临时目录编译harness"""
        return self.compile_utils.compile_harness_in_temp(source_file, "coverage")
      
    def fuzz_harness_with_timeout(self, binary_path: Path, fuzz_duration=10) -> Dict:
        """对harness进行限时模糊测试，评估其真实的模糊测试质量"""
        log_info(f"    开始对 {binary_path.name} 进行 {fuzz_duration} 秒模糊测试...")
        
        fuzz_result = {
            'total_executions': 0,
            'unique_crashes': 0,
            'coverage_bitmap': set(),
            'coverage_growth': [],
            'execution_speed': 0,
            'stability': 0.0
        }
        
        try:
            # 获取所有种子文件
            seed_files = self.get_seed_files(self.seeds_valid_dir)
            if not seed_files:
                log_warning(f"      警告: 没有找到种子文件，种子目录: {self.seeds_valid_dir}")
                return fuzz_result
            
            # 使用所有种子文件进行模糊测试
            log_info(f"      使用 {len(seed_files)} 个种子文件进行模糊测试")
            
            # 模糊测试
            return self.run_afl_fuzz(binary_path, seed_files, fuzz_duration)
                
        except Exception as e:
            log_error(f"      模糊测试失败: {str(e)}")
            return fuzz_result
    
    def run_afl_fuzz(self, binary_path: Path, seed_files: List[Path], duration: int) -> Dict:
        """使用AFL++和所有种子文件进行真实的模糊测试"""
        
        fuzz_result = {
            'total_executions': 0,
            'unique_crashes': 0,
            'coverage_bitmap': set(),
            'coverage_growth': [],
            'execution_speed': 0,
            'stability': 0.0
        }
        
        try:
            # 创建临时目录用于AFL++
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                input_dir = temp_path / "input"
                output_dir = temp_path / "output"
                input_dir.mkdir()
                output_dir.mkdir()
                
                # 复制所有种子文件到输入目录
                for i, seed_file in enumerate(seed_files):
                    seed_copy = input_dir / f"seed_{i}_{seed_file.name}"
                    shutil.copy2(seed_file, seed_copy)
                
                # 运行AFL++模糊测试
                cmd = [
                    'afl-fuzz',
                    '-i', str(input_dir),
                    '-o', str(output_dir),
                    '-t', '1000',  # 单个输入测试用例1秒超时
                ]
                
                # 如果有dict文件，添加到命令中
                if self.dict_file and self.dict_file.exists():
                    cmd.extend(['-x', str(self.dict_file)])
                    log_info(f"        使用字典文件: {self.dict_file}")
                
                cmd.extend(['--', str(binary_path), '@@'])
                
                log_info(f"      启动AFL++模糊测试: {' '.join(cmd)}")
                
                # 设置AFL++环境变量
                env = os.environ.copy()
                env['AFL_SKIP_CPUFREQ'] = '1'
                env['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
                env['AFL_NO_UI'] = '1'  # 禁用UI界面
                env['AFL_QUIET'] = '1'  # 静默模式
                env['AFL_FORKSRV_INIT_TMOUT'] = '10000'  # 增加fork server初始化超时
                env['AFL_HANG_TMOUT'] = '1000'  # 设置挂起超时
                
                # 启动AFL++进程
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    env=env
                )
                
                # 等待指定时间
                time.sleep(duration)
                
                # 终止AFL++进程
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                
                # 分析AFL++输出结果
                stats_file = output_dir / "default" / "fuzzer_stats"
                if stats_file.exists():
                    with open(stats_file, 'r') as f:
                        stats_content = f.read()
                        
                    # 解析统计信息
                    for line in stats_content.split('\n'):
                        if 'execs_done' in line:
                            fuzz_result['total_executions'] = int(line.split(':')[1].strip())
                        elif 'saved_crashes' in line:
                            fuzz_result['unique_crashes'] = int(line.split(':')[1].strip())
                        elif 'execs_per_sec' in line:
                            fuzz_result['execution_speed'] = float(line.split(':')[1].strip())
                        elif 'stability' in line:
                            stability_str = line.split(':')[1].strip().rstrip('%')
                            fuzz_result['stability'] = float(stability_str) / 100.0
                
                # 检查是否发现了crash，如果有则保存调试信息
                if fuzz_result['unique_crashes'] > 0:
                    log_warning(f"      发现 {fuzz_result['unique_crashes']} 个crash，保存调试信息...")
                    try:
                        # 保存crash调试信息
                        self.save_crash_debug_info(
                            harness_name=binary_path.stem,
                            binary_path=binary_path,
                            crash_dir=output_dir,
                            afl_cmd=cmd,
                            fuzz_duration=duration,
                            crash_count=fuzz_result['unique_crashes']
                        )
                    except Exception as e:
                        log_error(f"      保存crash调试信息时出错: {str(e)}")
                
                # 收集覆盖率信息 - 在临时目录还存在时直接处理
                queue_dir = output_dir / "default" / "queue"
                if queue_dir.exists():
                    # 直接在这里处理覆盖率，避免临时目录被删除后无法访问
                    try:
                        coverage_file = Path(f"/tmp/afl_batch_coverage_{binary_path.stem}_{os.getpid()}.txt")
                        
                        # 使用afl-showmap批量处理
                        cmd = [
                            'afl-showmap',
                            '-C',  # 收集覆盖率模式
                            '-i', str(queue_dir),  # 输入目录
                            '-o', str(coverage_file),
                            '-t', '5000',  # 超时5秒
                            '-q',  # 静默模式
                            '--',
                            str(binary_path),
                            '@@'  # 文件路径占位符
                        ]
                        
                        result = subprocess.run(
                            cmd,
                            capture_output=True,
                            timeout=30,  # 批量处理需要更长时间
                            text=True
                        )
                        
                        if result.returncode == 0 and coverage_file.exists():
                            # 解析覆盖率文件
                            bitmap = set()
                            try:
                                with open(coverage_file, 'r') as f:
                                    for line in f:
                                        line = line.strip()
                                        if ':' in line:
                                            edge_id = line.split(':')[0]
                                            bitmap.add(edge_id)
                                fuzz_result['coverage_bitmap'].update(bitmap)
                                log_info(f"        成功收集覆盖率: {len(bitmap)} 个边")
                            except Exception as e:
                                log_warning(f"        解析覆盖率文件失败: {e}")
                            finally:
                                # 清理临时文件
                                if coverage_file.exists():
                                    coverage_file.unlink()
                        else:
                            log_warning(f"        afl-showmap失败 (返回码: {result.returncode})")
                            if result.stderr:
                                log_warning(f"        错误信息: {result.stderr}")
                    except Exception as e:
                        log_warning(f"        覆盖率收集异常: {e}")
                    
                    fuzz_result['coverage_growth'].append(len(fuzz_result['coverage_bitmap']))
                
                log_info(f"      AFL++测试完成: 执行{fuzz_result['total_executions']}次, 覆盖率{len(fuzz_result['coverage_bitmap'])}")
                
                # 如果AFL++没有执行任何测试用例，可能是因为程序没有用AFL++编译
                if fuzz_result['total_executions'] == 0:
                    raise RuntimeError(f"AFL++未能执行任何测试用例，可能程序未用AFL++编译: {binary_path}")
                
        except Exception as e:
            log_error(f"      AFL++模糊测试失败: {str(e)}")
            
        return fuzz_result
    
    def analyze_harness_coverage(self, harness_info: Dict) -> Dict:
        """通过实际模糊测试分析harness的质量（在临时目录编译并测试）"""
        source_file = harness_info['source']
        harness_name = Path(source_file).name
        
        log_info(f"  分析harness质量: {harness_name}")
        
        # 在临时目录编译harness
        compile_success, binary_path, temp_dir = self._compile_harness_in_tmp(source_file)
        
        if not compile_success:
            log_error(f"编译失败，跳过覆盖率测试: {harness_name}")
            return {
                'harness': harness_name,
                'source_path': str(source_file),
                'compile_failed': True,
                'quality_score': 0.0  # 编译失败的harness质量分数为0
            }
        
        analysis_result = {
            'harness': harness_name,
            'source_path': str(source_file),
            'binary_path': str(binary_path),
            'fuzz_duration': 10,
            'compile_failed': False
        }
        
        # 进行限时模糊测试
        fuzz_result = self.fuzz_harness_with_timeout(binary_path, fuzz_duration=10)
        
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            log_info(f"清理临时目录: {temp_dir}")
        except:
            pass
        
        # 更新分析结果
        analysis_result.update({
            'total_bitmap': fuzz_result['coverage_bitmap'],
            'total_executions': fuzz_result['total_executions'],
            'execution_speed': fuzz_result['execution_speed'],
            'stability': fuzz_result['stability'],
            'unique_crashes': fuzz_result['unique_crashes']
        })
        
        # 计算覆盖率增长率
        if len(fuzz_result['coverage_growth']) > 1:
            initial_coverage = fuzz_result['coverage_growth'][0] if fuzz_result['coverage_growth'] else 0
            final_coverage = fuzz_result['coverage_growth'][-1] if fuzz_result['coverage_growth'] else 0
            analysis_result['coverage_growth_rate'] = (final_coverage - initial_coverage) / analysis_result['fuzz_duration']
        else:
            analysis_result['coverage_growth_rate'] = 0.0
        
        # 计算相对于全局位图的新覆盖率
        analysis_result['new_coverage'] = analysis_result['total_bitmap'] - self.global_bitmap
        analysis_result['coverage_gain'] = len(analysis_result['new_coverage'])
        
        # 计算综合质量分数
        # 基础分数：覆盖率增益是最重要的指标
        coverage_score = analysis_result['coverage_gain'] * 10  # 覆盖率增益权重最高
        
        # 执行速度分数（执行失败的harness得0分）
        if analysis_result['total_executions'] == 0:
            speed_score = 0
            stability_score = 0
            growth_score = 0
        else:
            speed_score = min(analysis_result['execution_speed'] / 100, 10)  # 执行速度，最高10分
            stability_score = analysis_result['stability'] * 5  # 稳定性，最高5分
            growth_score = analysis_result['coverage_growth_rate'] * 20  # 覆盖率增长率
        
        analysis_result['quality_score'] = coverage_score + speed_score + stability_score + growth_score
        
        log_info(f"    质量分数: {analysis_result['quality_score']:.2f} (执行{analysis_result['total_executions']}次, 稳定性{analysis_result['stability']:.2f}, 新覆盖率{analysis_result['coverage_gain']})")
        
        # 移除total_bitmap字段，只保留必要的统计信息
        # 保留total_bitmap的set格式用于内部计算，但不保存到JSON中
        temp_total_bitmap = analysis_result['total_bitmap']
        temp_new_coverage = analysis_result['new_coverage']
        
        # 从结果中移除total_bitmap和new_coverage，减少文件大小
        del analysis_result['total_bitmap']
        del analysis_result['new_coverage']
        
        # 为了后续处理，临时保存这些信息
        analysis_result['_temp_total_bitmap'] = temp_total_bitmap
        analysis_result['_temp_new_coverage'] = temp_new_coverage
        
        return analysis_result
    
    def select_best_harnesses(self, coverage_analyses: List[Dict], max_harnesses=3) -> List[Dict]:
        """基于综合质量分数选择最佳harness"""
        log_info(f"选择最佳 Harness (基于综合质量评分) - 最多选择{max_harnesses}个")
        
        if not coverage_analyses:
            log_warning("没有可分析的harness")
            return []
        
        # 显示所有harness的质量分数
        for analysis in coverage_analyses:
            if analysis.get('compile_failed', False):
                log_info(f"  {analysis['harness']}: 质量分数={analysis['quality_score']:.2f} (编译失败)")
            else:
                log_info(f"  {analysis['harness']}: 质量分数={analysis['quality_score']:.2f} "
                      f"(覆盖率={analysis.get('coverage_gain', 0)}, 速度={analysis.get('execution_speed', 0):.1f}/s, "
                      f"稳定性={analysis.get('stability', 0):.2f}, 增长率={analysis.get('coverage_growth_rate', 0):.2f})")
        
        # 按综合质量分数排序，选择表现最好的
        all_harnesses = sorted(coverage_analyses, key=lambda x: x['quality_score'], reverse=True)
        
        # 选择最佳harness并更新全局覆盖率
        selected_harnesses = []
        temp_global_bitmap = self.global_bitmap.copy()
        
        for analysis in all_harnesses:
            if len(selected_harnesses) >= max_harnesses:
                break
            
            # 跳过编译失败的harness
            if analysis.get('compile_failed', False):
                continue
                
            current_new_coverage = analysis['_temp_total_bitmap'] - temp_global_bitmap
            
            # 简化选择策略：直接按分数排序选择
            selected_harnesses.append(analysis)
            temp_global_bitmap.update(analysis['_temp_total_bitmap'])
            
            selection_reason = f"质量分数: {analysis['quality_score']:.2f}"
            if len(current_new_coverage) > 0:
                selection_reason += f", 新增覆盖率: {len(current_new_coverage)}"
                
                log_success(f"  ✓ 选择harness: {analysis['harness']} "
                      f"(质量分数: {analysis['quality_score']:.2f}, {selection_reason})")
                
                # 限制选择的harness数量为指定的最大值
                if len(selected_harnesses) >= max_harnesses:
                    break
        
        # 确保至少选择一个harness（如果有的话），但跳过编译失败的
        if not selected_harnesses and all_harnesses:
            # 寻找第一个编译成功的harness作为保底选择
            for analysis in all_harnesses:
                if not analysis.get('compile_failed', False):
                    selected_harnesses.append(analysis)
                    temp_global_bitmap.update(analysis['_temp_total_bitmap'])
                    log_warning(f"  ⚠ 保底选择: {analysis['harness']} "
                              f"(质量分数: {analysis['quality_score']:.2f})")
                    break
        
        # 更新全局覆盖率
        self.global_bitmap = temp_global_bitmap
        
        return selected_harnesses
    
    def filter_harnesses(self, execution_filtered_dir, final_dir=None, max_harnesses=3) -> List[Dict]:
        """执行代码覆盖率筛选"""
        log_info("OGHarn 第三步：代码覆盖率筛选 (Oracle 引导机制)")
        
        # 从执行过滤后的文件夹加载harness
        execution_successful_harnesses = self.load_execution_successful_harnesses_from_folder(execution_filtered_dir)
        self.coverage_stats['total_harnesses'] = len(execution_successful_harnesses)
        
        if not execution_successful_harnesses:
            log_error("没有找到执行成功的harness")
            return []
        
        log_info(f"开始分析 {len(execution_successful_harnesses)} 个执行成功的harness的代码覆盖率")
        
        # 分析每个harness的覆盖率
        coverage_analyses = []
        for harness_info in execution_successful_harnesses:
            analysis = self.analyze_harness_coverage(harness_info)
            coverage_analyses.append(analysis)
            
            # 更新统计信息（简化版本，不再按质量分类）
            if analysis.get('compile_failed', False):
                self.coverage_stats['coverage_failed'] += 1
            elif analysis.get('total_executions', 0) > 0:
                self.coverage_stats['coverage_success'] += 1
            else:
                self.coverage_stats['coverage_failed'] += 1
        
        # 选择最佳harness
        best_harnesses = self.select_best_harnesses(coverage_analyses, max_harnesses)
        self.coverage_stats['best_harnesses'] = [h['harness'] for h in best_harnesses]
        self.coverage_stats['coverage_analysis'] = coverage_analyses
        
        # 创建最终目录并复制最佳harness
        if final_dir and best_harnesses:
            final_path = Path(final_dir)
            final_path.mkdir(parents=True, exist_ok=True)
            
            log_info(f"\n复制最佳harness到最终目录: {final_path}")
            for harness in best_harnesses:
                # 从执行成功的harness中找到对应的源文件
                for exec_harness in execution_successful_harnesses:
                    if Path(exec_harness['source']).name == harness['harness']:
                        source_file = Path(exec_harness['source'])
                        dest_file = final_path / source_file.name
                        shutil.copy2(source_file, dest_file)
                        log_success(f"  已复制最佳harness: {dest_file}")
                        break
        
        # 清理临时字段，避免保存到JSON中
        for analysis in coverage_analyses:
            if '_temp_total_bitmap' in analysis:
                del analysis['_temp_total_bitmap']
            if '_temp_new_coverage' in analysis:
                del analysis['_temp_new_coverage']
        
        for harness in best_harnesses:
            if '_temp_total_bitmap' in harness:
                del harness['_temp_total_bitmap']
            if '_temp_new_coverage' in harness:
                del harness['_temp_new_coverage']
        
        # 保存分析结果
        self.save_coverage_results(coverage_analyses, best_harnesses)
        
        log_info("模糊测试质量筛选完成:")
        log_info(f"  总数: {self.coverage_stats['total_harnesses']}")
        log_success(f"  成功分析: {self.coverage_stats['coverage_success']}")
        log_info(f"  失败分析: {self.coverage_stats['coverage_failed']}")
        log_success(f"  最终选择: {len(best_harnesses)}")
        log_info(f"  全局覆盖率大小: {len(self.global_bitmap)}")
        
        return best_harnesses
    
    def save_coverage_results(self, coverage_analyses: List[Dict], best_harnesses: List[Dict]):
        """保存覆盖率分析结果"""
        # 保存统计信息
        stats_file = self.log_dir / "step3_coverage_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.coverage_stats, f, indent=2, ensure_ascii=False)
        
        # 保存详细分析结果
        analysis_file = self.log_dir / "step3_coverage_analysis.json"
        with open(analysis_file, 'w', encoding='utf-8') as f:
            json.dump(coverage_analyses, f, indent=2, ensure_ascii=False)
        
        # 保存最佳harness
        best_file = self.log_dir / "step3_best_harnesses.json"
        with open(best_file, 'w', encoding='utf-8') as f:
            json.dump(best_harnesses, f, indent=2, ensure_ascii=False)
        
        # 保存全局覆盖率位图
        bitmap_file = self.log_dir / "global_coverage_bitmap.json"
        with open(bitmap_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.global_bitmap), f, indent=2, ensure_ascii=False)
        
        log_success(f"覆盖率统计信息已保存到: {stats_file}")
        log_success(f"详细分析结果已保存到: {analysis_file}")
        log_success(f"最佳harness已保存到: {best_file}")
        log_success(f"全局覆盖率位图已保存到: {bitmap_file}")

def coverage_filter(execution_filtered_dir, seeds_valid_dir, final_dir=None, max_harnesses=3, dict_file=None, coverage_log_dir=None, config_parser=None):
    """基于模糊测试质量的harness筛选API接口"""
    # 创建覆盖率筛选器
    filter = CoverageFilter(coverage_log_dir or execution_filtered_dir, seeds_valid_dir, dict_file, config_parser)
    
    # 设置正确的目录
    if coverage_log_dir:
        filter.log_dir = Path(coverage_log_dir)  # 保存step3结果的目录
        # 确保目录存在
        filter.log_dir.mkdir(parents=True, exist_ok=True)
    else:
        filter.log_dir = Path(execution_filtered_dir)  # 如果没有指定，则使用执行过滤目录
    
    # 执行筛选
    best_harnesses = filter.filter_harnesses(execution_filtered_dir, final_dir, max_harnesses)
    
    log_info("模糊测试质量评估完成")
    log_success(f"最终选择的最佳harness数量: {len(best_harnesses)}")
    
    if best_harnesses:
        log_info("最佳harness列表:")
        for i, harness in enumerate(best_harnesses, 1):
            quality_score = harness.get('quality_score', 0)
            coverage_gain = harness.get('coverage_gain', 0)
            log_success(f"  {i}. {harness['harness']} (质量分数: {quality_score:.2f}, 覆盖率增益: {coverage_gain})")
    
    return best_harnesses

def main():
    """命令行入口（保持兼容性）"""
    if len(sys.argv) != 3:
        log_error("用法: python step3_coverage_filter.py <log_dir> <seeds_valid_dir>")
        sys.exit(1)
    
    log_dir = sys.argv[1]
    seeds_valid_dir = sys.argv[2]
    
    coverage_filter(log_dir, seeds_valid_dir)

if __name__ == "__main__":
    main()