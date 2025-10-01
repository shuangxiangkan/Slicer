#!/usr/bin/env python3
"""
OGHarn 三步筛选流程演示 - 第二步：执行筛选
模拟 CompileHarness.compileHarness 方法的执行阶段，包括崩溃检测和种子文件测试
"""

import subprocess
import json
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
from log import *
from step1_compile_filter import create_compile_utils

class ExecutionFilter:
    
    def __init__(self, log_dir, seeds_valid_dir, compile_log_dir=None, config_parser=None):
        self.log_dir = Path(log_dir)
        self.seeds_valid_dir = Path(seeds_valid_dir)
        self.compile_log_dir = Path(compile_log_dir) if compile_log_dir else self.log_dir
        self.config_parser = config_parser
        self.execution_stats = {
            'total_harnesses': 0,
            'execution_success': 0,
            'execution_failed': 0,
            'crashed_harnesses': [],
            'timeout_harnesses': [],
            'valid_seed_failures': []
        }
        
        # 创建编译工具
        self.compile_utils = create_compile_utils(config_parser)
        
        # 创建失败调试信息目录
        self.debug_dir = self.log_dir / "execution_failures"
        self.debug_dir.mkdir(parents=True, exist_ok=True)
    
    def save_execution_failure_debug_info(self, harness_name: str, binary_path: Path, seed_file: Path, 
                                        cmd: List[str], output: str, error: str, return_code: int):
        """保存执行失败的调试信息"""
        try:
            # 为每个失败的harness创建单独的目录
            failure_dir = self.debug_dir / f"{harness_name}_{seed_file.stem}_failure"
            failure_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制二进制文件
            if binary_path.exists():
                dest_binary = failure_dir / binary_path.name
                shutil.copy2(binary_path, dest_binary)
                log_info(f"已保存失败的二进制文件: {dest_binary}")
            
            # 复制种子文件
            if seed_file.exists():
                dest_seed = failure_dir / f"seed_{seed_file.name}"
                shutil.copy2(seed_file, dest_seed)
                log_info(f"已保存失败的种子文件: {dest_seed}")
            
            # 保存执行命令和结果信息
            debug_info = {
                'harness_name': harness_name,
                'binary_path': str(binary_path),
                'seed_file': str(seed_file),
                'command': cmd,
                'return_code': return_code,
                'stdout': output,
                'stderr': error,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'reproduction_command': f"cd {failure_dir} && {' '.join(cmd[:-1])} ./{binary_path.name} < seed_{seed_file.name}",
                'note': f"对应的源文件: {harness_name}.c (根据二进制文件名推断)"
            }
            
            debug_file = failure_dir / "debug_info.json"
            with open(debug_file, 'w', encoding='utf-8') as f:
                json.dump(debug_info, f, indent=2, ensure_ascii=False)
            
            # 创建重现脚本
            reproduce_script = failure_dir / "reproduce.sh"
            with open(reproduce_script, 'w', encoding='utf-8') as f:
                f.write("#!/bin/bash\n")
                f.write("# 重现执行失败的脚本\n")
                f.write(f"# 原始命令: {' '.join(cmd)}\n")
                f.write(f"# 返回码: {return_code}\n\n")
                f.write(f"echo \"执行失败的harness: {harness_name}\"\n")
                f.write(f"echo \"种子文件: seed_{seed_file.name}\"\n")
                f.write(f"echo \"二进制文件: {binary_path.name}\"\n")
                f.write("echo \"开始重现执行...\"\n\n")
                
                # 构建重现命令
                simple_cmd = f"./{binary_path.name} < seed_{seed_file.name}"
                f.write(f"{simple_cmd}\n")
                f.write("echo \"执行完成，返回码: $?\"\n")
            
            # 设置脚本可执行权限
            reproduce_script.chmod(0o755)
            
            log_info(f"执行失败调试信息已保存到: {failure_dir}")
            log_info(f"重现脚本: {reproduce_script}")
            
        except Exception as e:
            log_error(f"保存执行失败调试信息时出错: {str(e)}")  

    def _compile_harness_in_tmp(self, source_file):
        """在临时目录编译harness"""
        return self.compile_utils.compile_harness_in_temp(source_file, "execution")
    
    def load_compiled_harnesses_from_folder(self, compiled_harness_dir) -> List[Dict]:
        """从编译过滤后的文件夹加载harness列表"""
        compiled_dir = Path(compiled_harness_dir)
        if not compiled_dir.exists():
            log_error(f"编译过滤后的文件夹不存在: {compiled_dir}")
            return []
        
        # 获取所有C/C++文件
        harness_files = list(compiled_dir.glob("*.c")) + list(compiled_dir.glob("*.cpp"))
        
        if not harness_files:
            log_warning(f"在 {compiled_dir} 中未找到任何C/C++文件")
            return []
        
        log_info(f"从 {compiled_dir} 加载了 {len(harness_files)} 个harness文件")
        
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
    
    def execute_harness_with_seed(self, binary_path: Path, seed_file: Path, harness_name: str = None, timeout: int = 5) -> Tuple[bool, str, int]:
        """使用种子文件执行harness"""
        try:
            # 直接执行harness，利用AddressSanitizer自动检测内存错误
            # 构建执行命令：harness + seed_file_path
            cmd = [str(binary_path), str(seed_file)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=timeout,
                text=True
            )
            
            return_code = result.returncode
            output = result.stdout if result.stdout else ''
            error = result.stderr if result.stderr else ''
            
            # 检查是否崩溃或有内存错误
            if return_code < 0:
                # 负数返回码通常表示被信号终止（崩溃）
                error_msg = f"Crashed with signal {-return_code}: {error}"
                log_error(f"执行崩溃 - 二进制: {binary_path.name}, 种子: {seed_file.name}, 信号: {-return_code}, stderr: {error[:100]}")
                # 保存崩溃的调试信息
                self.save_execution_failure_debug_info(harness_name, binary_path, seed_file, cmd, output, error, return_code)
                
                return False, error_msg, return_code
            elif return_code > 0:
                # 正数返回码可能是正常退出或错误
                # 检查是否是AddressSanitizer检测到的内存错误
                if any(keyword in error.lower() for keyword in ['addresssanitizer', 'asan', 'heap-buffer-overflow', 'stack-buffer-overflow', 'use-after-free']):
                    error_msg = f"Memory error detected: {error}"
                    log_error(f"内存错误 - 二进制: {binary_path.name}, 种子: {seed_file.name}, 返回码: {return_code}, stderr: {error[:100]}")
                    # 保存内存错误的调试信息
                    self.save_execution_failure_debug_info(harness_name, binary_path, seed_file, cmd, output, error, return_code)
                    return False, error_msg, return_code
                elif error.strip():  # 如果有其他stderr输出，记录但不认为是失败
                    log_warning(f"执行警告 - 二进制: {binary_path.name}, 种子: {seed_file.name}, 返回码: {return_code}, stderr: {error[:100]}")
                
                return True, f"Exit code {return_code}: {output}", return_code
            else:
                # 返回码0表示正常执行
                return True, output, return_code
                
        except subprocess.TimeoutExpired:
            error_msg = "Execution timeout"
            log_error(f"执行超时 - 二进制: {binary_path.name}, 种子: {seed_file.name}, 超时时间: {timeout}秒")
            # 保存超时的调试信息
            cmd = [str(binary_path), str(seed_file)]
            self.save_execution_failure_debug_info(harness_name, binary_path, seed_file, cmd, error_msg, "", -1)
            
            return False, error_msg, -1
        except Exception as e:
            error_msg = f"Execution error: {str(e)}"
            log_error(f"执行异常 - 二进制: {binary_path.name}, 种子: {seed_file.name}, 异常: {str(e)}")    
            # 保存执行异常的调试信息
            self.save_execution_failure_debug_info(harness_name, binary_path, seed_file, cmd if 'cmd' in locals() else [], error_msg, str(e), -1)
            
            return False, error_msg, -1

    def test_harness_with_seeds(self, harness_info: Dict) -> Dict:
        """使用种子文件测试harness（在临时目录编译并执行）"""
        source_file = harness_info['source']
        harness_name = Path(source_file).name
        
        log_info(f"测试harness: {harness_name}")
        
        # 在临时目录编译harness
        compile_success, binary_path, temp_dir = self._compile_harness_in_tmp(source_file)
        
        if not compile_success:
            log_error(f"编译失败，跳过执行测试: {harness_name} (源文件: {source_file})")
            return {
                'harness': harness_name,
                'source_path': str(source_file),
                'valid_seed_results': [],
                'crashed': False,
                'timeout': False,
                'execution_success': False,
                'compile_failed': True
            }
        
        test_result = {
            'harness': harness_name,
            'source_path': str(source_file),
            'binary_path': str(binary_path),
            'temp_dir': str(temp_dir),
            'valid_seed_results': [],
            'crashed': False,
            'timeout': False,
            'execution_success': True,
            'compile_failed': False
        }
        
        # 测试有效种子
        valid_seeds = self.get_seed_files(self.seeds_valid_dir)
        log_info(f"测试 {len(valid_seeds)} 个有效种子")
        
        for seed_file in valid_seeds:
            success, output, return_code = self.execute_harness_with_seed(binary_path, seed_file, harness_name)
            
            result_info = {
                'seed_file': str(seed_file),
                'success': success,
                'output': output[:200],  # 限制输出长度
                'return_code': return_code
            }
            
            test_result['valid_seed_results'].append(result_info)
            
            if not success:
                if "timeout" in output.lower():
                    test_result['timeout'] = True
                    log_error(f"种子执行超时 - Harness: {harness_name}, 种子: {seed_file.name}, 错误: {output[:500]}")
                elif "crash" in output.lower() or return_code < 0:
                    test_result['crashed'] = True
                    log_error(f"种子执行崩溃 - Harness: {harness_name}, 种子: {seed_file.name}, 返回码: {return_code}, 错误: {output[:500]}")
                else:
                    log_error(f"种子执行失败 - Harness: {harness_name}, 种子: {seed_file.name}, 返回码: {return_code}, 错误: {output[:500]}")
                
                # 有效种子执行失败是问题
                self.execution_stats['valid_seed_failures'].append({
                    'harness': harness_name,
                    'seed': str(seed_file),
                    'error': output
                })
        
        # 判断整体执行是否成功
        if test_result['crashed']:
            test_result['execution_success'] = False
            self.execution_stats['crashed_harnesses'].append(harness_name)
            log_error(f"Harness整体执行失败(崩溃) - {harness_name}, 崩溃种子数: {len([r for r in test_result['valid_seed_results'] if not r['success'] and r['return_code'] < 0])}")
        elif test_result['timeout']:
            test_result['execution_success'] = False
            self.execution_stats['timeout_harnesses'].append(harness_name)
            log_error(f"Harness整体执行失败(超时) - {harness_name}, 超时种子数: {len([r for r in test_result['valid_seed_results'] if not r['success'] and 'timeout' in r['output'].lower()])}")
        else:
            log_info(f"Harness执行成功 - {harness_name}, 成功种子数: {len([r for r in test_result['valid_seed_results'] if r['success']])}/{len(test_result['valid_seed_results'])}")
        
        # 清理临时目录
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
            log_info(f"清理临时目录: {temp_dir}")
        except:
            pass
        
        # 移除临时目录信息，避免保存到JSON中
        if 'temp_dir' in test_result:
            del test_result['temp_dir']
        
        return test_result
    
    def filter_harnesses(self, compiled_harness_dir, executable_harness_dir=None) -> List[Dict]:
        """执行筛选所有harness"""
        log_info("OGHarn 第二步：执行筛选")
        
        # 从编译过滤后的文件夹加载harness
        compiled_harnesses = self.load_compiled_harnesses_from_folder(compiled_harness_dir)
        self.execution_stats['total_harnesses'] = len(compiled_harnesses)
        
        if not compiled_harnesses:
            log_warning("没有找到编译成功的harness")
            return []
        
        log_info(f"开始测试 {len(compiled_harnesses)} 个编译成功的harness")
        
        # 创建下一阶段目录
        if executable_harness_dir:
            next_stage_path = Path(executable_harness_dir)
            next_stage_path.mkdir(parents=True, exist_ok=True)
        
        successful_harnesses = []
        all_test_results = []
        
        for harness_info in compiled_harnesses:
            test_result = self.test_harness_with_seeds(harness_info)
            all_test_results.append(test_result)
            
            if test_result['execution_success']:
                # 保存成功执行的harness信息（只保存源文件路径）
                successful_harness = {
                    'source': harness_info['source']
                }
                successful_harnesses.append(successful_harness)
                self.execution_stats['execution_success'] += 1
                
                # 复制成功执行的源文件到下一阶段目录
                source_file = Path(harness_info['source'])
                dest_file = next_stage_path / source_file.name
                shutil.copy2(source_file, dest_file)
                log_info(f"已复制到下一阶段: {dest_file}")
            else:
                self.execution_stats['execution_failed'] += 1
        
        # 保存详细测试结果
        self.save_execution_results(all_test_results)
        
        log_info("执行筛选完成")
        failed_count = self.execution_stats['total_harnesses'] - self.execution_stats['execution_success']
        if failed_count == 0:
            log_success(f"执行完成: 总数{self.execution_stats['total_harnesses']}, 全部成功")
        else:
            log_warning(f"执行完成: 总数{self.execution_stats['total_harnesses']}, 成功{self.execution_stats['execution_success']}, 失败{failed_count}")
        if self.execution_stats['crashed_harnesses']:
            log_warning(f"崩溃: {len(self.execution_stats['crashed_harnesses'])}个")
        if self.execution_stats['timeout_harnesses']:
            log_warning(f"超时: {len(self.execution_stats['timeout_harnesses'])}个")
        
        return successful_harnesses
    
    def save_execution_results(self, test_results: List[Dict]):
        """保存执行结果"""
        # 确保日志目录存在
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存统计信息
        stats_file = self.log_dir / "step2_execution_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.execution_stats, f, indent=2, ensure_ascii=False)
        
        # 保存详细测试结果
        results_file = self.log_dir / "step2_execution_results.json"
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False)
        
        log_info(f"执行统计信息已保存到: {stats_file}")
        log_info(f"详细执行结果已保存到: {results_file}")

def execution_filter(log_dir, seeds_valid_dir, compiled_harness_dir, executable_harness_dir=None, config_parser=None):
    """执行筛选API接口"""
    # 创建执行筛选器
    filter = ExecutionFilter(log_dir, seeds_valid_dir, log_dir, config_parser)
    
    # 执行筛选
    successful_harnesses = filter.filter_harnesses(compiled_harness_dir, executable_harness_dir)
    
    # 确保日志目录存在
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    # 保存执行筛选摘要（不再保存详细文件列表）
    summary_file = log_dir_path / "step2_execution_summary.json"
    summary_data = {
        'total_harnesses': filter.execution_stats['total_harnesses'],
        'successful_harnesses': filter.execution_stats['execution_success'],
        'failed_harnesses': filter.execution_stats['execution_failed'],
        'crashed_harnesses': len(filter.execution_stats['crashed_harnesses']),
        'timeout_harnesses': len(filter.execution_stats['timeout_harnesses']),
        'success_rate': filter.execution_stats['execution_success'] / max(filter.execution_stats['total_harnesses'], 1),
        'note': f"成功执行的源文件已复制到: {executable_harness_dir}"
    }
    
    with open(summary_file, 'w', encoding='utf-8') as f:
        json.dump(summary_data, f, indent=2, ensure_ascii=False)
    
    log_info(f"执行摘要已保存到: {summary_file}")
    log_success(f"通过执行筛选的harness数量: {len(successful_harnesses)}")
    
    return successful_harnesses

def main():
    """命令行入口（保持兼容性）"""
    import sys
    if len(sys.argv) != 3:
        log_error("用法: python step2_execution_filter.py <log_dir> <seeds_valid_dir>")
        sys.exit(1)
    
    log_dir = sys.argv[1]
    seeds_valid_dir = sys.argv[2]
    
    execution_filter(log_dir, seeds_valid_dir)

if __name__ == "__main__":
    main()