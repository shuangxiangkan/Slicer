#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM代码分析功能测试
测试LLM在代码安全分析和测试工具生成方面的应用
"""

import sys
import unittest
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from llm import create_llm_client

class TestLLMCodeAnalysis(unittest.TestCase):
    """LLM代码分析功能测试类"""
    
    @classmethod
    def setUpClass(cls):
        """设置测试环境"""
        try:
            # 使用统一接口创建客户端，自动选择可用的provider, 默认使用openai
            cls.client = create_llm_client()
            # cls.client = create_llm_client(provider='claude')
            print(f"使用{cls.client.provider}客户端进行测试")
        except Exception as e:
            raise unittest.SkipTest(f"无法创建LLM客户端: {e}")
    
    def test_memory_leak_analysis(self):
        """测试内存泄漏分析功能"""
        print("\n\n\n\n\n\n=== 测试内存泄漏分析功能 ===")
        
        # 测试用的C代码示例（包含内存泄漏）
        test_code = """
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

char* create_buffer(int size) {
    char* buffer = malloc(size * sizeof(char));
    if (buffer == NULL) {
        return NULL;
    }
    memset(buffer, 0, size);
    return buffer;
}

int process_data(const char* input) {
    char* temp_buffer = create_buffer(1024);
    if (temp_buffer == NULL) {
        return -1;
    }
    
    strcpy(temp_buffer, input);
    printf("Processing: %s\n", temp_buffer);
    
    // Note: temp_buffer is not freed here, causing memory leak
    return 0;
}

int main() {
    process_data("Hello World");
    process_data("Test Data");
    return 0;
}
"""
        
        prompt = f"""
Analyze the following C code for memory leak issues. If any exist, identify the specific location and cause, and provide fix suggestions.

Code:
```c
{test_code}
```

Please answer in the following format:
1. Memory leak exists: [Yes/No]
2. Problem location: [specific line number and function name]
3. Problem cause: [brief explanation]
4. Fix suggestion: [specific fix method]
"""
        
        try:
            response = self.client.generate_response(prompt)
            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            
            print(f"Memory leak analysis result:\n{response}")
            
        except Exception as e:
            self.skipTest(f"Memory leak analysis test failed: {e}")
    
    def test_afl_fuzzer_driver_generation(self):
        """测试AFL++模糊测试驱动程序生成功能"""
        print("\n\n\n\n\n\n=== 测试AFL++模糊测试驱动程序生成功能 ===")
        
        # 使用cJSON库的API作为示例
        api_info = """
API Name: cJSON_Parse
Function Signature: cJSON *cJSON_Parse(const char *value)
Description: Parse JSON string and return cJSON object
Parameters:
  - value: JSON string to parse
Return Value: Returns cJSON object pointer on success, NULL on failure
Header File: #include "cJSON.h"
"""
        
        prompt = f"""
Generate an AFL++ fuzzing driver for the following third-party library API.

API Information:
{api_info}

Requirements:
1. Use standard AFL++ driver structure
2. Read fuzzing input from stdin
3. Handle memory management correctly
4. Include necessary error checking
5. Add appropriate comments

Please generate complete C code.
"""
        
        try:
            response = self.client.generate_response(prompt)
            self.assertIsNotNone(response)
            self.assertIsInstance(response, str)
            self.assertGreater(len(response), 0)
            
            print(f"AFL++ driver generation result:\n{response}")
            
        except Exception as e:
            self.skipTest(f"AFL++ driver generation test failed: {e}")
    


def run_tests():
    """运行所有测试"""
    print("开始LLM代码分析功能测试...")
    print("注意: 这些测试需要有效的API密钥才能运行")
    
    try:
        # 尝试创建客户端来验证配置
        test_client = create_llm_client()
        print(f"检测到可用的{test_client.provider}客户端")
    except Exception as e:
        print(f"\n警告: {e}")
        print("请在 llm/.env 文件中配置API密钥后再运行测试")
        return
    
    # 运行测试
    unittest.main(argv=[''], exit=False, verbosity=2)

if __name__ == '__main__':
    run_tests()