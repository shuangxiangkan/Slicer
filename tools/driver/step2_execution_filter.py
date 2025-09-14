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

class ExecutionFilter:
    
    def __init__(self, log_dir, seeds_valid_dir, compile_log_dir=None):
        self.log_dir = Path(log_dir)
        self.seeds_valid_dir = Path(seeds_valid_dir)
        self.compile_log_dir = Path(compile_log_dir) if compile_log_dir else self.log_dir
        self.execution_stats = {
            'total_harnesses': 0,
            'execution_success': 0,
            'execution_failed': 0,
            'crashed_harnesses': [],
            'timeout_harnesses': [],
            'valid_seed_failures': []
        }
        
        # 在初始化时检查AFL++可用性，如果不可用直接报错
        if not self._check_afl_available():
            log_error("AFL++不可用，请确保已安装AFL++并在PATH中")
            raise RuntimeError("AFL++不可用，请确保已安装AFL++并在PATH中")
    
    def _check_afl_available(self) -> bool:
        """检查AFL++是否可用（私有方法，仅在初始化时调用）"""
        try:
            # 使用which命令检查afl-showmap是否存在
            result = subprocess.run(['which', 'afl-showmap'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def load_compiled_harnesses(self) -> List[Dict]:
        """加载第一步编译成功的harness列表"""
        success_file = self.compile_log_dir / "step1_successful_harnesses.json"
        if not success_file.exists():
            log_error(f"未找到编译成功的harness列表文件: {success_file}")
            return []
        
        with open(success_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
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
        """使用种子文件测试harness"""
        binary_path = Path(harness_info['binary'])
        harness_name = binary_path.name
        
        log_info(f"测试harness: {harness_name}")
        
        test_result = {
            'harness': harness_name,
            'binary_path': str(binary_path),
            'valid_seed_results': [],
            'crashed': False,
            'timeout': False,
            'execution_success': True
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
        
        return test_result
    
    def filter_harnesses(self, next_stage_dir=None) -> List[Dict]:
        """执行筛选所有harness"""
        log_info("OGHarn 第二步：执行筛选")
        
        # 加载编译成功的harness
        compiled_harnesses = self.load_compiled_harnesses()
        self.execution_stats['total_harnesses'] = len(compiled_harnesses)
        
        if not compiled_harnesses:
            log_warning("没有找到编译成功的harness")
            return []
        
        log_info(f"开始测试 {len(compiled_harnesses)} 个编译成功的harness")
        
        # 创建下一阶段目录
        if next_stage_dir:
            next_stage_path = Path(next_stage_dir)
            next_stage_path.mkdir(parents=True, exist_ok=True)
        
        successful_harnesses = []
        all_test_results = []
        
        for harness_info in compiled_harnesses:
            test_result = self.test_harness_with_seeds(harness_info)
            all_test_results.append(test_result)
            
            if test_result['execution_success']:
                successful_harnesses.append(harness_info)
                self.execution_stats['execution_success'] += 1
                
                # 复制成功执行的源文件到下一阶段目录
                if next_stage_dir:
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

def execution_filter(log_dir, seeds_valid_dir, next_stage_dir=None, compile_log_dir=None):
    """执行筛选API接口"""
    # 创建执行筛选器
    filter = ExecutionFilter(log_dir, seeds_valid_dir, compile_log_dir)
    
    # 执行筛选
    successful_harnesses = filter.filter_harnesses(next_stage_dir)
    
    # 确保日志目录存在
    log_dir_path = Path(log_dir)
    log_dir_path.mkdir(parents=True, exist_ok=True)
    
    # 保存通过执行筛选的harness列表
    success_file = log_dir_path / "step2_successful_harnesses.json"
    with open(success_file, 'w', encoding='utf-8') as f:
        json.dump(successful_harnesses, f, indent=2, ensure_ascii=False)
    
    log_info(f"通过执行筛选的harness列表已保存到: {success_file}")
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