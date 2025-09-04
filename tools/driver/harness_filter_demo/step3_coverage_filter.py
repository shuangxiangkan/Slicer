#!/usr/bin/env python3
"""
OGHarn 三步筛选流程演示 - 第三步：代码覆盖率筛选
模拟 OGHarn 的 Oracle 引导机制，通过代码覆盖率分析选择最佳 harness
"""

import subprocess
import json
import shutil
import tempfile
import time
import sys
from pathlib import Path
from typing import List, Dict, Set

class CoverageFilter:
    def __init__(self, log_dir, seeds_valid_dir):
        self.log_dir = Path(log_dir)
        self.seeds_valid_dir = Path(seeds_valid_dir)
        self.global_bitmap = set()  # 模拟 OGHarn 的 globalBitmap
        self.coverage_stats = {
            'total_harnesses': 0,
            'coverage_success': 0,
            'coverage_failed': 0,
            'no_new_coverage': 0,
            'linear_coverage': 0,
            'best_harnesses': [],
            'coverage_analysis': []
        }
        
        # 在初始化时检查AFL++可用性，如果不可用直接报错
        if not self._check_afl_available():
            raise RuntimeError("AFL++不可用，请确保已安装AFL++并在PATH中")
    
    def load_execution_successful_harnesses(self) -> List[Dict]:
        """加载第二步执行成功的harness列表"""
        success_file = self.log_dir / "step2_successful_harnesses.json"
        if not success_file.exists():
            print(f"错误: 未找到执行成功的harness列表文件: {success_file}")
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
    
    def get_coverage_bitmap(self, binary_path: Path, seed_file: Path) -> Set[str]:
        """获取代码覆盖率位图，只使用 AFL++ 的 showmap"""
        try:
            return self.get_afl_coverage(binary_path, seed_file)
        except Exception as e:
            print(f"    获取覆盖率失败: {str(e)}")
            return set()
    
    def _check_afl_available(self) -> bool:
        """检查AFL++是否可用"""
        try:
            # 使用which命令检查afl-showmap是否存在
            result = subprocess.run(['which', 'afl-showmap'], capture_output=True, timeout=5)
            return result.returncode == 0
        except:
            return False
    
    def get_afl_coverage(self, binary_path: Path, seed_file: Path) -> Set[str]:
        """使用 AFL++ showmap 获取覆盖率位图"""
        try:
            # 创建临时文件存储覆盖率输出
            coverage_file = self.log_dir / f"coverage_{binary_path.stem}_{seed_file.stem}.txt"
            
            cmd = [
                'afl-showmap',
                '-o', str(coverage_file),
                '-m', '50',  # 内存限制
                '-t', '5000',  # 超时5秒
                '--',
                str(binary_path)
            ]
            
            # 读取种子文件
            with open(seed_file, 'rb') as f:
                seed_data = f.read()
            
            result = subprocess.run(
                cmd,
                input=seed_data,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0 and coverage_file.exists():
                # 解析覆盖率文件，模拟 OGHarn 的 getBitmap 方法
                bitmap = set()
                with open(coverage_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if ':' in line:
                            # AFL++ 输出格式: edge_id:hit_count
                            edge_id = line.split(':')[0]
                            bitmap.add(edge_id)
                
                # 清理临时文件
                coverage_file.unlink()
                return bitmap
            
        except Exception as e:
            print(f"    AFL++ 覆盖率获取失败: {str(e)}")
        
        return set()
      
    def fuzz_harness_with_timeout(self, binary_path: Path, fuzz_duration=10) -> Dict:
        """对harness进行限时模糊测试，评估其真实的模糊测试质量"""
        print(f"    开始对 {binary_path.name} 进行 {fuzz_duration} 秒模糊测试...")
        
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
                print(f"      警告: 没有找到种子文件，种子目录: {self.seeds_valid_dir}")
                return fuzz_result
            
            # 使用所有种子文件进行模糊测试
            print(f"      使用 {len(seed_files)} 个种子文件进行模糊测试")
            
            # AFL++已在初始化时检查，此处直接进行模糊测试
            return self.run_afl_fuzz(binary_path, seed_files, fuzz_duration)
                
        except Exception as e:
            print(f"      模糊测试失败: {str(e)}")
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
                    print(f"        已添加种子文件: {seed_file.name}")
                
                # 运行AFL++模糊测试
                cmd = [
                    'afl-fuzz',
                    '-i', str(input_dir),
                    '-o', str(output_dir),
                    '-t', '1000',  # 1秒超时
                    '-m', '50',    # 50MB内存限制
                    '--',
                    str(binary_path)
                ]
                
                print(f"      启动AFL++模糊测试: {' '.join(cmd)}")
                
                # 启动AFL++进程
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
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
                stats_file = output_dir / "fuzzer_stats"
                if stats_file.exists():
                    with open(stats_file, 'r') as f:
                        stats_content = f.read()
                        
                    # 解析统计信息
                    for line in stats_content.split('\n'):
                        if 'execs_done' in line:
                            fuzz_result['total_executions'] = int(line.split(':')[1].strip())
                        elif 'unique_crashes' in line:
                            fuzz_result['unique_crashes'] = int(line.split(':')[1].strip())
                        elif 'exec_speed' in line:
                            fuzz_result['execution_speed'] = float(line.split(':')[1].strip())
                        elif 'stability' in line:
                            stability_str = line.split(':')[1].strip().rstrip('%')
                            fuzz_result['stability'] = float(stability_str) / 100.0
                
                # 收集覆盖率信息
                queue_dir = output_dir / "queue"
                if queue_dir.exists():
                    for queue_file in queue_dir.iterdir():
                        if queue_file.is_file():
                            bitmap = self.get_coverage_bitmap(binary_path, queue_file)
                            fuzz_result['coverage_bitmap'].update(bitmap)
                            fuzz_result['coverage_growth'].append(len(fuzz_result['coverage_bitmap']))
                
                print(f"      AFL++测试完成: 执行{fuzz_result['total_executions']}次, 覆盖率{len(fuzz_result['coverage_bitmap'])}")
                
                # 如果AFL++没有执行任何测试用例，可能是因为程序没有用AFL++编译
                if fuzz_result['total_executions'] == 0:
                    raise RuntimeError(f"AFL++未能执行任何测试用例，可能程序未用AFL++编译: {binary_path}")
                
        except Exception as e:
            print(f"      AFL++模糊测试失败: {str(e)}")
            
        return fuzz_result
    

    
    def analyze_harness_coverage(self, harness_info: Dict) -> Dict:
        """通过实际模糊测试分析harness的质量"""
        binary_path = Path(harness_info['binary'])
        harness_name = binary_path.name
        
        print(f"  分析harness质量: {harness_name}")
        
        analysis_result = {
            'harness': harness_name,
            'binary_path': str(binary_path),
            'total_bitmap': set(),
            'new_coverage': set(),
            'coverage_gain': 0,
            'fuzz_duration': 10,
            'total_executions': 0,
            'execution_speed': 0,
            'stability': 0.0,
            'unique_crashes': 0,
            'coverage_growth_rate': 0.0,
            'coverage_quality': 'unknown'
        }
        
        # 进行限时模糊测试
        fuzz_result = self.fuzz_harness_with_timeout(binary_path, fuzz_duration=10)
        
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
        
        # 计算相对于全局位图的新覆盖率
        analysis_result['new_coverage'] = analysis_result['total_bitmap'] - self.global_bitmap
        analysis_result['coverage_gain'] = len(analysis_result['new_coverage'])
        
        # 基于模糊测试结果评估质量
        if analysis_result['total_executions'] == 0:
            analysis_result['coverage_quality'] = 'execution_failed'
        elif analysis_result['stability'] < 0.5:
            analysis_result['coverage_quality'] = 'unstable'
        elif analysis_result['coverage_gain'] == 0:
            analysis_result['coverage_quality'] = 'no_new_coverage'
        elif analysis_result['execution_speed'] < 10:  # 每秒少于10次执行
            analysis_result['coverage_quality'] = 'too_slow'
        elif analysis_result['coverage_growth_rate'] < 0.1:  # 覆盖率增长太慢
            analysis_result['coverage_quality'] = 'poor_coverage_growth'
        else:
            analysis_result['coverage_quality'] = 'good'
        
        print(f"    质量评估: {analysis_result['coverage_quality']} (执行{analysis_result['total_executions']}次, 稳定性{analysis_result['stability']:.2f}, 新覆盖率{analysis_result['coverage_gain']})")
        
        # 转换set为list以便JSON序列化
        analysis_result['total_bitmap'] = list(analysis_result['total_bitmap'])
        analysis_result['new_coverage'] = list(analysis_result['new_coverage'])
        
        return analysis_result
    
    def select_best_harnesses(self, coverage_analyses: List[Dict], max_harnesses=3) -> List[Dict]:
        """基于模糊测试质量选择最佳harness"""
        print(f"\n=== 选择最佳 Harness (基于模糊测试质量) - 最多选择{max_harnesses}个 ===")
        
        # 过滤掉质量不好的harness
        good_harnesses = []
        for analysis in coverage_analyses:
            if analysis['coverage_quality'] == 'good':
                good_harnesses.append(analysis)
        
        print(f"质量良好的harness数量: {len(good_harnesses)}")
        
        # 计算综合质量分数
        for analysis in good_harnesses:
            # 综合评分：覆盖率增益 + 执行速度 + 稳定性 + 覆盖率增长率
            coverage_score = analysis['coverage_gain'] * 10  # 覆盖率增益权重最高
            speed_score = min(analysis['execution_speed'] / 100, 10)  # 执行速度，最高10分
            stability_score = analysis['stability'] * 5  # 稳定性，最高5分
            growth_score = analysis['coverage_growth_rate'] * 20  # 覆盖率增长率
            
            analysis['quality_score'] = coverage_score + speed_score + stability_score + growth_score
            
            print(f"  {analysis['harness']}: 质量分数={analysis['quality_score']:.2f} "
                  f"(覆盖率={analysis['coverage_gain']}, 速度={analysis['execution_speed']:.1f}/s, "
                  f"稳定性={analysis['stability']:.2f}, 增长率={analysis['coverage_growth_rate']:.2f})")
        
        # 按综合质量分数排序
        good_harnesses.sort(key=lambda x: x['quality_score'], reverse=True)
        
        # 选择最佳harness并更新全局覆盖率
        selected_harnesses = []
        temp_global_bitmap = self.global_bitmap.copy()
        
        for analysis in good_harnesses:
            current_new_coverage = set(analysis['total_bitmap']) - temp_global_bitmap
            
            # 即使没有新覆盖率，如果质量分数很高也可以选择（考虑执行速度等因素）
            if len(current_new_coverage) > 0 or (len(selected_harnesses) == 0 and analysis['quality_score'] > 10):
                selected_harnesses.append(analysis)
                temp_global_bitmap.update(analysis['total_bitmap'])
                
                print(f"  ✓ 选择harness: {analysis['harness']} "
                      f"(质量分数: {analysis['quality_score']:.2f}, 新增覆盖率: {len(current_new_coverage)})")
                
                # 限制选择的harness数量为指定的最大值
                if len(selected_harnesses) >= max_harnesses:
                    break
        
        # 如果没有选择到任何harness，选择质量分数最高的一个
        if not selected_harnesses and coverage_analyses:
            # 从所有分析结果中选择质量分数最高的
            all_analyses = sorted(coverage_analyses, 
                                key=lambda x: x.get('quality_score', 0), reverse=True)
            if all_analyses:
                best_analysis = all_analyses[0]
                selected_harnesses.append(best_analysis)
                temp_global_bitmap.update(best_analysis['total_bitmap'])
                print(f"  ⚠ 备选: {best_analysis['harness']} (质量: {best_analysis['coverage_quality']})")
        
        # 更新全局覆盖率
        self.global_bitmap = temp_global_bitmap
        
        return selected_harnesses
    
    def filter_harnesses(self, final_dir=None, max_harnesses=3) -> List[Dict]:
        """执行代码覆盖率筛选"""
        print("=== OGHarn 第三步：代码覆盖率筛选 (Oracle 引导机制) ===")
        
        # 加载执行成功的harness
        execution_successful_harnesses = self.load_execution_successful_harnesses()
        self.coverage_stats['total_harnesses'] = len(execution_successful_harnesses)
        
        if not execution_successful_harnesses:
            print("没有找到执行成功的harness")
            return []
        
        print(f"开始分析 {len(execution_successful_harnesses)} 个执行成功的harness的代码覆盖率")
        
        # 分析每个harness的覆盖率
        coverage_analyses = []
        for harness_info in execution_successful_harnesses:
            analysis = self.analyze_harness_coverage(harness_info)
            coverage_analyses.append(analysis)
            
            # 更新统计信息
            if analysis['coverage_quality'] == 'good':
                self.coverage_stats['coverage_success'] += 1
            elif analysis['coverage_quality'] == 'no_new_coverage':
                self.coverage_stats['no_new_coverage'] += 1
            elif analysis['coverage_quality'] in ['execution_failed', 'unstable', 'too_slow', 'poor_coverage_growth']:
                self.coverage_stats['coverage_failed'] += 1
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
            
            print(f"\n复制最佳harness到最终目录: {final_path}")
            for harness in best_harnesses:
                # 从执行成功的harness中找到对应的源文件
                for exec_harness in execution_successful_harnesses:
                    if Path(exec_harness['binary']).name == harness['harness']:
                        source_file = Path(exec_harness['source'])
                        dest_file = final_path / source_file.name
                        shutil.copy2(source_file, dest_file)
                        print(f"  已复制最佳harness: {dest_file}")
                        break
        
        # 保存分析结果
        self.save_coverage_results(coverage_analyses, best_harnesses)
        
        print(f"\n模糊测试质量筛选完成:")
        print(f"  总数: {self.coverage_stats['total_harnesses']}")
        print(f"  高质量: {self.coverage_stats['coverage_success']}")
        print(f"  无新覆盖率: {self.coverage_stats['no_new_coverage']}")
        print(f"  质量问题: {self.coverage_stats['coverage_failed']}")
        print(f"  最终选择: {len(best_harnesses)}")
        print(f"  全局覆盖率大小: {len(self.global_bitmap)}")
        
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
        
        print(f"覆盖率统计信息已保存到: {stats_file}")
        print(f"详细分析结果已保存到: {analysis_file}")
        print(f"最佳harness已保存到: {best_file}")
        print(f"全局覆盖率位图已保存到: {bitmap_file}")

def coverage_filter(log_dir, seeds_valid_dir, final_dir=None, max_harnesses=3):
    """基于模糊测试质量的harness筛选API接口"""
    # 创建覆盖率筛选器
    filter = CoverageFilter(log_dir, seeds_valid_dir)
    
    # 执行筛选
    best_harnesses = filter.filter_harnesses(final_dir, max_harnesses)
    
    print(f"\n=== 模糊测试质量评估完成 ===")
    print(f"最终选择的最佳harness数量: {len(best_harnesses)}")
    
    if best_harnesses:
        print("\n最佳harness列表:")
        for i, harness in enumerate(best_harnesses, 1):
            quality_score = harness.get('quality_score', 0)
            print(f"  {i}. {harness['harness']} (质量分数: {quality_score:.2f}, 覆盖率增益: {harness['coverage_gain']})")
    
    return best_harnesses

def main():
    """命令行入口（保持兼容性）"""
    if len(sys.argv) != 3:
        print("用法: python step3_coverage_filter.py <log_dir> <seeds_valid_dir>")
        sys.exit(1)
    
    log_dir = sys.argv[1]
    seeds_valid_dir = sys.argv[2]
    
    coverage_filter(log_dir, seeds_valid_dir)

if __name__ == "__main__":
    main()