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
    
    def execute_harness_with_seed(self, binary_path: Path, seed_file: Path, timeout: int = 5) -> Tuple[bool, str, int]:
        """使用种子文件执行harness"""
        try:
            # 使用AFL++的showmap来执行并获取覆盖率信息
            # AFL++可用性已在初始化时检查，此处直接使用
            cmd = [
                'afl-showmap',
                '-o', '/dev/stdout',
                '-m', '50',  # 内存限制50MB
                '-t', str(timeout * 1000),  # 超时时间(毫秒)
                '--',
                str(binary_path)
            ]
            
            # 将种子文件作为stdin输入
            with open(seed_file, 'rb') as f:
                seed_data = f.read()
            
            result = subprocess.run(
                cmd,
                input=seed_data,
                capture_output=True,
                timeout=timeout + 2
            )
            
            return_code = result.returncode
            output = result.stdout.decode('utf-8', errors='ignore') if result.stdout else ''
            error = result.stderr.decode('utf-8', errors='ignore') if result.stderr else ''
            
            # 检查是否崩溃 (返回码非0通常表示异常)
            if return_code < 0:
                # 负数返回码通常表示被信号终止（崩溃）
                return False, f"Crashed with signal {-return_code}: {error}", return_code
            elif return_code > 0:
                # 正数返回码可能是正常退出或错误
                return True, f"Exit code {return_code}: {output}", return_code
            else:
                # 返回码0表示正常执行
                return True, output, return_code
                
        except subprocess.TimeoutExpired:
            return False, "Execution timeout", -1
        except Exception as e:
            return False, f"Execution error: {str(e)}", -1
    

    def test_harness_with_seeds(self, harness_info: Dict) -> Dict:
        """使用种子文件测试harness（在临时目录编译并执行）"""
        source_file = harness_info['source']
        harness_name = Path(source_file).name
        
        log_info(f"测试harness: {harness_name}")
        
        # 在临时目录编译harness
        compile_success, binary_path, temp_dir = self._compile_harness_in_tmp(source_file)
        
        if not compile_success:
            log_error(f"编译失败，跳过执行测试: {harness_name}")
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
            success, output, return_code = self.execute_harness_with_seed(binary_path, seed_file)
            
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
                elif "crash" in output.lower() or return_code < 0:
                    test_result['crashed'] = True
                
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
        elif test_result['timeout']:
            test_result['execution_success'] = False
            self.execution_stats['timeout_harnesses'].append(harness_name)
        
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