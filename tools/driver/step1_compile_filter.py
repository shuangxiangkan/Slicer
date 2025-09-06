#!/usr/bin/env python3
"""
三步筛选流程演示 - 第一步：编译筛选
模拟 CompileHarness.checkSequence 和 compileHarness 方法的编译阶段
"""

import subprocess
import json
import shutil
from pathlib import Path
from log import *

class CompileFilter:
    def __init__(self, harness_dir, output_dir, log_dir):
        self.harness_dir = Path(harness_dir)
        self.output_dir = Path(output_dir)
        self.log_dir = Path(log_dir)
        self.compile_stats = {
            'total': 0,
            'compile_success': 0,
            'compile_failed': 0,
            'failed_harnesses': []
        }
        
        # 在初始化时检查AFL++可用性，如果不可用直接报错
        if not self._check_afl_available():
            log_error("AFL++不可用，请确保已安装AFL++并在PATH中")
            raise RuntimeError("AFL++不可用，请确保已安装AFL++并在PATH中")
    
    def _check_afl_available(self) -> bool:
        """检查AFL++是否可用（私有方法，仅在初始化时调用）"""
        try:
            # 使用which命令检查afl-clang-fast++是否存在
            result = subprocess.run(['which', 'afl-clang-fast++'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def compile_harness(self, harness_file):
        """编译单个harness文件"""
        log_info(f"正在编译 harness: {harness_file.name}")
        
        # 使用AFL++编译器进行插桩编译
        output_binary = self.output_dir / f"{harness_file.stem}_compiled"
        
        try:
            # 编译命令 - 使用afl-clang-fast++进行AFL++插桩
            compile_cmd = [
                'afl-clang-fast++', 
                '-o', str(output_binary),
                str(harness_file),
                '-g',  # 调试信息
                '-O0', # 无优化，便于调试和覆盖率统计
                '-fsanitize-coverage=trace-pc-guard'  # AFL++覆盖率插桩
            ]
            
            result = subprocess.run(
                compile_cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0:
                log_success(f"编译成功: {harness_file.name}")
                self.compile_stats['compile_success'] += 1
                return True, output_binary, result.stdout
            else:
                log_error(f"编译失败 [{harness_file.name}]: {result.stderr}")
                self.compile_stats['compile_failed'] += 1
                self.compile_stats['failed_harnesses'].append({
                    'file': harness_file.name,
                    'error': result.stderr
                })
                return False, None, result.stderr
                
        except subprocess.TimeoutExpired:
            log_error(f"编译失败 [{harness_file.name}]: 编译超时")
            self.compile_stats['compile_failed'] += 1
            self.compile_stats['failed_harnesses'].append({
                'file': harness_file.name,
                'error': 'Compilation timeout'
            })
            return False, None, "Compilation timeout"
        except Exception as e:
            log_error(f"编译失败 [{harness_file.name}]: 编译异常 - {str(e)}")
            self.compile_stats['compile_failed'] += 1
            self.compile_stats['failed_harnesses'].append({
                'file': harness_file.name,
                'error': str(e)
            })
            return False, None, str(e)
    
    def filter_harnesses(self, next_stage_dir=None):
        """筛选所有harness文件"""
        log_info("三步筛选流程 - 第一步：编译筛选")
        log_info(f"扫描目录: {self.harness_dir}")
        
        # 获取所有C/C++文件
        harness_files = list(self.harness_dir.glob("*.c")) + list(self.harness_dir.glob("*.cpp"))
        self.compile_stats['total'] = len(harness_files)
        
        if not harness_files:
            log_warning("未找到任何C/C++文件")
            return []
        
        log_info(f"找到 {len(harness_files)} 个harness文件")
        
        successful_harnesses = []
        
        # 创建下一阶段目录
        if next_stage_dir:
            next_stage_path = Path(next_stage_dir)
            next_stage_path.mkdir(parents=True, exist_ok=True)
        
        for harness_file in harness_files:
            success, binary_path, output = self.compile_harness(harness_file)
            if success:
                harness_info = {
                    'source': harness_file,
                    'binary': binary_path,
                    'compile_output': output
                }
                successful_harnesses.append(harness_info)
                
                # 复制成功编译的源文件到下一阶段目录
                if next_stage_dir:
                    dest_file = next_stage_path / harness_file.name
                    shutil.copy2(harness_file, dest_file)
                    log_info(f"已复制到下一阶段: {dest_file}")
        
        # 保存编译统计信息
        self.save_compile_stats()
        
        log_info("编译筛选完成")
        failed_count = self.compile_stats['total'] - self.compile_stats['compile_success']
        if failed_count == 0:
            log_success(f"编译完成: 总数{self.compile_stats['total']}, 全部成功")
        else:
            log_warning(f"编译完成: 总数{self.compile_stats['total']}, 成功{self.compile_stats['compile_success']}, 失败{failed_count}")
        
        return successful_harnesses
    
    def save_compile_stats(self):
        """保存编译统计信息"""
        stats_file = self.log_dir / "step1_compile_stats.json"
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.compile_stats, f, indent=2, ensure_ascii=False)
        log_info(f"编译统计信息已保存到: {stats_file}")

def compile_filter(harness_dir, output_dir, log_dir, next_stage_dir=None):
    """编译筛选API接口"""
    # 确保输出目录存在
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    
    # 创建编译筛选器
    filter = CompileFilter(harness_dir, output_dir, log_dir)
    
    # 执行筛选
    successful_harnesses = filter.filter_harnesses(next_stage_dir)
    
    # 保存成功编译的harness列表
    success_file = Path(log_dir) / "step1_successful_harnesses.json"
    success_data = [{
        'source': str(h['source']),
        'binary': str(h['binary'])
    } for h in successful_harnesses]
    
    with open(success_file, 'w', encoding='utf-8') as f:
        json.dump(success_data, f, indent=2, ensure_ascii=False)
    
    log_info(f"成功编译的harness列表已保存到: {success_file}")
    log_success(f"通过编译筛选的harness数量: {len(successful_harnesses)}")
    
    return successful_harnesses

def main():
    """命令行入口（保持兼容性）"""
    import sys
    if len(sys.argv) != 4:
        log_error("用法: python step1_compile_filter.py <harness_dir> <output_dir> <log_dir>")
        sys.exit(1)
    
    harness_dir = sys.argv[1]
    output_dir = sys.argv[2]
    log_dir = sys.argv[3]
    
    compile_filter(harness_dir, output_dir, log_dir)

if __name__ == "__main__":
    main()