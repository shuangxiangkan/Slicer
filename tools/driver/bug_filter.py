#!/usr/bin/env python3
"""
Bug Filter - 过滤误报，找出真正的第三方库设计问题
通过 LLM 分析 crash/execution failures，区分 harness 问题和库设计问题
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, List, Any
from log import log_info, log_success, log_warning, log_error

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from llm.base import create_llm_client
from llm.config import LLMConfig


class BugFilter:
    """分析 failures，区分 harness 问题和库设计问题"""
    
    def __init__(self, library_output_dir: str):
        self.library_output_dir = Path(library_output_dir)
        self.library_name = self.library_output_dir.name
        
        # Initialize LLM client
        try:
            self.llm_config = LLMConfig.from_env()
            self.llm_client = create_llm_client(config=self.llm_config)
            log_info(f"LLM client initialized: {self.llm_client.provider}")
        except Exception as e:
            log_error(f"Failed to initialize LLM client: {e}")
            self.llm_client = None
        
        self.results = {
            'library_bugs': [],      # 库设计问题
            'harness_bugs': [],      # harness 问题
            'analysis_failed': []    # 分析失败
        }
    
    def find_all_failures(self) -> List[Dict[str, Any]]:
        """遍历所有 API 目录，找到所有 failure 信息"""
        failures = []
        
        for api_dir in self.library_output_dir.iterdir():
            if not api_dir.is_dir():
                continue
            
            # 查找 execution_failures
            exec_failures_dir = api_dir / "harness_execution_logs" / "execution_failures"
            if exec_failures_dir.exists():
                for failure_dir in exec_failures_dir.iterdir():
                    if failure_dir.is_dir():
                        failure_info = self._parse_failure(failure_dir, api_dir, "execution")
                        if failure_info:
                            failures.append(failure_info)
            
            # 查找 crash_failures
            crash_failures_dir = api_dir / "harness_coverage_logs" / "crash_failures"
            if crash_failures_dir.exists():
                for failure_dir in crash_failures_dir.iterdir():
                    if failure_dir.is_dir():
                        failure_info = self._parse_failure(failure_dir, api_dir, "crash")
                        if failure_info:
                            failures.append(failure_info)
        
        log_info(f"Found {len(failures)} failures to analyze")
        return failures
    
    def _parse_failure(self, failure_dir: Path, api_dir: Path, failure_type: str) -> Dict[str, Any]:
        """解析单个 failure 目录"""
        debug_info_path = failure_dir / "debug_info.json"
        if not debug_info_path.exists():
            return None
        
        try:
            with open(debug_info_path, 'r') as f:
                debug_info = json.load(f)
            
            # 从 harness_name 推断源文件
            harness_name = debug_info.get('harness_name', '')
            harness_source = None
            harness_dir = api_dir / "harness"
            if harness_dir.exists():
                for harness_file in harness_dir.iterdir():
                    if harness_file.name == harness_name:
                        harness_source = harness_file
                        break
            
            return {
                'failure_type': failure_type,
                'failure_dir': str(failure_dir),
                'api_name': api_dir.name,
                'harness_name': harness_name,
                'harness_source_path': str(harness_source) if harness_source else None,
                'debug_info': debug_info
            }
        except Exception as e:
            log_warning(f"Failed to parse {failure_dir}: {e}")
            return None
    
    def _build_analysis_prompt(self, failure: Dict[str, Any], harness_code: str) -> str:
        """构建 LLM 分析提示"""
        debug_info = failure['debug_info']
        
        prompt = f"""你是一个 fuzzing 专家。请分析以下 crash/failure 信息，判断这是 harness 生成问题还是第三方库C库的设计缺陷。

## 库名称
{self.library_name}

## 错误信息
- Return Code: {debug_info.get('return_code', 'N/A')}
- stderr: {debug_info.get('stderr', 'N/A')}
- stdout: {debug_info.get('stdout', 'N/A')}

## Harness 源代码
```c
{harness_code}
```

## 判断标准
1. **Harness 问题**: 
   - harness 中的 assert 断言不合理（基于错误的假设）
   - harness 使用 API 的方式不正确
   - harness 中的内存管理错误
   - harness 对返回值的处理不当

2. **库设计问题**:
   - 库函数在合法输入下崩溃
   - 库存在内存泄漏/越界等问题
   - 库对边界条件处理不当
   - 库的行为与文档不符

请只回复 JSON 格式：
{{
    "verdict": "harness_bug" 或 "library_bug",
    "confidence": 0.0-1.0,
    "reason": "简短原因说明"
}}
"""
        return prompt
    
    def analyze_failure(self, failure: Dict[str, Any]) -> Dict[str, Any]:
        """使用 LLM 分析单个 failure"""
        if not self.llm_client:
            return {'verdict': 'unknown', 'error': 'LLM client not available'}
        
        # 读取 harness 源代码
        harness_code = ""
        if failure['harness_source_path'] and Path(failure['harness_source_path']).exists():
            with open(failure['harness_source_path'], 'r') as f:
                harness_code = f.read()
        else:
            harness_code = "/* Harness source code not found */"
        
        prompt = self._build_analysis_prompt(failure, harness_code)
        
        try:
            response = self.llm_client.generate_response(prompt)
            # 提取 JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                result = json.loads(response[json_start:json_end])
                return result
        except Exception as e:
            log_warning(f"Analysis failed for {failure['harness_name']}: {e}")
            return {'verdict': 'unknown', 'error': str(e)}
        
        return {'verdict': 'unknown', 'error': 'Failed to parse response'}
    
    def run(self) -> Dict[str, Any]:
        """运行完整的分析流程"""
        failures = self.find_all_failures()
        
        for i, failure in enumerate(failures):
            log_info(f"Analyzing [{i+1}/{len(failures)}]: {failure['harness_name']}")
            
            analysis = self.analyze_failure(failure)
            
            record = {
                'api_name': failure['api_name'],
                'harness_name': failure['harness_name'],
                'harness_source_path': failure['harness_source_path'],
                'failure_dir': failure['failure_dir'],
                'failure_type': failure['failure_type'],
                'analysis': analysis
            }
            
            verdict = analysis.get('verdict', 'unknown')
            if verdict == 'library_bug':
                self.results['library_bugs'].append(record)
                log_success(f"  -> Library bug: {analysis.get('reason', '')}")
            elif verdict == 'harness_bug':
                self.results['harness_bugs'].append(record)
                log_info(f"  -> Harness bug: {analysis.get('reason', '')}")
            else:
                self.results['analysis_failed'].append(record)
                log_warning(f"  -> Analysis failed: {analysis.get('error', '')}")
        
        # 保存结果
        self._save_results()
        return self.results
    
    def _generate_summary(self) -> Dict[str, Any]:
        """生成 API 级别的总结"""
        # 统计每个 API 的 library bug 数量
        library_api_counts = {}
        for bug in self.results['library_bugs']:
            api = bug['api_name']
            library_api_counts[api] = library_api_counts.get(api, 0) + 1
        
        # 统计每个 API 的 harness bug 数量
        harness_api_counts = {}
        for bug in self.results['harness_bugs']:
            api = bug['api_name']
            harness_api_counts[api] = harness_api_counts.get(api, 0) + 1
        
        # 分类 API
        all_library_apis = set(library_api_counts.keys())
        all_harness_apis = set(harness_api_counts.keys())
        
        # 纯库问题 API（只在 library_bugs 中出现）
        pure_library_apis = sorted(all_library_apis - all_harness_apis)
        # 纯 harness 问题 API（只在 harness_bugs 中出现）
        pure_harness_apis = sorted(all_harness_apis - all_library_apis)
        # 混合问题 API（两者都有）
        mixed_apis = sorted(all_library_apis & all_harness_apis)
        
        return {
            'total_library_bugs': len(self.results['library_bugs']),
            'total_harness_bugs': len(self.results['harness_bugs']),
            'total_analysis_failed': len(self.results['analysis_failed']),
            'library_bug_apis': {api: library_api_counts[api] for api in pure_library_apis},
            'harness_bug_apis': {api: harness_api_counts[api] for api in pure_harness_apis},
            'mixed_apis': {
                api: {'library': library_api_counts.get(api, 0), 'harness': harness_api_counts.get(api, 0)}
                for api in mixed_apis
            }
        }
    
    def _save_results(self):
        """保存分析结果"""
        # 生成总结
        summary = self._generate_summary()
        
        # 构建带总结的结果
        output_data = {
            'summary': summary,
            'library_bugs': self.results['library_bugs'],
            'harness_bugs': self.results['harness_bugs'],
            'analysis_failed': self.results['analysis_failed']
        }
        
        output_file = self.library_output_dir / "bug_filter_results.json"
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        log_success(f"Results saved to {output_file}")
        
        # 打印摘要
        print("\n" + "="*60)
        print("Bug Filter Summary")
        print("="*60)
        print(f"Total library bugs: {summary['total_library_bugs']}")
        print(f"Total harness bugs: {summary['total_harness_bugs']}")
        print(f"Analysis failed:    {summary['total_analysis_failed']}")
        
        if summary['library_bug_apis']:
            print("\n🔴 库设计问题 API (仅库问题):")
            for api, count in summary['library_bug_apis'].items():
                print(f"  - {api}: {count} failures")
        
        if summary['harness_bug_apis']:
            print("\n🟢 Harness 问题 API (仅 harness 问题):")
            for api, count in summary['harness_bug_apis'].items():
                print(f"  - {api}: {count} failures")
        
        if summary['mixed_apis']:
            print("\n🟡 混合问题 API (两者都有):")
            for api, counts in summary['mixed_apis'].items():
                print(f"  - {api}: library={counts['library']}, harness={counts['harness']}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python bug_filter.py <library_output_dir>")
        print("Example: python bug_filter.py Output/libzip")
        sys.exit(1)
    
    library_output_dir = sys.argv[1]
    
    if not os.path.exists(library_output_dir):
        log_error(f"Directory not found: {library_output_dir}")
        sys.exit(1)
    
    filter = BugFilter(library_output_dir)
    results = filter.run()
    
    # 返回码：如果有库 bug 则返回 1
    sys.exit(0 if not results['library_bugs'] else 1)


if __name__ == "__main__":
    main()
